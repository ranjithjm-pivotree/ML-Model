"""
main.py — E-commerce website data collection pipeline.

Usage:
    python main.py --urls urls.txt --output ecommerce_dataset.csv
    python main.py --url https://example.com

For each URL the pipeline:
1. Runs Playwright (behavioral + functional + screenshot)
2. Calls PageSpeed API (performance)
3. Scrapes HTML with BeautifulSoup (trust)
4. Calls Gemini Vision (visual quality)
5. Appends one row to the output CSV
"""

import argparse
import asyncio
import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# Collectors
from collectors.behavioral import get_behavioral_metrics
from collectors.performance import get_performance_metrics
from collectors.trust       import get_trust_signals
from collectors.visual      import get_visual_scores
from config import OUTPUT_CSV

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)),
        logging.FileHandler("scraper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("pipeline")


# ── Column order (matches ML feature expectations) ────────────────────────────
COLUMNS = [
    # Meta
    "url", "collected_at",
    # Behavioral
    "popup_count", "has_guest_checkout", "click_depth_to_checkout", "cart_persistence",
    # Functional
    "has_search_autosuggest", "has_quick_buy", "broken_link_count", "is_mobile_responsive",
    # Performance
    "lcp_ms", "cls", "tbt_ms", "ttfb_ms", "performance_score",
    # Trust
    "has_phone", "has_email", "has_address",
    "has_return_policy", "has_privacy_policy", "has_tos",
    "has_social_links", "has_payment_badges", "trust_score",
    # Visual
    "visual_clutter_score", "visual_modern_score", "visual_image_quality", "visual_overall",
    # Label (to be filled manually or by a separate labelling script)
    "label",
]


async def collect_one(url: str) -> dict:
    """Collect all metrics for a single URL. Returns a flat dict."""
    log.info(f">> Starting: {url}")
    row = {"url": url, "collected_at": datetime.utcnow().isoformat(), "label": ""}

    # ── 1. Behavioral + functional (also captures HTML + screenshot) ───────────
    log.info("  [1/4] Behavioral & functional (Playwright)…")
    beh = await get_behavioral_metrics(url)
    page_html = beh.pop("page_html", "")
    row.update(beh)

    # ── 2. Performance ─────────────────────────────────────────────────────────
    log.info("  [2/4] Performance (PageSpeed API)…")
    row.update(get_performance_metrics(url))

    # ── 3. Trust signals ───────────────────────────────────────────────────────
    log.info("  [3/4] Trust signals (BeautifulSoup)…")
    row.update(get_trust_signals(page_html))

    # ── 4. Visual quality ──────────────────────────────────────────────────────
    log.info("  [4/4] Visual quality (Gemini)…")
    row.update(get_visual_scores())

    log.info(f"  Done: {url}")
    return row


def save_row(row: dict, output_path: str):
    """Append a single row to the CSV, writing header if file is new."""
    path     = Path(output_path)
    is_new   = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        if is_new:
            writer.writeheader()
        writer.writerow(row)


async def run_pipeline(urls: list[str], output: str, delay: float = 2.0):
    """Process all URLs sequentially with a polite delay between requests."""
    log.info(f"Pipeline starting - {len(urls)} URL(s) -> {output}")

    for url in tqdm(urls, desc="Sites"):
        url = url.strip()
        if not url or url.startswith("#"):
            continue
        try:
            row = await collect_one(url)
            save_row(row, output)
        except Exception as e:
            log.error(f"Failed for {url}: {e}", exc_info=True)
            # Save a blank row so we know it was attempted
            save_row({"url": url, "collected_at": datetime.utcnow().isoformat()}, output)

        await asyncio.sleep(delay)   # polite delay between sites

    log.info(f"Pipeline complete. Data saved to: {output}")

    # Print summary
    try:
        df = pd.read_csv(output)
        log.info(f"\nDataset shape: {df.shape}")
        log.info(f"Columns: {list(df.columns)}")
    except Exception:
        pass


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Collect e-commerce website metrics for ML training"
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--url",  type=str, help="Single URL to collect")
    group.add_argument("--urls", type=str, help="Path to a text file with one URL per line")
    p.add_argument("--output", type=str, default=OUTPUT_CSV,
                   help=f"Output CSV path (default: {OUTPUT_CSV})")
    p.add_argument("--delay", type=float, default=2.0,
                   help="Seconds to wait between sites (default: 2)")
    return p.parse_args()


if __name__ == "__main__":
    args  = parse_args()
    urls  = [args.url] if args.url else Path(args.urls).read_text().splitlines()
    urls  = [u.strip() for u in urls if u.strip() and not u.startswith("#")]
    asyncio.run(run_pipeline(urls, args.output, args.delay))
