import re
import zipfile
from pathlib import Path
from urllib.parse import unquote

import requests
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TransferSpeedColumn,
)


def sanitize(name: str) -> str:
    """Remove characters that are problematic in file paths."""
    for ch in r'<>:"/\|?*':
        name = name.replace(ch, "_")
    return name.strip(". ")


def _parse_filename(headers: dict, url: str) -> str:
    """Extract filename from response headers or URL."""
    cd = headers.get("Content-Disposition", "")
    if cd:
        match = re.search(r"filename\*=UTF-8''(.+?)(?:;|$)", cd)
        if match:
            return unquote(match.group(1).strip())
        match = re.search(r'filename="?([^";]+)"?', cd)
        if match:
            return match.group(1).strip()
    name = unquote(url.split("/")[-1].split("?")[0])
    return name or "download"


def item_exists(artist: str, title: str, output_dir: Path) -> bool:
    """Check if an item has already been downloaded."""
    folder_name = sanitize(f"{artist} - {title}")
    dest_dir = output_dir / folder_name
    if not dest_dir.exists():
        return False
    # Consider it downloaded if the folder has any non-empty files
    return any(f.stat().st_size > 0 for f in dest_dir.iterdir() if f.is_file())


def download_item(
    session: requests.Session,
    url: str,
    artist: str,
    title: str,
    output_dir: Path,
    progress: Progress,
) -> Path:
    """Download a file from `url` into output_dir/artist - title/."""
    folder_name = sanitize(f"{artist} - {title}")
    dest_dir = output_dir / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    resp = session.get(url, stream=True)
    resp.raise_for_status()

    filename = sanitize(_parse_filename(resp.headers, url))
    dest = dest_dir / filename

    total = int(resp.headers.get("Content-Length", 0)) or None
    task = progress.add_task(f"{artist} - {title}", total=total)

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            f.write(chunk)
            progress.update(task, advance=len(chunk))

    if dest.suffix.lower() == ".zip":
        _extract_and_remove_zip(dest)

    return dest


def _extract_and_remove_zip(zip_path: Path) -> None:
    dest_dir = zip_path.parent
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    zip_path.unlink()


def make_progress() -> Progress:
    return Progress(
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
    )
