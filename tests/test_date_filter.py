from datetime import datetime, timedelta, timezone

from bcdl.cli import filter_items


def gmt(local: datetime) -> str:
    """Format a naive local datetime the way Bandcamp reports purchase times.

    Bandcamp stamps purchases in GMT, so a local evening purchase often lands
    on the following calendar day in the reported string.
    """
    return (
        local.astimezone()
        .astimezone(timezone.utc)
        .strftime("%d %b %Y %H:%M:%S GMT")
    )


def item(local: datetime, title: str = "Some Album") -> dict:
    return {
        "purchased": gmt(local),
        "download_available": True,
        "band_name": "Some Artist",
        "album_title": title,
        "sale_item_id": 1,
    }


def titles(items):
    return [i["album_title"] for i in items]


def test_until_includes_purchase_made_that_evening_local():
    """The bug: an 18:13 local purchase is 00:13 GMT the next day."""
    evening = item(datetime(2026, 8, 7, 18, 13), "Evening Buy")

    result = filter_items([evening], since="2026-08-07", until="2026-08-07")

    assert titles(result) == ["Evening Buy"]


def test_until_includes_last_second_of_that_local_day():
    late = item(datetime(2026, 8, 7, 23, 59, 59), "Late Buy")

    result = filter_items([late], until="2026-08-07")

    assert titles(result) == ["Late Buy"]


def test_until_excludes_start_of_next_local_day():
    next_day = item(datetime(2026, 8, 8, 0, 0, 0), "Next Day")

    result = filter_items([next_day], until="2026-08-07")

    assert result == []


def test_since_includes_midnight_of_that_local_day():
    midnight = item(datetime(2026, 8, 7, 0, 0, 0), "Midnight Buy")

    result = filter_items([midnight], since="2026-08-07")

    assert titles(result) == ["Midnight Buy"]


def test_since_excludes_previous_local_day():
    previous = item(datetime(2026, 8, 6, 23, 59, 59), "Previous Day")

    result = filter_items([previous], since="2026-08-07")

    assert result == []


def test_single_day_window_selects_only_that_local_day():
    items = [
        item(datetime(2026, 8, 6, 20, 0), "Day Before"),
        item(datetime(2026, 8, 7, 9, 30), "Morning"),
        item(datetime(2026, 8, 7, 18, 13), "Evening"),
        item(datetime(2026, 8, 8, 10, 0), "Day After"),
    ]

    result = filter_items(items, since="2026-08-07", until="2026-08-07")

    assert titles(result) == ["Morning", "Evening"]


def test_skips_items_without_download_available():
    unavailable = item(datetime(2026, 8, 7, 12, 0), "No Download")
    unavailable["download_available"] = False

    result = filter_items([unavailable], since="2026-08-07", until="2026-08-07")

    assert result == []


def test_skips_items_with_unparseable_date():
    broken = item(datetime(2026, 8, 7, 12, 0), "Broken Date")
    broken["purchased"] = "not a date"
    broken.pop("added", None)

    result = filter_items([broken], since="2026-08-07", until="2026-08-07")

    assert result == []


def test_no_bounds_returns_all_downloadable_items():
    items = [
        item(datetime(2020, 1, 1, 12, 0), "Old"),
        item(datetime(2026, 8, 7, 12, 0), "New"),
    ]

    result = filter_items(items)

    assert titles(result) == ["Old", "New"]


def test_dst_boundary_day_uses_that_days_offset():
    """A date's local offset must be resolved for that date, not today's."""
    winter = item(datetime(2026, 1, 15, 18, 30), "Winter Buy")

    result = filter_items([winter], since="2026-01-15", until="2026-01-15")

    assert titles(result) == ["Winter Buy"]


def test_window_spanning_multiple_days_is_inclusive_on_both_ends():
    items = [
        item(datetime(2026, 8, 6, 23, 0), "First Day Late"),
        item(datetime(2026, 8, 7, 12, 0), "Middle"),
        item(datetime(2026, 8, 8, 22, 0), "Last Day Late"),
        item(datetime(2026, 8, 9, 1, 0), "Outside"),
    ]

    result = filter_items(items, since="2026-08-06", until="2026-08-08")

    assert titles(result) == ["First Day Late", "Middle", "Last Day Late"]
