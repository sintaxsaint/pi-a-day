#!/usr/bin/env python3
"""
pi-a-day — Fetches Pi bootloader docs, generates an AI report, publishes to
Cloudflare Pages via a GitHub push.

Usage:
    python main.py [HF_API_KEY] [--pi=pi5] [--force] [--no-push]

Options:
    --pi=NAME   Pi model key to generate (default: pi5)
    --force     Re-generate even if already done
    --no-push   Write files locally but skip the git push

Env vars:
    HF_API_KEY  Hugging Face API key (alternative to positional arg)
    HF_MODEL    Override model ID (default: MiniMaxAI/MiniMax-M2.5)
"""

import os
import sys
import json
import subprocess
import datetime

import requests
from bs4 import BeautifulSoup
import markdown as md_lib

# ---------------------------------------------------------------------------
# Pi configurations — add more Pi models here in the future
# ---------------------------------------------------------------------------
PI_CONFIGS = {
    "pi5": {
        "name": "Raspberry Pi 5",
        "sources": [
            {
                "title": "Pi5 Boot Process — Raspberry Pi Forums",
                "url": "https://forums.raspberrypi.com/viewtopic.php?t=373222",
            },
            {
                "title": "kernel_2712.img — DeepWiki",
                "url": "https://deepwiki.com/raspberrypi/firmware/2.1.5-raspberry-pi-5-kernel-(kernel_2712.img)",
            },
            {
                "title": "Supporting Pi 5 — Circle Discussion #413",
                "url": "https://github.com/rsta2/circle/discussions/413",
            },
            {
                "title": "UART on Pi 5 GPIO 14/15 — Raspberry Pi Forums",
                "url": "https://forums.raspberrypi.com/viewtopic.php?t=378931",
            },
        ],
    },
}

HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
DEFAULT_MODEL = "MiniMaxAI/MiniMax-M2.5"
MAX_CHARS_PER_SOURCE = 6000
STATE_FILE = "state.json"
SITE_DIR = "site"

# ---------------------------------------------------------------------------
# Styling — embedded in each generated HTML file, no external CSS file needed
# ---------------------------------------------------------------------------
CSS = """\
:root{--bg:#0f1117;--surface:#1a1d27;--border:#2d3748;--text:#e2e8f0;
--muted:#94a3b8;--accent:#c84b31;--code-bg:#0d1117;--link:#63b3ed}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  line-height:1.75;font-size:16px}
a{color:var(--link);text-decoration:none}
a:hover{text-decoration:underline}
/* ── header ── */
header{background:var(--surface);border-bottom:2px solid var(--accent);
  padding:2rem 1rem}
header nav{max-width:860px;margin:0 auto .75rem;font-size:.9rem;color:var(--muted)}
header nav a{color:var(--muted)}
.inner{max-width:860px;margin:0 auto}
header h1{font-size:1.9rem;color:#fff;margin-bottom:.3rem}
header .meta{color:var(--muted);font-size:.85rem}
header .meta a{color:var(--muted)}
/* ── main content ── */
main{max-width:860px;margin:2.5rem auto;padding:0 1rem}
h1,h2,h3,h4{color:#fff;line-height:1.3}
h2{font-size:1.35rem;border-bottom:1px solid var(--border);
  padding-bottom:.4rem;margin:2.25rem 0 .75rem}
h3{font-size:1.1rem;color:#cbd5e0;margin:1.75rem 0 .5rem}
h4{font-size:1rem;color:#94a3b8;margin:1.25rem 0 .4rem}
p{margin:.75rem 0}
ul,ol{margin:.75rem 0 .75rem 1.6rem}
li{margin:.3rem 0}
code{background:var(--code-bg);border:1px solid var(--border);border-radius:4px;
  padding:.15em .4em;font-family:"Fira Code","Cascadia Code",Consolas,monospace;
  font-size:.87em}
pre{background:var(--code-bg);border:1px solid var(--border);border-radius:8px;
  padding:1.1rem;overflow-x:auto;margin:1.25rem 0}
pre code{border:none;padding:0;background:none}
blockquote{border-left:3px solid var(--accent);padding:.5rem 1rem;
  margin:1rem 0;color:var(--muted);font-style:italic}
table{width:100%;border-collapse:collapse;margin:1rem 0;font-size:.9rem}
th,td{padding:.6rem .9rem;text-align:left;border:1px solid var(--border)}
th{background:var(--surface);color:var(--muted);font-weight:600}
/* ── sources box ── */
.sources{background:var(--surface);border:1px solid var(--border);
  border-radius:8px;padding:1rem 1.25rem;margin:0 0 2rem}
.sources h3{margin:0 0 .5rem;font-size:.85rem;color:var(--muted);
  text-transform:uppercase;letter-spacing:.07em}
.sources ul{margin:.4rem 0 0 1.25rem}
.sources li{margin:.2rem 0;font-size:.9rem}
/* ── footer ── */
footer{background:var(--surface);border-top:1px solid var(--border);
  padding:1.5rem 1rem;text-align:center;color:var(--muted);font-size:.85rem;
  margin-top:4rem}
/* ── index cards ── */
.hero{padding:1rem 0 2rem;text-align:center}
.hero p{color:var(--muted);margin:.5rem 0}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
  gap:1.5rem;margin:2rem 0}
.card{background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:1.5rem;transition:border-color .2s}
.card:hover{border-color:var(--accent)}
.card h2{border:none;font-size:1.1rem;margin:0 0 .4rem}
.card .sub{color:var(--muted);font-size:.9rem}
.card .date{color:#475569;font-size:.8rem;margin-top:.3rem}
.card a.btn{display:inline-block;margin-top:1.1rem;padding:.4rem .9rem;
  background:var(--accent);color:#fff;border-radius:6px;font-size:.9rem;
  font-weight:600}
.card a.btn:hover{opacity:.85;text-decoration:none}
.empty{color:var(--muted);text-align:center;padding:3rem 1rem;font-size:1.1rem}
"""

INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>pi-a-day — Raspberry Pi Bootloader Docs</title>
  <style>{css}</style>
</head>
<body>
<header>
  <div class="inner">
    <h1>pi-a-day</h1>
    <p class="meta">AI-assisted community documentation for Raspberry Pi bootloaders &amp; boot processes</p>
  </div>
</header>
<main>
  <div class="card-grid">
{cards}
  </div>
</main>
<footer>
  Built with pi-a-day &nbsp;·&nbsp; AI-generated from community sources &nbsp;·&nbsp;
  <a href="https://github.com/rsta2/circle/discussions/413">Contribute</a>
</footer>
</body>
</html>
"""

REPORT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} — pi-a-day</title>
  <style>{css}</style>
</head>
<body>
<header>
  <nav><a href="index.html">← All Reports</a></nav>
  <div class="inner">
    <h1>{title}</h1>
    <p class="meta">Generated {date} &nbsp;·&nbsp; <a href="{md_file}">Download .md</a></p>
  </div>
</header>
<main>
  <div class="sources">
    <h3>Sources</h3>
    <ul>
{source_items}
    </ul>
  </div>
{body}
</main>
<footer>
  AI-generated from community sources using
  <a href="https://huggingface.co/MiniMaxAI/MiniMax-M2.5">MiniMax M2.5</a>
  via <a href="https://github.com/">pi-a-day</a>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# State tracking — skips already-generated reports
# ---------------------------------------------------------------------------
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Web scraping
# ---------------------------------------------------------------------------
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


def _parse_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    lines = [ln for ln in soup.get_text(separator="\n", strip=True).splitlines() if ln.strip()]
    return "\n".join(lines)[:MAX_CHARS_PER_SOURCE]


def _wayback_url(url: str) -> str | None:
    """Return the most recent Wayback Machine snapshot URL, or None."""
    try:
        r = requests.get(
            "http://archive.org/wayback/available",
            params={"url": url},
            timeout=15,
        )
        snap = r.json().get("archived_snapshots", {}).get("closest", {})
        if snap.get("available"):
            return snap["url"]
    except Exception:
        pass
    return None


def fetch_content(url: str, title: str) -> str:
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)

    # 1. Try live URL
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 200:
            return _parse_text(resp.text)
        print(f"  [WARN] {resp.status_code} from '{title}' — trying Wayback Machine...", file=sys.stderr)
    except requests.RequestException as exc:
        print(f"  [WARN] Could not fetch '{title}': {exc} — trying Wayback Machine...", file=sys.stderr)

    # 2. Wayback Machine snapshot
    archive_url = _wayback_url(url)
    if archive_url:
        try:
            resp = session.get(archive_url, timeout=30)
            resp.raise_for_status()
            print(f"  [INFO] Using Wayback Machine snapshot for '{title}'")
            return _parse_text(resp.text)
        except requests.RequestException as exc2:
            print(f"  [WARN] Wayback fallback also failed for '{title}': {exc2}", file=sys.stderr)
    else:
        print(f"  [WARN] No Wayback snapshot found for '{title}'", file=sys.stderr)

    return ""


# ---------------------------------------------------------------------------
# AI report generation
# ---------------------------------------------------------------------------
def build_prompt(pi_cfg: dict, sources_text: str) -> str:
    name = pi_cfg["name"]
    return f"""You are a Raspberry Pi hardware and firmware expert writing community documentation.

Based on the source material below — collected from official forums, GitHub discussions, and wiki pages — write a comprehensive technical report titled:

**"{name} Bootloader & Boot Process: Community Documentation"**

Structure the report with these sections:
1. Overview of the {name} Boot Sequence (step-by-step from power-on to kernel)
2. The Bootloader (EEPROM / rpi-eeprom) and its role
3. kernel_2712.img — what it is, why it exists, how it differs from kernel8.img
4. UART / Serial Console on GPIO 14/15 — configuration, quirks, differences from Pi 4
5. Bare-Metal and OS Bring-up Notes (relevant for Circle, U-Boot, custom firmware)
6. Key differences from Raspberry Pi 4 boot process
7. Open questions / areas without official documentation

Rules:
- Use clear Markdown headings and bullet points
- Where info is uncertain or community-sourced, say so explicitly
- Cite the source title in parentheses where relevant
- Be technical but accessible

SOURCE MATERIAL:
{sources_text}"""


def generate_report(prompt: str, api_key: str, model: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.3,
    }
    try:
        resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"\n[ERROR] API call failed: {exc}", file=sys.stderr)
        if hasattr(exc, "response") and exc.response is not None:
            print(f"Response: {exc.response.text[:500]}", file=sys.stderr)
        sys.exit(1)
    return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Site generation
# ---------------------------------------------------------------------------
def build_site(pi_key: str, pi_cfg: dict, report_md: str, date_str: str, state: dict) -> None:
    os.makedirs(SITE_DIR, exist_ok=True)

    # Markdown → HTML
    body_html = md_lib.markdown(report_md, extensions=["extra", "toc", "sane_lists"])

    # Source list items
    source_items = "\n".join(
        f'      <li><a href="{s["url"]}" target="_blank" rel="noopener">{s["title"]}</a></li>'
        for s in pi_cfg["sources"]
    )

    # Report page
    md_file = f"{pi_key}-report.md"
    report_html = REPORT_TEMPLATE.format(
        css=CSS,
        title=f"{pi_cfg['name']} Bootloader & Boot Process",
        date=date_str,
        md_file=md_file,
        source_items=source_items,
        body=body_html,
    )
    with open(os.path.join(SITE_DIR, f"{pi_key}.html"), "w", encoding="utf-8") as f:
        f.write(report_html)

    # Raw markdown (downloadable from the site)
    with open(os.path.join(SITE_DIR, md_file), "w", encoding="utf-8") as f:
        src_list = "\n".join(f"- [{s['title']}]({s['url']})" for s in pi_cfg["sources"])
        f.write(
            f"# {pi_cfg['name']} Bootloader & Boot Process\n\n"
            f"*Generated {date_str}*\n\n"
            f"## Sources\n\n{src_list}\n\n---\n\n{report_md}\n"
        )

    # Index page — list all completed Pi reports
    cards = []
    for pk, cfg in PI_CONFIGS.items():
        if state.get(pk, {}).get("done"):
            gen_date = state[pk].get("generated_at", "")
            cards.append(
                f'    <div class="card">\n'
                f'      <h2>{cfg["name"]}</h2>\n'
                f'      <p class="sub">Bootloader &amp; Boot Process</p>\n'
                f'      <p class="date">{gen_date}</p>\n'
                f'      <a class="btn" href="{pk}.html">Read Report</a>\n'
                f'    </div>'
            )

    cards_html = "\n".join(cards) if cards else '    <p class="empty">No reports generated yet.</p>'
    index_html = INDEX_TEMPLATE.format(css=CSS, cards=cards_html)
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"  site/{pi_key}.html")
    print(f"  site/{md_file}")
    print(f"  site/index.html")


# ---------------------------------------------------------------------------
# Git push → triggers Cloudflare Pages rebuild
# ---------------------------------------------------------------------------
def git_push(pi_key: str, pi_cfg: dict, date_str: str) -> None:
    files = [
        f"site/{pi_key}.html",
        f"site/{pi_key}-report.md",
        "site/index.html",
        STATE_FILE,
    ]
    try:
        subprocess.run(["git", "add"] + files, check=True)
        msg = f"report: {pi_cfg['name']} bootloader [{date_str}]"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Pushed. Cloudflare Pages will deploy in ~30 seconds.")
    except subprocess.CalledProcessError as exc:
        print(f"[WARN] Git step failed: {exc}", file=sys.stderr)
        print("Files are saved locally. Push manually to deploy.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    args = sys.argv[1:]
    pi_key = "pi5"
    force = False
    no_push = False
    api_key_arg = None

    for a in args:
        if a == "--force":
            force = True
        elif a == "--no-push":
            no_push = True
        elif a.startswith("--pi="):
            pi_key = a.split("=", 1)[1]
        elif not a.startswith("--"):
            api_key_arg = a

    api_key = os.environ.get("HF_API_KEY") or api_key_arg
    if not api_key:
        print("Error: Hugging Face API key required.", file=sys.stderr)
        print("  Usage: python main.py hf_YOUR_KEY", file=sys.stderr)
        sys.exit(1)

    if pi_key not in PI_CONFIGS:
        print(f"[ERROR] Unknown pi: '{pi_key}'. Available: {', '.join(PI_CONFIGS)}", file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("HF_MODEL", DEFAULT_MODEL)
    pi_cfg = PI_CONFIGS[pi_key]
    state = load_state()

    if state.get(pi_key, {}).get("done") and not force:
        print(f"{pi_cfg['name']} report already generated.")
        print(f"  site/{pi_key}.html")
        print("Use --force to regenerate.")
        sys.exit(0)

    date_str = datetime.date.today().isoformat()
    print(f"pi-a-day: {pi_cfg['name']}")
    print(f"Model   : {model}\n")

    # 1. Scrape sources
    print("Fetching sources...")
    sections = []
    for src in pi_cfg["sources"]:
        print(f"  -> {src['title']}")
        text = fetch_content(src["url"], src["title"])
        if text:
            sep = "=" * 60
            sections.append(f"\n\n{sep}\nSOURCE: {src['title']}\nURL: {src['url']}\n{sep}\n\n{text}")
        else:
            print("     (skipped — no content retrieved)")

    if not sections:
        print("[ERROR] Could not fetch any source content.", file=sys.stderr)
        sys.exit(1)
    print(f"\nFetched {len(sections)}/{len(pi_cfg['sources'])} sources.")

    # 2. Generate report
    print("Generating report via AI (this may take a minute)...")
    prompt = build_prompt(pi_cfg, "\n".join(sections))
    report_md = generate_report(prompt, api_key, model)

    # 3. Save raw markdown alongside the repo root too
    raw_path = f"{pi_key}-bootloader-report.md"
    with open(raw_path, "w", encoding="utf-8") as f:
        src_list = "\n".join(f"- [{s['title']}]({s['url']})" for s in pi_cfg["sources"])
        f.write(
            f"# {pi_cfg['name']} Bootloader & Boot Process\n\n"
            f"*Generated {date_str}*\n\n"
            f"## Sources\n\n{src_list}\n\n---\n\n{report_md}\n"
        )

    # 4. Build website files
    print("\nBuilding site...")
    state.setdefault(pi_key, {})["done"] = True
    state[pi_key]["generated_at"] = date_str
    build_site(pi_key, pi_cfg, report_md, date_str, state)
    save_state(state)
    print(f"  {STATE_FILE}")

    # 5. Git push → Cloudflare Pages deploys automatically
    if not no_push:
        print("\nPublishing to GitHub...")
        git_push(pi_key, pi_cfg, date_str)
    else:
        print("\n[--no-push] Skipping git push. Files written locally.")

    print(f"\nDone! Report: site/{pi_key}.html")


if __name__ == "__main__":
    main()
