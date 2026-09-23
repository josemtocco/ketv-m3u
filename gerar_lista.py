#!/usr/bin/env python3
import html
import re
import sys
import time
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

BASE = "https://www.ketv.com.br"
INDEX = f"{BASE}/canais"
OUT = "ketv.m3u"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; KE-TV-M3U-Updater/1.0; +https://github.com/)"
})

TIMEOUT = 20

def get(url):
    r = SESSION.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r

def clean_url(u):
    u = html.unescape(u).replace("\\/", "/").strip()
    u = u.strip('"\'')
    return urldefrag(u)[0]

def absolute(u, base):
    return clean_url(urljoin(base, u))

def channel_links(index_html):
    soup = BeautifulSoup(index_html, "html.parser")
    found = {}

    for a in soup.find_all("a", href=True):
        href = absolute(a["href"], BASE)
        p = urlparse(href)
        if p.netloc != urlparse(BASE).netloc:
            continue
        if not p.path.startswith("/canal/"):
            continue

        name = " ".join(a.get_text(" ", strip=True).split())
        if not name:
            name = p.path.rstrip("/").split("/")[-1].replace("-", " ").title()

        found[href] = name

    return found

URL_PATTERNS = [
    r'https?://[^"\'<>\s\\]+?\.m3u8(?:\?[^"\'<>\s\\]*)?',
    r'(?:"|\')([^"\']+?\.m3u8(?:\?[^"\']*)?)(?:"|\')',
]

def extract_m3u8(page_url, page_html):
    candidates = []

    # Raw HTML / JavaScript
    for pattern in URL_PATTERNS:
        for m in re.finditer(pattern, page_html, flags=re.I):
            value = m.group(1) if m.lastindex else m.group(0)
            candidates.append(absolute(value, page_url))

    # Common HTML media/source attributes
    soup = BeautifulSoup(page_html, "html.parser")
    for tag in soup.find_all(["video", "source"]):
        for attr in ("src", "data-src", "data-hls", "data-stream"):
            value = tag.get(attr)
            if value and ".m3u8" in value.lower():
                candidates.append(absolute(value, page_url))

    # Embedded JSON / escaped strings
    decoded = html.unescape(page_html).replace("\\/", "/").replace("\\u0026", "&")
    for m in re.finditer(r'https?://[^"\'<>\s]+?\.m3u8(?:\?[^"\'<>\s]*)?', decoded, re.I):
        candidates.append(clean_url(m.group(0)))

    # Keep unique URLs, prefer https
    out = []
    seen = set()
    for u in candidates:
        u = clean_url(u)
        if not u.lower().startswith(("http://", "https://")):
            continue
        if ".m3u8" not in u.lower():
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

def validate_hls(url):
    try:
        r = SESSION.get(
            url,
            timeout=TIMEOUT,
            headers={"Accept": "application/vnd.apple.mpegurl,application/x-mpegURL,*/*"},
        )
        if r.status_code != 200:
            return False
        body = r.text[:10000]
        return "#EXTM3U" in body
    except requests.RequestException:
        return False

def channel_metadata(page_url, page_html, fallback_name):
    soup = BeautifulSoup(page_html, "html.parser")

    title = soup.find("h1")
    name = title.get_text(" ", strip=True) if title else fallback_name
    name = re.sub(r"\s+", " ", name).strip()

    # Remove common suffixes only from display name.
    name = re.sub(r"\s+ao vivo\s*$", "", name, flags=re.I).strip()

    category = "KE TV"
    text = soup.get_text(" ", strip=True)

    # Try to recover category from the page.
    m = re.search(r"Categoria\s+(.{1,80}?)(?:Idioma|País|Qualidade|Tipo de programação)", text, re.I)
    if m:
        category = re.sub(r"\s+", " ", m.group(1)).strip(" :")

    logo = ""
    for img in soup.find_all("img", src=True):
        src = absolute(img["src"], page_url)
        alt = (img.get("alt") or "").lower()
        if "logo" in alt or "logo" in src.lower():
            logo = src
            break

    return name or fallback_name, category or "KE TV", logo

def main():
    try:
        index = get(INDEX)
    except Exception as e:
        print(f"Erro ao consultar {INDEX}: {e}", file=sys.stderr)
        sys.exit(1)

    links = channel_links(index.text)
    print(f"Canais encontrados: {len(links)}")

    rows = []
    for i, (page_url, fallback_name) in enumerate(links.items(), 1):
        try:
            page = get(page_url)
            streams = extract_m3u8(page_url, page.text)
            if not streams:
                print(f"[{i}/{len(links)}] sem m3u8: {fallback_name}")
                continue

            stream = next((u for u in streams if validate_hls(u)), None)
            if not stream:
                print(f"[{i}/{len(links)}] m3u8 não validado: {fallback_name}")
                continue

            name, category, logo = channel_metadata(page_url, page.text, fallback_name)
            rows.append((name, category, logo, stream, page_url))
            print(f"[{i}/{len(links)}] OK: {name}")
        except Exception as e:
            print(f"[{i}/{len(links)}] erro: {fallback_name}: {e}")

    rows.sort(key=lambda x: (x[1].lower(), x[0].lower()))

    lines = ["#EXTM3U"]
    for name, category, logo, stream, page_url in rows:
        attrs = [
            f'tvg-name="{name.replace(chr(34), chr(39))}"',
            f'group-title="{category.replace(chr(34), chr(39))}"',
        ]
        if logo:
            attrs.append(f'tvg-logo="{logo}"')

        lines.append(f'#EXTINF:-1 {" ".join(attrs)},{name}')
        lines.append(stream)

    # Keep an explicit empty-but-valid playlist if nothing passed validation.
    # This prevents stale/dead URLs from silently being published.
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Playlist gerada: {OUT}")
    print(f"Canais validados: {len(rows)}")

if __name__ == "__main__":
    main()
