"""
config.py — Central configuration for the e-commerce data collection pipeline.
Set your API keys here or via environment variables.
"""

import os

# ── API Keys ──────────────────────────────────────────────────────────────────
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY", "AIzaSyDQA-4swGWir8Xnn7Z0Ld9QwBsOKqgtfWA")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY",    "AIzaSyDQA-4swGWir8Xnn7Z0Ld9QwBsOKqgtfWA")

# ── Playwright Settings ────────────────────────────────────────────────────────
HEADLESS          = True          # Set False to watch the browser during debugging
PAGE_TIMEOUT_MS   = 30_000        # 30 s per navigation
ACTION_TIMEOUT_MS = 5_000         # 5 s per element interaction
VIEWPORT_DESKTOP  = {"width": 1440, "height": 900}
VIEWPORT_MOBILE   = {"width": 390,  "height": 844}   # iPhone 14 Pro
USER_AGENT        = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ── PageSpeed API ──────────────────────────────────────────────────────────────
PAGESPEED_URL     = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PAGESPEED_STRATEGY = "mobile"    # "mobile" | "desktop"

# ── Gemini Vision ──────────────────────────────────────────────────────────────
GEMINI_MODEL      = "gemini-2.5-flash"
SCREENSHOT_PATH   = "/tmp/ecom_screenshot.png"

# ── Output ─────────────────────────────────────────────────────────────────────
OUTPUT_CSV        = "ecommerce_dataset.csv"
