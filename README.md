# pi-a-day

Fetches the latest community and unofficial documentation on how the **Raspberry Pi 5 bootloader** works — an area with little official documentation — uses **MiniMax M2.5** (free via Hugging Face) to generate a clean technical report, and publishes it to a **Cloudflare Pages** website automatically.

Run it once per Pi model. It tracks what's been done and won't re-run unless you `--force` it.

## How it works

1. Scrapes these Pi 5 boot sources:
   - [Pi5 Boot Process — Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=373222)
   - [kernel_2712.img — DeepWiki](https://deepwiki.com/raspberrypi/firmware/2.1.5-raspberry-pi-5-kernel-(kernel_2712.img))
   - [Supporting Pi 5 — Circle Discussion #413](https://github.com/rsta2/circle/discussions/413)
   - [UART on Pi 5 GPIO 14/15 — Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=378931)
2. Sends the collected text to [MiniMaxAI/MiniMax-M2.5](https://huggingface.co/MiniMaxAI/MiniMax-M2.5) via the Hugging Face Inference API.
3. Converts the report to HTML and writes it into `site/`.
4. Commits and pushes to GitHub — Cloudflare Pages deploys automatically.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Connect to Cloudflare Pages (one-time)

1. Go to [Cloudflare Pages](https://pages.cloudflare.com/) → **Create a project** → **Connect to Git**
2. Select this repository
3. Set **Build settings**:
   - Build command: *(leave empty)*
   - Build output directory: `site`
4. Click **Save and Deploy**

That's it. Every time the tool pushes to GitHub, Cloudflare Pages rebuilds automatically.

### 3. Run the tool

```bash
python main.py hf_YOUR_API_KEY
```

Or via environment variable:

```bash
HF_API_KEY=hf_YOUR_API_KEY python main.py
```

Get a free Hugging Face API key at: https://huggingface.co/settings/tokens

## Usage

```
python main.py [HF_API_KEY] [--pi=pi5] [--force] [--no-push]
```

| Flag | Description |
|------|-------------|
| `--pi=NAME` | Pi model to generate (default: `pi5`) |
| `--force` | Re-generate even if already done |
| `--no-push` | Write files locally, skip the git push |

| Env var | Description |
|---------|-------------|
| `HF_API_KEY` | Hugging Face API key |
| `HF_MODEL` | Override model ID (default: `MiniMaxAI/MiniMax-M2.5`) |

## Output

After running:
- `site/pi5.html` — rendered report (served by Cloudflare Pages)
- `site/pi5-report.md` — raw markdown (downloadable from the site)
- `site/index.html` — index listing all completed reports
- `pi5-bootloader-report.md` — raw markdown at repo root
- `state.json` — tracks which Pi models have been done
