# bcdl

CLI tool to download your purchased Bandcamp collection.

## Install

Requires [uv](https://docs.astral.sh/uv/):

```
git clone https://github.com/natekot/bcdl.git
cd bcdl
uv sync
```

## Setup

Get your `identity` cookie from Bandcamp:

1. Log into [bandcamp.com](https://bandcamp.com)
2. Open browser DevTools → Application (Chrome) or Storage (Firefox) → Cookies → `https://bandcamp.com`
3. Copy the value of the `identity` cookie

Then run:

```
uv run bcdl configure
```

Paste the cookie value when prompted. It's saved to `~/.config/bcdl/config.json`.

## Usage

```
uv run bcdl download [options]
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--format FORMAT` | Audio format | `flac` |
| `--since YYYY-MM-DD` | Only items purchased on/after this date | — |
| `--until YYYY-MM-DD` | Only items purchased on/before this date | — |
| `--output DIR` | Output directory | `./downloads` |
| `--dry-run` | List matching items without downloading | — |

### Supported formats

`mp3-v0`, `mp3-320`, `flac`, `wav`, `aiff-lossless`, `aac-hi`, `alac`, `vorbis`

### Examples

Preview purchases from January 2025:

```
uv run bcdl download --dry-run --since 2025-01-01 --until 2025-01-31
```

Download everything since February 2026 as WAV:

```
uv run bcdl download --format wav --since 2026-02-01
```

Re-running the same command skips already-downloaded items. Album ZIPs are automatically extracted.
