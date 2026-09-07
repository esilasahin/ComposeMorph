#!/usr/bin/env python3
"""
collect-dataset-b.py
---------------------
Dataset B (Real-World Docker Compose Corpus) toplayıcı.

Bildiri görevinin 3. maddesinde istenen "en az 500, tercihen 1000+ gerçek
Docker Compose dosyası" hedefine ulaşmak için GitHub'daki açık kaynak
repolardan docker-compose.yml / docker-compose.yaml / compose.yml /
compose.yaml dosyalarını indirir.

ÇALIŞMA MODU
============
GitHub'ın Code Search API'si ("filename:docker-compose.yml" gibi aramalar)
KİMLİK DOĞRULAMA (token) OLMADAN ÇALIŞMIYOR (401 Unauthorized). Bu yüzden
script iki modda çalışır:

  1) GITHUB_TOKEN ortam değişkeni set edilmişse:
     -> GitHub Code Search API kullanılır (çok daha isabetli/çeşitli sonuç,
        dosya repo kökü dışında herhangi bir yerde olsa da bulunur).
        Rate limit: kimlik doğrulamalı search API için 30 istek/dakika.

  2) Token yoksa (varsayılan / bu sandbox'taki durum):
     -> Repository Search API (bu uç nokta token'sız da çalışıyor,
        10 istek/dakika limitli) ile popüler / docker-compose ile ilgili
        repolar bulunur, ardından her repo için olası dosya yolları
        (docker-compose.yml, docker-compose.yaml, compose.yml, ...,
        deploy/docker-compose.yml, docker/docker-compose.yml, ...)
        raw.githubusercontent.com üzerinden doğrudan denenir (bu CDN
        GitHub API rate limitine tabi değildir).
     Bu mod token'lı moda göre daha az çeşitli sonuç verir (çoğunlukla
     repo kökünde veya çok bilinen alt dizinlerde dosya bulur) ama
     500+ dosyaya ulaşmak için yeterlidir.

KULLANIM
========
    # Token'sız (bu ortamda test edilen varsayılan mod)
    python3 collect-dataset-b.py --target 600

    # Token'lı (önerilir, çok daha zengin/çeşitli bir corpus verir)
    export GITHUB_TOKEN=ghp_xxx...
    python3 collect-dataset-b.py --target 1000

Çıktılar:
    datasets/real-world/<owner>__<repo>__<path-sanitized>.yml   (ham dosyalar)
    datasets/real-world/_manifest.jsonl                          (metadata)
    datasets/real-world/_collection_log.txt                      (log)

Manifest her satırda şu alanları içerir:
    {source_repo, source_path, stars, default_branch, raw_url,
     local_filename, size_bytes, sha256, discovered_via}

Bu manifest hem tekrarlanabilirlik (RQ'ların "reproducible" gereksinimi)
hem de analyze-dataset-b.py için giriş olarak kullanılır.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests
import yaml

GITHUB_API = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"

# Repo kökünde / bilinen alt dizinlerde denenecek olası dosya adları.
# Docker Compose Specification hem eski (docker-compose.yml) hem yeni
# (compose.yaml) adlandırmayı destekler; ikisi de dahil edilmiştir.
CANDIDATE_FILENAMES = [
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "docker-compose.dev.yml",
    "docker-compose.prod.yml",
    "docker-compose.local.yml",
    "docker-compose.override.yml",
]

CANDIDATE_DIRS = [
    "",
    "docker/",
    "deploy/",
    "deployment/",
    ".docker/",
    "docker/dev/",
    "local/",
    "infra/",
    "ops/",
]

# Token'sız modda repo bulmak için kullanılan arama sorguları.
# Farklı q string'leri farklı repo kümeleri döndürür -> çeşitlilik.
REPO_SEARCH_QUERIES = [
    "topic:docker-compose",
    "topic:docker-compose-file",
    "docker-compose in:readme,description stars:>50",
    "microservices docker-compose in:readme",
    "docker-compose language:YAML in:readme",
    "self-hosted docker-compose in:readme",
    "docker-compose stack in:readme stars:>20",
    "compose.yaml in:readme",
]

# Token'lı modda code search için kullanılan sorgular (çeşitlilik için
# birden fazla dosya adı ve dil filtresi kombinasyonu).
CODE_SEARCH_QUERIES = [
    "filename:docker-compose.yml",
    "filename:docker-compose.yaml",
    "filename:compose.yml",
    "filename:compose.yaml",
]


@dataclass
class Candidate:
    owner: str
    repo: str
    path: str
    default_branch: str
    stars: int = 0
    discovered_via: str = ""


def log(msg: str, logfile) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    if logfile:
        logfile.write(line + "\n")
        logfile.flush()


def make_session(token: Optional[str]) -> requests.Session:
    s = requests.Session()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "cpp-compose-editor-dataset-collector",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    s.headers.update(headers)
    return s


def sanitize(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")


def looks_like_compose_file(text: str) -> bool:
    """Hızlı bir sağlık kontrolü: dosya gerçekten bir Compose dosyası mı?"""
    if len(text) > 2_000_000:  # 2MB üstünü atla (muhtemelen alakasız/şişkin)
        return False
    try:
        data = yaml.safe_load(text)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    # Compose dosyalarının neredeyse tamamında 'services' anahtarı bulunur.
    return "services" in data and isinstance(data.get("services"), dict)


def search_repos(session: requests.Session, query: str, max_pages: int,
                  per_page: int, sleep_s: float, logfile) -> list:
    results = []
    for page in range(1, max_pages + 1):
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        }
        url = f"{GITHUB_API}/search/repositories?{urllib.parse.urlencode(params)}"
        resp = session.get(url, timeout=30)
        if resp.status_code == 403 or resp.status_code == 429:
            log(f"  rate-limited on repo search (HTTP {resp.status_code}); "
                f"backing off 60s", logfile)
            time.sleep(60)
            continue
        if resp.status_code != 200:
            log(f"  repo search failed HTTP {resp.status_code}: {resp.text[:200]}",
                logfile)
            break
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        results.extend(items)
        if len(items) < per_page:
            break
        time.sleep(sleep_s)
    return results


def search_code(session: requests.Session, query: str, max_pages: int,
                 per_page: int, sleep_s: float, logfile) -> list:
    results = []
    for page in range(1, max_pages + 1):
        params = {"q": query, "per_page": per_page, "page": page}
        url = f"{GITHUB_API}/search/code?{urllib.parse.urlencode(params)}"
        resp = session.get(url, timeout=30)
        if resp.status_code in (403, 429):
            log(f"  rate-limited on code search (HTTP {resp.status_code}); "
                f"backing off 60s", logfile)
            time.sleep(60)
            continue
        if resp.status_code != 200:
            log(f"  code search failed HTTP {resp.status_code}: {resp.text[:200]}",
                logfile)
            break
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        results.extend(items)
        if len(items) < per_page or page * per_page >= 1000:
            # GitHub search API toplamda en fazla 1000 sonuç döndürür.
            break
        time.sleep(sleep_s)
    return results


def collect_candidates_no_token(session: requests.Session, target: int,
                                 logfile) -> list:
    """Token'sız mod: repo search + bilinen dosya yollarını prob et."""
    candidates = []
    seen_repos = set()

    for query in REPO_SEARCH_QUERIES:
        log(f"Repo search query: {query!r}", logfile)
        repos = search_repos(session, query, max_pages=10, per_page=100,
                              sleep_s=7.0, logfile=logfile)
        log(f"  -> {len(repos)} repo bulundu", logfile)
        for r in repos:
            full_name = r["full_name"]
            if full_name in seen_repos:
                continue
            seen_repos.add(full_name)
            owner, repo = full_name.split("/", 1)
            branch = r.get("default_branch") or "main"
            stars = r.get("stargazers_count", 0)
            for d in CANDIDATE_DIRS:
                for fname in CANDIDATE_FILENAMES:
                    candidates.append(Candidate(
                        owner=owner, repo=repo, path=f"{d}{fname}",
                        default_branch=branch, stars=stars,
                        discovered_via=f"repo-search:{query}",
                    ))
        # Rota sayısı hedefin birkaç katına ulaştıysa erken kes
        # (her repo başına ~%dosya bulma olasılığı düşük olduğundan
        # bolca aday üretmek gerekiyor).
        if len(seen_repos) >= target * 3:
            break

    log(f"Toplam benzersiz repo: {len(seen_repos)}, "
        f"toplam prob edilecek aday yol: {len(candidates)}", logfile)
    return candidates


def collect_candidates_with_token(session: requests.Session, target: int,
                                   logfile) -> list:
    """Token'lı mod: code search doğrudan dosya yollarını verir."""
    candidates = []
    seen = set()
    for query in CODE_SEARCH_QUERIES:
        log(f"Code search query: {query!r}", logfile)
        items = search_code(session, query, max_pages=10, per_page=100,
                             sleep_s=2.5, logfile=logfile)
        log(f"  -> {len(items)} sonuç", logfile)
        for it in items:
            repo_info = it.get("repository", {})
            full_name = repo_info.get("full_name")
            path = it.get("path")
            if not full_name or not path:
                continue
            key = (full_name, path)
            if key in seen:
                continue
            seen.add(key)
            owner, repo = full_name.split("/", 1)
            candidates.append(Candidate(
                owner=owner, repo=repo, path=path,
                default_branch="",  # aşağıda çözülecek
                stars=repo_info.get("stargazers_count", 0) or 0,
                discovered_via=f"code-search:{query}",
            ))
        if len(seen) >= target * 2:
            break
    return candidates


def resolve_branch_and_fetch(session: requests.Session, cand: Candidate,
                              logfile) -> Optional[str]:
    """Verilen candidate için raw dosya içeriğini indirmeyi dener.
    default_branch bilinmiyorsa main/master fallback dener."""
    branches = [cand.default_branch] if cand.default_branch else []
    branches += [b for b in ("main", "master") if b not in branches]

    for branch in branches:
        if not branch:
            continue
        url = f"{RAW_BASE}/{cand.owner}/{cand.repo}/{branch}/{cand.path}"
        try:
            resp = requests.get(url, timeout=15)
        except requests.RequestException:
            continue
        if resp.status_code == 200:
            cand.default_branch = branch
            return resp.text
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=int, default=500,
                     help="Toplanacak hedef geçerli Compose dosyası sayısı (varsayılan: 500)")
    ap.add_argument("--output-dir", default="datasets/real-world",
                     help="Çıktı dizini")
    ap.add_argument("--sleep-between-raw", type=float, default=0.15,
                     help="raw.githubusercontent.com istekleri arası bekleme (saniye)")
    ap.add_argument("--max-candidates", type=int, default=20000,
                     help="En fazla kaç aday yol denensin (güvenlik limiti)")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    os.makedirs(args.output_dir, exist_ok=True)
    logpath = os.path.join(args.output_dir, "_collection_log.txt")
    manifest_path = os.path.join(args.output_dir, "_manifest.jsonl")

    with open(logpath, "a", encoding="utf-8") as logfile:
        log("=" * 70, logfile)
        log(f"Dataset B toplama başlıyor. target={args.target}, "
            f"token={'VAR' if token else 'YOK (fallback mod)'}", logfile)

        session = make_session(token)

        if token:
            candidates = collect_candidates_with_token(session, args.target, logfile)
        else:
            log("GITHUB_TOKEN bulunamadı -> repository-search + raw-probe "
                "fallback moduna geçiliyor. Daha zengin bir corpus için "
                "GITHUB_TOKEN ortam değişkenini set edip tekrar çalıştırmanız "
                "önerilir (bkz. script docstring'i).", logfile)
            candidates = collect_candidates_no_token(session, args.target, logfile)

        candidates = candidates[: args.max_candidates]
        log(f"Toplam {len(candidates)} aday denenecek.", logfile)

        collected = 0
        tried = 0
        manifest_entries = []
        already_saved_hashes = set()

        # Zaten var olan manifest'i oku (script tekrar çalıştırılırsa
        # kaldığı yerden devam etsin / mükerrer indirmesin).
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as mf:
                for line in mf:
                    try:
                        entry = json.loads(line)
                        already_saved_hashes.add(entry["sha256"])
                        manifest_entries.append(entry)
                    except Exception:
                        pass
            collected = len(manifest_entries)
            log(f"Mevcut manifestte {collected} dosya bulundu, üzerine eklenecek.",
                logfile)

        with open(manifest_path, "a", encoding="utf-8") as mf:
            for cand in candidates:
                if collected >= args.target:
                    break
                tried += 1
                if tried % 50 == 0:
                    log(f"...{tried} aday denendi, {collected} dosya toplandı", logfile)

                text = resolve_branch_and_fetch(session, cand, logfile)
                time.sleep(args.sleep_between_raw)
                if text is None:
                    continue
                if not looks_like_compose_file(text):
                    continue

                digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
                if digest in already_saved_hashes:
                    continue  # aynı içerikli dosya (fork/duplikasyon) -> atla
                already_saved_hashes.add(digest)

                local_name = sanitize(f"{cand.owner}__{cand.repo}__{cand.path}") + ".yml"
                local_path = os.path.join(args.output_dir, local_name)
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(text)

                entry = {
                    "source_repo": f"{cand.owner}/{cand.repo}",
                    "source_path": cand.path,
                    "stars": cand.stars,
                    "default_branch": cand.default_branch,
                    "raw_url": f"{RAW_BASE}/{cand.owner}/{cand.repo}/{cand.default_branch}/{cand.path}",
                    "local_filename": local_name,
                    "size_bytes": len(text.encode("utf-8")),
                    "sha256": digest,
                    "discovered_via": cand.discovered_via,
                }
                mf.write(json.dumps(entry, ensure_ascii=False) + "\n")
                mf.flush()
                manifest_entries.append(entry)
                collected += 1
                if collected % 25 == 0:
                    log(f"  {collected}/{args.target} dosya toplandı "
                        f"(son: {entry['source_repo']}/{entry['source_path']})",
                        logfile)

        log(f"Bitti. Denenen aday: {tried}, toplanan geçerli dosya: {collected} "
            f"(hedef: {args.target})", logfile)
        if collected < args.target:
            log("UYARI: Hedefe ulaşılamadı. Önerilenler: "
                "(1) GITHUB_TOKEN set edip code-search modunu kullanın, "
                "(2) --max-candidates değerini artırın, "
                "(3) REPO_SEARCH_QUERIES listesine yeni sorgular ekleyin, "
                "(4) scripti tekrar çalıştırın (kaldığı yerden devam eder).",
                logfile)

        print(f"\nToplam {collected} dosya -> {args.output_dir}")
        print(f"Manifest: {manifest_path}")
        print(f"Log: {logpath}")


if __name__ == "__main__":
    main()
