import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import api, config, downloader

FORMATS = [
    "mp3-v0",
    "mp3-320",
    "flac",
    "wav",
    "aiff-lossless",
    "aac-hi",
    "alac",
    "vorbis",
]

console = Console()


def cmd_configure(_args: argparse.Namespace) -> None:
    console.print("Paste your Bandcamp [bold]identity[/bold] cookie value:")
    identity = input("> ").strip()
    if not identity:
        console.print("[red]No value provided, aborting.[/red]")
        sys.exit(1)

    config.set_identity_cookie(identity)
    console.print(f"[green]Saved to {config.CONFIG_FILE}[/green]")

    try:
        session = api.make_session(identity)
        fan_id = api.get_fan_id(session)
        console.print(f"[green]Authenticated — fan_id: {fan_id}[/green]")
    except Exception as e:
        console.print(f"[yellow]Warning: could not verify cookie: {e}[/yellow]")


def cmd_download(args: argparse.Namespace) -> None:
    identity = config.get_identity_cookie()
    if not identity:
        console.print("[red]No identity cookie configured. Run 'bcdl configure' first.[/red]")
        sys.exit(1)

    session = api.make_session(identity)

    console.print("Fetching fan ID...")
    try:
        fan_id = api.get_fan_id(session)
    except Exception as e:
        console.print(f"[red]Failed to authenticate: {e}[/red]")
        sys.exit(1)

    console.print(f"Fan ID: {fan_id}")
    console.print("Fetching collection...")

    items, redownload_urls = api.get_collection_items(session, fan_id)
    console.print(f"Found {len(items)} items in collection.")

    filtered = filter_items(items, since=args.since, until=args.until)

    console.print(f"{len(filtered)} items match the date filter.")

    if not filtered:
        return

    if args.dry_run:
        print_items_table(filtered)
        return

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    progress = downloader.make_progress()
    with progress:
        for item in filtered:
            artist = item.get("band_name", "Unknown Artist")
            title = item.get("album_title") or item.get("item_title", "Unknown")

            if downloader.item_exists(artist, title, output_dir):
                console.print(f"[dim]  Already exists, skipping {artist} - {title}[/dim]")
                continue

            # Look up the redownload URL for this item
            sale_key = f"p{item['sale_item_id']}"
            download_page_url = redownload_urls.get(sale_key)
            if not download_page_url:
                console.print(f"[yellow]  No download page for {artist} - {title}[/yellow]")
                continue

            console.print(f"\nGetting download link for [bold]{artist} - {title}[/bold]...")
            try:
                url = api.get_download_url(session, download_page_url, args.format)
            except Exception as e:
                console.print(f"[red]  Failed to get download URL: {e}[/red]")
                continue

            if not url:
                console.print(f"[yellow]  No download available for format '{args.format}'[/yellow]")
                continue

            try:
                dest = downloader.download_item(session, url, artist, title, output_dir, progress)
                console.print(f"[green]  Saved to {dest}[/green]")
            except Exception as e:
                console.print(f"[red]  Download failed: {e}[/red]")


def day_start(s: str) -> datetime:
    """Midnight local time on the given date.

    Calling astimezone() on a naive datetime reads it as local time and picks
    the UTC offset in effect on that date, so DST is handled per-date rather
    than using today's offset.
    """
    return datetime.strptime(s, "%Y-%m-%d").astimezone()


def day_after(s: str) -> datetime:
    """Midnight local time on the day following the given date."""
    return (datetime.strptime(s, "%Y-%m-%d") + timedelta(days=1)).astimezone()


def filter_items(
    items: list[dict], since: str | None = None, until: str | None = None
) -> list[dict]:
    """Select downloadable items purchased within the local-time date range.

    Both bounds are inclusive whole local days. Bandcamp reports purchase
    times in GMT, so an evening purchase is stamped with the next calendar
    day; comparing against local day boundaries keeps --since/--until
    meaning the days the user actually saw on the clock.
    """
    start = day_start(since) if since else None
    end = day_after(until) if until else None

    matched = []
    for item in items:
        if not item.get("download_available"):
            continue
        purchased = parse_item_date(item)
        if purchased is None:
            continue
        if start and purchased < start:
            continue
        if end and purchased >= end:
            continue
        matched.append(item)

    return matched


def parse_item_date(item: dict) -> datetime | None:
    purchased = item.get("purchased")
    if purchased:
        try:
            return datetime.strptime(purchased, "%d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    added = item.get("added")
    if added and isinstance(added, str):
        try:
            return datetime.strptime(added, "%d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return None


def print_items_table(items: list[dict]) -> None:
    table = Table(title="Matching Items")
    table.add_column("#", style="dim")
    table.add_column("Artist")
    table.add_column("Title")
    table.add_column("Purchased")

    for i, item in enumerate(items, 1):
        artist = item.get("band_name", "?")
        title = item.get("album_title") or item.get("item_title", "?")
        date = item.get("purchased") or "?"
        table.add_row(str(i), artist, title, date)

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(prog="bcdl", description="Bandcamp Collection Downloader")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("configure", help="Set identity cookie")

    dl = sub.add_parser("download", help="Download from collection")
    dl.add_argument("--format", default="flac", choices=FORMATS, help="Audio format (default: flac)")
    dl.add_argument("--since", help="Only items purchased on/after this date (YYYY-MM-DD)")
    dl.add_argument("--until", help="Only items purchased on/before this date (YYYY-MM-DD)")
    dl.add_argument("--output", default="./downloads", help="Output directory (default: ./downloads)")
    dl.add_argument("--dry-run", action="store_true", help="List matching items without downloading")

    args = parser.parse_args()

    if args.command == "configure":
        cmd_configure(args)
    elif args.command == "download":
        cmd_download(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
