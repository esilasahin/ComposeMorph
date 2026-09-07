#!/usr/bin/env python3
"""
collect-large-files.py
------------------------
Dataset B içinde eksik olan "Large" (500-2000 satır) ve "XLarge" (>2000 satır)
boyut gruplarını doldurmak için GERÇEK Docker Compose dosyalarını arar.

collect-dataset-b.py'den farkı: token'sız modda sadece "olası dosya yolu"
tahmin ediyorduk (docker-compose.yml, docker/docker-compose.yml, ...).
Bu script ise (GITHUB_TOKEN gerektirir) her aday repo için GitHub'ın
"Git Trees API"sini kullanarak REPO'NUN TÜM DOSYA AĞACINI tarar ve içinde
adı *compose*.y*ml geçen HER dosyayı bulur — dosya repo kökünde olsun,
10 seviye alt dizinde olsun fark etmez. Bu, büyük "homelab" / "self-hosted
stack" tipi repoların derinlerde sakladığı devasa compose dosyalarını
yakalamak için gerekli.

Ayrıca arama sorguları özellikle "çok servisli büyük stack" barındırma
olasılığı yüksek repo türlerine (homelab, self-hosted, media-server,
monitoring-stack) odaklanır.

GEREKSİNİM: GITHUB_TOKEN ortam değişkeni set edilmiş olmalı
(bkz. collect-dataset-b.py docstring'i — token nasıl oluşturulur).
Token'sız çalıştırılırsa script hemen uyarı verip çıkar.

KULLANIM
========
    export GITHUB_TOKEN=ghp_xxx...
    python3 collect-large-files.py --min-lines 500 --target 40

Çıktı:
    datasets/real-world/large/<owner>__<repo>__<path>.yml
    datasets/real-world/large/_manifest.jsonl
        (source_repo, source_path, stars, line_count, size_bytes,
         size_bucket: "large"|"xlarge", raw_url, sha256)
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import requests
import yaml

GITHUB_API = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"

# Büyük, çok-servisli tek-dosya stack'leri barındırma olasılığı yüksek
# repo türlerine odaklanan arama sorguları.
REPO_SEARCH_QUERIES = [
    "topic:homelab docker-compose",
    "topic:selfhosted stars:>30",
    "topic:self-hosted docker-compose stars:>30",
    "homelab stack docker-compose in:readme stars:>20",
    "media server stack docker-compose in:readme",
    "monitoring stack prometheus grafana docker-compose in:readme",
    "elk stack docker-compose in:readme",
    "microservices demo docker-compose in:readme stars:>50",
    "docker-compose \"20 services\" OR \"30 services\" in:readme",
    "awesome-compose in:name",
    "self-hosted server docker-compose all in one",
]

# Dosya adında aranacak desen (compose kelimesini içeren .yml/.yaml dosyaları)
COMPOSE_NAME_RE = re.compile(r"compose[^/]*\.ya?ml$", re.IGNORECASE)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def make_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "cpp-compose-editor-large-file-hunter",
    })
    return s


def sanitize(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")


def search_repos(session: requests.Session, query: str, max_pages: int = 5,
                  per_page: int = 100) -> list:
    results = []
    for page in range(1, max_pages + 1):
        params = {"q": query, "sort": "stars", "order": "desc",
                   "per_page": per_page, "page": page}
        url = f"{GITHUB_API}/search/repositories?{urllib.parse.urlencode(params)}"
        resp = session.get(url, timeout=30)
        if resp.status_code in (403, 429):
            log(f"  rate-limited (HTTP {resp.status_code}); 30s bekleniyor")
            time.sleep(30)
            continue
        if resp.status_code != 200:
            log(f"  arama hatası HTTP {resp.status_code}")
            break
        items = resp.json().get("items", [])
        if not items:
            break
        results.extend(items)
        if len(items) < per_page:
            break
        time.sleep(1.0)
    return results


def get_repo_tree(session: requests.Session, owner: str, repo: str,
                   branch: str) -> Optional[list]:
    """Repo'nun tüm dosya ağacını (recursive) döner. Çok büyük repolarda
    GitHub bu isteği kesebilir (truncated=true); o durumda elimizdeki
    kısmi sonuçla devam ederiz (yine de bulma şansı var)."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    try:
        resp = session.get(url, timeout=30)
    except requests.RequestException:
        return None
    if resp.status_code in (403, 429):
        log("  rate-limited on tree fetch; 30s bekleniyor")
        time.sleep(30)
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("tree", [])


def looks_like_compose_file(text: str) -> bool:
    if len(text) > 5_000_000:
        return False
    try:
        data = yaml.safe_load(text)
    except Exception:
        return False
    return isinstance(data, dict) and "services" in data and isinstance(data["services"], dict)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-lines", type=int, default=500,
                     help="Bir dosyanın 'büyük' sayılması için asgari satır sayısı")
    ap.add_argument("--target", type=int, default=40,
                     help="Toplanacak hedef büyük dosya sayısı")
    ap.add_argument("--output-dir", default="datasets/real-world/large")
    ap.add_argument("--max-repos", type=int, default=4000,
                     help="En fazla kaç repo'nun ağacı taransın (güvenlik limiti)")
    ap.add_argument("--query-start", type=int, default=0,
                     help="REPO_SEARCH_QUERIES listesinde hangi indeksten başlansın "
                          "(daha önce denenen sorguları atlamak için, örn. --query-start 2)")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("HATA: GITHUB_TOKEN set edilmemiş. Bu script token gerektirir "
              "(repo dosya ağacını taramak için yüksek rate limit gerekiyor).")
        print("export GITHUB_TOKEN=ghp_... çalıştırıp tekrar deneyin.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    manifest_path = os.path.join(args.output_dir, "_manifest.jsonl")

    session = make_session(token)

    seen_repos = set()
    repos = []
    queries_to_try = REPO_SEARCH_QUERIES[args.query_start:]
    log(f"{len(queries_to_try)}/{len(REPO_SEARCH_QUERIES)} sorgu denenecek "
        f"(başlangıç indeksi: {args.query_start})")
    for q in queries_to_try:
        log(f"Repo search: {q!r}")
        found = search_repos(session, q)
        log(f"  -> {len(found)} repo")
        for r in found:
            if r["full_name"] not in seen_repos:
                seen_repos.add(r["full_name"])
                repos.append(r)
        if len(repos) >= args.max_repos:
            break

    log(f"Toplam {len(repos)} benzersiz repo taranacak (dosya ağacı derin tarama).")

    already = set()
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            for line in f:
                try:
                    already.add(json.loads(line)["sha256"])
                except Exception:
                    pass
        log(f"Mevcut manifestte {len(already)} dosya var, üzerine eklenecek.")

    initial_count = len(already)
    collected = initial_count
    manifest_f = open(manifest_path, "a", encoding="utf-8")

    for i, r in enumerate(repos):
        if collected - initial_count >= args.target:
            break
        if i % 20 == 0:
            log(f"...{i}/{len(repos)} repo tarandı, şimdiye kadar "
                f"{collected - initial_count} yeni büyük dosya bulundu")

        full_name = r["full_name"]
        owner, repo = full_name.split("/", 1)
        branch = r.get("default_branch") or "main"
        stars = r.get("stargazers_count", 0)

        tree = get_repo_tree(session, owner, repo, branch)
        if not tree:
            continue

        compose_paths = [
            item["path"] for item in tree
            if item.get("type") == "blob" and COMPOSE_NAME_RE.search(item.get("path", ""))
        ]
        if not compose_paths:
            continue

        for path in compose_paths:
            raw_url = f"{RAW_BASE}/{owner}/{repo}/{branch}/{path}"
            try:
                resp = requests.get(raw_url, timeout=15)
            except requests.RequestException:
                continue
            if resp.status_code != 200:
                continue
            text = resp.text
            line_count = text.count("\n") + 1
            if line_count < args.min_lines:
                continue
            if not looks_like_compose_file(text):
                continue

            digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
            if digest in already:
                continue
            already.add(digest)

            bucket = "large" if line_count < 2000 else "xlarge"
            local_name = sanitize(f"{owner}__{repo}__{path}") + ".yml"
            with open(os.path.join(args.output_dir, local_name), "w", encoding="utf-8") as f:
                f.write(text)

            entry = {
                "source_repo": full_name, "source_path": path, "stars": stars,
                "default_branch": branch, "raw_url": raw_url,
                "local_filename": local_name, "size_bytes": len(text.encode("utf-8")),
                "line_count": line_count, "size_bucket": bucket,
                "sha256": digest, "discovered_via": "tree-scan",
            }
            manifest_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            manifest_f.flush()
            collected += 1
            log(f"  BULUNDU [{bucket}] {full_name}/{path} ({line_count} satır)")

    manifest_f.close()
    log(f"Bitti. {args.output_dir} içinde toplam {collected} büyük dosya var "
        f"(bu çalıştırmada eklenen: {collected - initial_count}).")
    print(f"\nÇıktı: {args.output_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()