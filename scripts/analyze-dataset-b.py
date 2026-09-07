#!/usr/bin/env python3
"""
analyze-dataset-b.py
---------------------
collect-dataset-b.py ile toplanan corpus üzerinde, bildiri görev dosyasının
3. maddesinde ("Dataset B — Real-World Docker Compose Corpus") istenen
metrikleri hesaplar:

    - file size (bytes)
    - line count
    - service count
    - top-level section count
    - extension field count (x-* alanları)
    - YAML nesting depth
    - short/long syntax kullanımı (environment, ports, volumes için)

Çıktılar:
    datasets/real-world/_analysis.csv     (dosya başına satır)
    datasets/real-world/_analysis_summary.json  (korpus özeti: min/max/median/mean)

Kullanım:
    python3 analyze-dataset-b.py \
        --input-dir datasets/real-world \
        --manifest datasets/real-world/_manifest.jsonl
"""

import argparse
import csv
import json
import os
import statistics as st
from typing import Any, Dict

import yaml


def yaml_depth(node: Any, current: int = 0) -> int:
    """Bir YAML düğümünün maksimum iç içe geçme (nesting) derinliğini hesaplar."""
    if isinstance(node, dict):
        if not node:
            return current
        return max(yaml_depth(v, current + 1) for v in node.values())
    if isinstance(node, list):
        if not node:
            return current
        return max(yaml_depth(v, current + 1) for v in node)
    return current


def count_extension_fields(node: Any) -> int:
    """Dokümanın herhangi bir yerindeki 'x-' ile başlayan alan sayısını sayar
    (Compose Specification extension field konvansiyonu)."""
    count = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.startswith("x-"):
                count += 1
            count += count_extension_fields(v)
    elif isinstance(node, list):
        for v in node:
            count += count_extension_fields(v)
    return count


def classify_syntax_usage(services: Dict[str, Any]) -> Dict[str, int]:
    """environment / ports / volumes alanlarında short-syntax (liste/string)
    vs long-syntax (mapping/dict-listesi) kullanımını sayar."""
    counts = {
        "environment_short": 0, "environment_long": 0,
        "ports_short": 0, "ports_long": 0,
        "volumes_short": 0, "volumes_long": 0,
    }
    if not isinstance(services, dict):
        return counts

    for svc in services.values():
        if not isinstance(svc, dict):
            continue

        env = svc.get("environment")
        if isinstance(env, list):
            counts["environment_short"] += 1
        elif isinstance(env, dict):
            counts["environment_long"] += 1

        ports = svc.get("ports")
        if isinstance(ports, list):
            for p in ports:
                if isinstance(p, dict):
                    counts["ports_long"] += 1
                else:
                    counts["ports_short"] += 1

        vols = svc.get("volumes")
        if isinstance(vols, list):
            for v in vols:
                if isinstance(v, dict):
                    counts["volumes_long"] += 1
                else:
                    counts["volumes_short"] += 1

    return counts


def analyze_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    size_bytes = len(text.encode("utf-8"))

    try:
        data = yaml.safe_load(text)
    except Exception as e:
        return {
            "file": os.path.basename(path),
            "size_bytes": size_bytes,
            "line_count": line_count,
            "parse_error": str(e)[:200],
        }

    if not isinstance(data, dict):
        return {
            "file": os.path.basename(path),
            "size_bytes": size_bytes,
            "line_count": line_count,
            "parse_error": "root is not a mapping",
        }

    services = data.get("services", {}) if isinstance(data.get("services"), dict) else {}
    top_level_sections = list(data.keys())
    syntax = classify_syntax_usage(services)

    return {
        "file": os.path.basename(path),
        "size_bytes": size_bytes,
        "line_count": line_count,
        "service_count": len(services),
        "top_level_section_count": len(top_level_sections),
        "top_level_sections": ";".join(sorted(top_level_sections)),
        "extension_field_count": count_extension_fields(data),
        "yaml_nesting_depth": yaml_depth(data),
        **syntax,
        "parse_error": "",
    }


def summarize(rows):
    numeric_fields = [
        "size_bytes", "line_count", "service_count", "top_level_section_count",
        "extension_field_count", "yaml_nesting_depth",
        "environment_short", "environment_long",
        "ports_short", "ports_long", "volumes_short", "volumes_long",
    ]
    valid_rows = [r for r in rows if not r.get("parse_error")]
    summary = {
        "total_files": len(rows),
        "parseable_files": len(valid_rows),
        "parse_failures": len(rows) - len(valid_rows),
    }
    for field_name in numeric_fields:
        values = [r[field_name] for r in valid_rows if field_name in r]
        if not values:
            continue
        summary[field_name] = {
            "min": min(values),
            "max": max(values),
            "mean": round(st.mean(values), 2),
            "median": st.median(values),
            "stdev": round(st.stdev(values), 2) if len(values) > 1 else 0.0,
        }
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-dir", default="datasets/real-world")
    ap.add_argument("--out-csv", default=None)
    ap.add_argument("--out-summary", default=None)
    args = ap.parse_args()

    out_csv = args.out_csv or os.path.join(args.input_dir, "_analysis.csv")
    out_summary = args.out_summary or os.path.join(args.input_dir, "_analysis_summary.json")

    files = sorted(
        f for f in os.listdir(args.input_dir)
        if f.endswith((".yml", ".yaml")) and not f.startswith("_")
    )
    if not files:
        print(f"UYARI: {args.input_dir} içinde .yml/.yaml dosyası bulunamadı. "
              f"Önce collect-dataset-b.py çalıştırılmalı.")
        return

    rows = []
    for fname in files:
        rows.append(analyze_file(os.path.join(args.input_dir, fname)))

    fieldnames = sorted({k for r in rows for k in r.keys()})
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    summary = summarize(rows)
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"{len(rows)} dosya analiz edildi.")
    print(f"  Geçerli (parse edilebilen): {summary['parseable_files']}")
    print(f"  Parse hatası: {summary['parse_failures']}")
    print(f"CSV  -> {out_csv}")
    print(f"JSON -> {out_summary}")


if __name__ == "__main__":
    main()
