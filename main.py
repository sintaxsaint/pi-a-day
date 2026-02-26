#!/usr/bin/env python3
"""
pi-a-day /Fetches Pi bootloader docs, generates an AI report, publishes to
Cloudflare Pages via a GitHub push.

Usage:
    python main.py [HF_API_KEY] [--pi=KEY|all] [--force] [--no-push]

    Run with no --pi flag to get an interactive selector screen.

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
# Pi configurations /one entry per SoC generation
# ---------------------------------------------------------------------------
PI_CONFIGS = {
    "pi1": {
        "name": "BCM2835 - Pi 1 / Zero / CM1",
        "soc": "BCM2835",
        "models": [
            "Raspberry Pi 1 Model A", "Raspberry Pi 1 Model B",
            "Raspberry Pi 1 Model A+", "Raspberry Pi 1 Model B+",
            "Raspberry Pi Zero", "Raspberry Pi Zero W",
            "Compute Module 1",
        ],
        "sources": [
            {
                "title": "Raspberry Pi Boot Modes /Official Docs",
                "url": "https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-modes",
            },
            {
                "title": "RPi Boot Sequence /eLinux Wiki",
                "url": "https://elinux.org/RPi_Software",
            },
            {
                "title": "raspberrypi/firmware /GitHub (bootcode.bin era)",
                "url": "https://github.com/raspberrypi/firmware",
            },
            {
                "title": "How the Pi boots /Raspberry Pi Forums",
                "url": "https://forums.raspberrypi.com/viewtopic.php?t=6854",
            },
        ],
    },
    "pi2": {
        "name": "BCM2836 - Pi 2 Model B",
        "soc": "BCM2836",
        "models": [
            "Raspberry Pi 2 Model B (rev 1.0)", "Raspberry Pi 2 Model B (rev 1.1)",
        ],
        "sources": [
            {
                "title": "Raspberry Pi Boot Modes /Official Docs",
                "url": "https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-modes",
            },
            {
                "title": "How the Pi boots /Raspberry Pi Forums",
                "url": "https://forums.raspberrypi.com/viewtopic.php?t=6854",
            },
            {
                "title": "RPi U-Boot /eLinux Wiki",
                "url": "https://elinux.org/RPi_U-Boot",
            },
            {
                "title": "raspberrypi/firmware /GitHub",
                "url": "https://github.com/raspberrypi/firmware",
            },
        ],
    },
    "pi3": {
        "name": "BCM2837 - Pi 3 / Zero 2W / CM3",
        "soc": "BCM2837",
        "models": [
            "Raspberry Pi 2 Model B v1.2", "Raspberry Pi 3 Model B",
            "Raspberry Pi 3 Model B+", "Raspberry Pi 3 Model A+",
            "Raspberry Pi Zero 2 W", "Compute Module 3", "Compute Module 3+",
        ],
        "sources": [
            {
                "title": "Pi 3 USB / Network Boot /Official Docs",
                "url": "https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#pi-3-only-bootcode-bin-usb-boot",
            },
            {
                "title": "raspberrypi/usbboot /GitHub (BCM2837 USB boot ROM)",
                "url": "https://github.com/raspberrypi/usbboot",
            },
            {
                "title": "RPiconfig boot options /eLinux Wiki",
                "url": "https://elinux.org/RPiconfig",
            },
            {
                "title": "BCM2837 64-bit boot thread /Raspberry Pi Forums",
                "url": "https://forums.raspberrypi.com/viewtopic.php?t=174648",
            },
        ],
    },
    "pi4": {
        "name": "BCM2711 - Pi 4 / Pi 400 / CM4",
        "soc": "BCM2711",
        "models": [
            "Raspberry Pi 4 Model B", "Raspberry Pi 400",
            "Compute Module 4", "Compute Module 4S",
        ],
        "sources": [
            {
                "title": "BCM2711 Boot EEPROM /Official Docs",
                "url": "https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-4-boot-eeprom",
            },
            {
                "title": "raspberrypi/rpi-eeprom /GitHub",
                "url": "https://github.com/raspberrypi/rpi-eeprom",
            },
            {
                "title": "Pi 4 Bootloader Configuration /Official Docs",
                "url": "https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-4-bootloader-configuration",
            },
            {
                "title": "Pi 4 EEPROM boot deep dive /Raspberry Pi Forums",
                "url": "https://forums.raspberrypi.com/viewtopic.php?t=243087",
            },
        ],
    },
    "pi5": {
        "name": "BCM2712 - Pi 5 / Pi 500 / CM5",
        "soc": "BCM2712",
        "models": [
            "Raspberry Pi 5", "Raspberry Pi 500", "Compute Module 5",
        ],
        "sources": [
            {
                "title": "Pi5 Boot Process /Raspberry Pi Forums",
                "url": "https://forums.raspberrypi.com/viewtopic.php?t=373222",
            },
            {
                "title": "kernel_2712.img /DeepWiki",
                "url": "https://deepwiki.com/raspberrypi/firmware/2.1.5-raspberry-pi-5-kernel-(kernel_2712.img)",
            },
            {
                "title": "Supporting Pi 5 /Circle Discussion #413",
                "url": "https://github.com/rsta2/circle/discussions/413",
            },
            {
                "title": "UART on Pi 5 GPIO 14/15 /Raspberry Pi Forums",
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
# Styling /embedded in each generated HTML file, no external CSS file needed
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
  <title>pi-a-day /Raspberry Pi Bootloader Docs</title>
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
  <p style="margin-top:2.5rem;text-align:center">
    <a href="report.html" style="color:var(--muted);font-size:.9rem">
      Missing a Pi model? Report it →
    </a>
  </p>
</main>
<footer>
  Built with pi-a-day &nbsp;·&nbsp; AI-generated from community sources &nbsp;·&nbsp;
  <a href="https://github.com/sintaxsaint/pi-a-day">GitHub</a>
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
  <title>{title} /pi-a-day</title>
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
  via <a href="https://github.com/sintaxsaint/pi-a-day">pi-a-day</a>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Interactive selector
# ---------------------------------------------------------------------------
def show_selector(state: dict) -> list[str]:
    """Show a numbered menu of all Pi generations and return selected key(s)."""
    keys = list(PI_CONFIGS.keys())

    print("\npi-a-day - Raspberry Pi Bootloader Documentation\n")
    print(f"  {'#':<4} {'Generation':<32} {'Models':<34} Status")
    print("  " + "-" * 78)

    for i, key in enumerate(keys, 1):
        cfg = PI_CONFIGS[key]
        done = state.get(key, {}).get("done", False)
        status = "\033[32mdone\033[0m" if done else "\033[33mtodo\033[0m"
        models_short = ", ".join(cfg["models"][:2])
        if len(cfg["models"]) > 2:
            models_short += f" +{len(cfg['models']) - 2}"
        print(f"  {i:<4} {cfg['name']:<32} {models_short:<34} [{status}]")

    missing = [k for k in keys if not state.get(k, {}).get("done")]
    print()
    print(f"  a.   Generate all missing ({len(missing)} remaining)")
    print(f"  q.   Quit")
    print()

    while True:
        try:
            choice = input("  Enter number or a/q: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if choice == "q":
            sys.exit(0)
        if choice == "a":
            return missing if missing else []
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                return [keys[idx]]
        except ValueError:
            pass
        print("  Invalid /enter a number, 'a', or 'q'.")


# ---------------------------------------------------------------------------
# State tracking
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

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 200:
            return _parse_text(resp.text)
        print(f"  [WARN] {resp.status_code} from '{title}' /trying Wayback Machine...", file=sys.stderr)
    except requests.RequestException as exc:
        print(f"  [WARN] Could not fetch '{title}': {exc} /trying Wayback Machine...", file=sys.stderr)

    archive_url = _wayback_url(url)
    if archive_url:
        try:
            resp = session.get(archive_url, timeout=30)
            resp.raise_for_status()
            print(f"  [INFO] Using Wayback Machine snapshot for '{title}'")
            return _parse_text(resp.text)
        except requests.RequestException as exc2:
            print(f"  [WARN] Wayback fallback failed for '{title}': {exc2}", file=sys.stderr)
    else:
        print(f"  [WARN] No Wayback snapshot for '{title}'", file=sys.stderr)

    return ""


# ---------------------------------------------------------------------------
# AI report generation
# ---------------------------------------------------------------------------
def build_prompt(pi_cfg: dict, sources_text: str) -> str:
    name = pi_cfg["name"]
    soc = pi_cfg["soc"]
    models = ", ".join(pi_cfg["models"])
    return f"""You are a Raspberry Pi hardware and firmware expert writing community documentation.

Based on the source material below /collected from official docs, forums, GitHub, and wikis /write a comprehensive technical report titled:

**"{name} Bootloader & Boot Process: Community Documentation"**

This report covers the following hardware: {models}

Structure the report with these sections:
1. Overview of the {soc} Boot Sequence (step-by-step from power-on to kernel handoff)
2. Boot Firmware & Storage (bootcode.bin / EEPROM / start.elf /whichever applies to {soc})
3. Boot Modes supported (SD card, USB, network/PXE /what's available on {soc})
4. UART / Serial Console /configuration and quirks on {soc} hardware
5. Bare-Metal and OS Bring-up Notes (U-Boot, Circle, custom firmware considerations)
6. Key differences from neighbouring Pi generations
7. Open questions / areas without official documentation

Rules:
- Use clear Markdown headings and bullet points
- Be specific to the {soc} SoC /don't describe features of other generations
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

    body_html = md_lib.markdown(report_md, extensions=["extra", "toc", "sane_lists"])

    source_items = "\n".join(
        f'      <li><a href="{s["url"]}" target="_blank" rel="noopener">{s["title"]}</a></li>'
        for s in pi_cfg["sources"]
    )

    md_file = f"{pi_key}-report.md"
    report_html = REPORT_TEMPLATE.format(
        css=CSS,
        title=f"{pi_cfg['name']} /Bootloader & Boot Process",
        date=date_str,
        md_file=md_file,
        source_items=source_items,
        body=body_html,
    )
    with open(os.path.join(SITE_DIR, f"{pi_key}.html"), "w", encoding="utf-8") as f:
        f.write(report_html)

    with open(os.path.join(SITE_DIR, md_file), "w", encoding="utf-8") as f:
        src_list = "\n".join(f"- [{s['title']}]({s['url']})" for s in pi_cfg["sources"])
        f.write(
            f"# {pi_cfg['name']} /Bootloader & Boot Process\n\n"
            f"*Generated {date_str}*\n\n"
            f"## Sources\n\n{src_list}\n\n---\n\n{report_md}\n"
        )

    # Rebuild index with all currently done reports
    cards = []
    for pk, cfg in PI_CONFIGS.items():
        if state.get(pk, {}).get("done"):
            gen_date = state[pk].get("generated_at", "")
            models_preview = ", ".join(cfg["models"][:3])
            if len(cfg["models"]) > 3:
                models_preview += f" +{len(cfg['models']) - 3} more"
            cards.append(
                f'    <div class="card">\n'
                f'      <h2>{cfg["name"]}</h2>\n'
                f'      <p class="sub">{models_preview}</p>\n'
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
        msg = f"report: {pi_cfg['name']} [{date_str}]"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Pushed. Cloudflare Pages will deploy in ~30 seconds.")
    except subprocess.CalledProcessError as exc:
        print(f"[WARN] Git step failed: {exc}", file=sys.stderr)
        print("Files saved locally. Push manually to deploy.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Generate one Pi report end-to-end
# ---------------------------------------------------------------------------
def run_one(pi_key: str, api_key: str, model: str, force: bool, no_push: bool,
            state: dict) -> None:
    pi_cfg = PI_CONFIGS[pi_key]
    date_str = datetime.date.today().isoformat()

    if state.get(pi_key, {}).get("done") and not force:
        print(f"  {pi_cfg['name']} already done /skipping (use --force to regenerate)")
        return

    print(f"\n{'='*60}")
    print(f"  {pi_cfg['name']}")
    print(f"{'='*60}")

    # 1. Scrape
    print("Fetching sources...")
    sections = []
    for src in pi_cfg["sources"]:
        print(f"  -> {src['title']}")
        text = fetch_content(src["url"], src["title"])
        if text:
            sep = "=" * 60
            sections.append(f"\n\n{sep}\nSOURCE: {src['title']}\nURL: {src['url']}\n{sep}\n\n{text}")
        else:
            print("     (skipped /no content retrieved)")

    if not sections:
        print(f"[ERROR] No content fetched for {pi_cfg['name']} /skipping.", file=sys.stderr)
        return
    print(f"\nFetched {len(sections)}/{len(pi_cfg['sources'])} sources.")

    # 2. Generate
    print("Generating report via AI...")
    prompt = build_prompt(pi_cfg, "\n".join(sections))
    report_md = generate_report(prompt, api_key, model)

    # 3. Build site files
    print("\nBuilding site...")
    state.setdefault(pi_key, {})["done"] = True
    state[pi_key]["generated_at"] = date_str
    build_site(pi_key, pi_cfg, report_md, date_str, state)
    save_state(state)
    print(f"  {STATE_FILE}")

    # 4. Push
    if not no_push:
        print("\nPublishing to GitHub...")
        git_push(pi_key, pi_cfg, date_str)
    else:
        print("\n[--no-push] Skipping git push.")

    print(f"Done: site/{pi_key}.html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    args = sys.argv[1:]
    pi_arg = None   # None = show selector, "all" = all missing, else a key
    force = False
    no_push = False
    api_key_arg = None

    for a in args:
        if a == "--force":
            force = True
        elif a == "--no-push":
            no_push = True
        elif a.startswith("--pi="):
            pi_arg = a.split("=", 1)[1]
        elif not a.startswith("--"):
            api_key_arg = a

    api_key = os.environ.get("HF_API_KEY") or api_key_arg
    if not api_key:
        print("Error: Hugging Face API key required.", file=sys.stderr)
        print("  Usage: python main.py hf_YOUR_KEY", file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("HF_MODEL", DEFAULT_MODEL)
    state = load_state()

    # Resolve which Pi(s) to generate
    if pi_arg is None:
        # Interactive selector
        selected_keys = show_selector(state)
        if not selected_keys:
            print("Nothing to generate.")
            sys.exit(0)
    elif pi_arg == "all":
        selected_keys = [k for k in PI_CONFIGS if not state.get(k, {}).get("done")]
        if not selected_keys:
            print("All reports already generated. Use --force to regenerate.")
            sys.exit(0)
    else:
        if pi_arg not in PI_CONFIGS:
            print(f"[ERROR] Unknown pi key '{pi_arg}'. Available: {', '.join(PI_CONFIGS)}", file=sys.stderr)
            sys.exit(1)
        selected_keys = [pi_arg]

    print(f"\nModel: {model}")
    print(f"Generating {len(selected_keys)} report(s): {', '.join(selected_keys)}\n")

    for pi_key in selected_keys:
        run_one(pi_key, api_key, model, force, no_push, state)

    print("\nAll done.")


if __name__ == "__main__":
    main()
