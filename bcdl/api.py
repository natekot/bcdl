import html as html_module
import json
import re
import time

import requests

BASE_URL = "https://bandcamp.com"


def make_session(identity: str) -> requests.Session:
    session = requests.Session()
    session.cookies.set("identity", identity, domain=".bandcamp.com")
    session.headers["User-Agent"] = "bcdl/0.1.0"
    return session


def get_fan_id(session: requests.Session) -> int:
    resp = session.get(f"{BASE_URL}/api/fan/2/collection_summary")
    resp.raise_for_status()
    data = resp.json()
    return data["fan_id"]


def get_collection_items(
    session: requests.Session, fan_id: int
) -> tuple[list[dict], dict[str, str]]:
    """Fetch all purchased items and their redownload URLs.

    Returns (items, redownload_urls) where redownload_urls maps
    "p{sale_item_id}" to download page URLs.
    """
    items = []
    seen_sale_ids: set[int] = set()
    redownload_urls: dict[str, str] = {}

    # Seed with a future token so we get the most recent items first
    older_than_token = f"{int(time.time()) + 86400}::a::"

    while True:
        payload = {
            "fan_id": fan_id,
            "count": 100,
            "older_than_token": older_than_token,
        }

        resp = session.post(
            f"{BASE_URL}/api/fancollection/1/collection_items",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        batch = data.get("items", [])
        if not batch:
            break

        for item in batch:
            sid = item.get("sale_item_id")
            if sid not in seen_sale_ids:
                seen_sale_ids.add(sid)
                items.append(item)

        redownload_urls.update(data.get("redownload_urls", {}))

        if not data.get("more_available", False):
            break

        older_than_token = data.get("last_token")
        if not older_than_token:
            break

    return items, redownload_urls


def get_download_url(
    session: requests.Session,
    download_page_url: str,
    format_key: str,
) -> str | None:
    """Fetch the download page and extract the direct download URL for the format."""
    resp = session.get(download_page_url)
    resp.raise_for_status()

    match = re.search(r'data-blob="([^"]*)"', resp.text)
    if not match:
        match = re.search(r"data-blob='([^']*)'", resp.text)
    if not match:
        return None

    blob = json.loads(html_module.unescape(match.group(1)))

    digital_items = blob.get("digital_items", [])
    if not digital_items:
        return None

    downloads = digital_items[0].get("downloads", {})
    format_info = downloads.get(format_key)
    if not format_info:
        return None

    return format_info.get("url")
