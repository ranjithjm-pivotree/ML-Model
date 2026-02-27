"""
collectors/performance.py
Fetches Core Web Vitals via Google PageSpeed Insights API.
Returns: lcp_ms, cls, tbt_ms, ttfb_ms, performance_score
"""

import requests
import logging
from config import PAGESPEED_API_KEY, PAGESPEED_URL, PAGESPEED_STRATEGY

log = logging.getLogger(__name__)


def get_performance_metrics(url: str) -> dict:
    """
    Calls the PageSpeed Insights API and extracts key performance metrics.
    All values default to -1 on failure so the row is still usable in ML.
    """
    defaults = {
        "lcp_ms":            -1,
        "cls":               -1,
        "tbt_ms":            -1,
        "ttfb_ms":           -1,
        "performance_score": -1,
    }

    try:
        params = {
            "url":      url,
            "key":      PAGESPEED_API_KEY,
            "strategy": PAGESPEED_STRATEGY,
        }
        resp = requests.get(PAGESPEED_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        cats   = data.get("lighthouseResult", {}).get("categories", {})
        audits = data.get("lighthouseResult", {}).get("audits", {})

        def audit_val(key, field="numericValue"):
            return audits.get(key, {}).get(field, -1)

        return {
            "lcp_ms":            round(audit_val("largest-contentful-paint"), 2),
            "cls":               round(audit_val("cumulative-layout-shift"), 4),
            "tbt_ms":            round(audit_val("total-blocking-time"), 2),
            "ttfb_ms":           round(audit_val("server-response-time"), 2),
            "performance_score": round(
                cats.get("performance", {}).get("score", -1) * 100, 1
            ),
        }

    except Exception as e:
        log.warning(f"[Performance] {url} → {e}")
        return defaults
