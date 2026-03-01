# pi-a-day

Community documentation for Raspberry Pi bootloaders, AI-generated from forum posts, GitHub discussions, and wikis.

**Live site: https://pi-a-day.pages.dev**

## Requirements

- A [GitHub account](https://github.com/join) — the tool pushes generated reports to GitHub automatically
- Git installed and configured with your GitHub credentials
- Clone this repo:

```bash
git clone https://github.com/sintaxsaint/pi-a-day.git
cd pi-a-day
```

## Run it

```bash
pip install -r requirements.txt
python main.py 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
```

Scrapes Pi 5 bootloader sources → generates a report via MiniMax M2.5 → builds the site → pushes to GitHub (Cloudflare redeploys automatically). Only runs once per Pi model — use `--force` to regenerate.

## Options

| Flag | What it does |
|------|-------------|
| `--pi=NAME` | Pi model to generate (default: `pi5`) |
| `--force` | Re-generate even if already done |
| `--no-push` | Build locally, skip the git push |
