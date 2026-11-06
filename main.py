"""One RSS check per run; send the most newsworthy fresh story if available."""

import argparse
import sys
import time
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from bale import format_post, send_post
from config import FEEDS, get_settings
from feeds import fetch_article_details, fetch_feed, fingerprint_keys, summarize_news
from news_rules import importance
from state import load_history, save_history


def run_once(settings):
    """Existing one-story-per-run workflow; NO daily quota or spacing restrictions."""
    now = datetime.now(timezone.utc)
    history = load_history()
    items = []
    feed_successes = 0
    for source, url in FEEDS.items():
        try:
            feed_items = fetch_feed(source, url)
            feed_successes += 1
            items.extend(feed_items)
            print(f"[RSS] {source}: {len(feed_items)} items")
        except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError, ValueError) as exc:
            print(f"[WARN] {source}: {type(exc).__name__}: {exc}")

    if feed_successes == 0:
        raise RuntimeError("All RSS feeds failed")

    candidates = []
    for item in items:
        age = now - item["published"]
        if not -timedelta(minutes=10) <= age <= timedelta(hours=settings["max_age_hours"]):
            continue
        if any(key in history for key in fingerprint_keys(item)):
            continue
        score, worth_publishing = importance(item)
        if not worth_publishing:
            print(f"[SKIP LOW-IMPACT] {item['title']}")
            continue
        candidates.append((score, item))

    if not candidates:
        print("[INFO] No fresh meaningful news; nothing sent.")
        return None

    # Important news wins; ties go to the most recent item.
    score, selected = max(candidates, key=lambda pair: (pair[0], pair[1]["published"]))
    print(f"[SELECTED importance={score}] {selected['title']}")

    rss_summary = summarize_news(selected.get("summary", ""))
    try:
        details = fetch_article_details(selected["link"])
        selected["summary"] = details["summary"] or rss_summary
        selected["photo"] = selected.get("photo") or details["photo"]
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, ValueError) as exc:
        print(f"[WARN] Article details unavailable: {type(exc).__name__}")
        selected["summary"] = rss_summary

    if settings["preview"]:
        print("[PREVIEW] No message sent.\n")
        print(format_post(selected))
        print("\n[IMAGE]", selected.get("photo") or "No image found")
        return selected

    # Keep deduplication behavior: record only after successful API delivery.
    result = send_post(settings["bot_token"], settings["channel"], selected)
    for key in fingerprint_keys(selected):
        history[key] = time.time()
    save_history(history)
    print(f"[SENT] {result}: {selected['source']} / {selected['title']}")
    return selected


def main():
    parser = argparse.ArgumentParser(description="Check RSS and publish one important Bale news story.")
    parser.add_argument("--preview", action="store_true", help="Preview without publishing")
    args = parser.parse_args()
    run_once(get_settings(preview=args.preview))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
