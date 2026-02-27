"""
collectors/trust.py
Scrapes homepage + footer HTML for trust & legitimacy signals.
Works on static and server-rendered HTML passed in as a string.

Returns:
    has_phone, has_email, has_address,
    has_return_policy, has_privacy_policy, has_tos,
    has_social_links, has_payment_badges, trust_score (0-8)
"""

import re
import logging
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# ── Patterns ───────────────────────────────────────────────────────────────────
PHONE_RE   = re.compile(r"(\+?\d[\d\s\-\(\)]{7,}\d)")
EMAIL_RE   = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
ADDRESS_KW = ["street", "avenue", "suite", "floor", "po box", "zip", "postal"]

POLICY_KW  = {
    "has_return_policy":  ["return", "refund", "exchange"],
    "has_privacy_policy": ["privacy policy", "privacy"],
    "has_tos":            ["terms of service", "terms & conditions", "terms and conditions"],
}

SOCIAL_DOMAINS = ["instagram.com", "facebook.com", "twitter.com", "tiktok.com",
                  "youtube.com", "pinterest.com", "linkedin.com"]

PAYMENT_KW = ["visa", "mastercard", "paypal", "amex", "american express",
              "apple pay", "google pay", "stripe", "norton", "mcafee", "ssl"]


def _text(soup: BeautifulSoup) -> str:
    return soup.get_text(" ", strip=True).lower()


def get_trust_signals(html: str) -> dict:
    defaults = {
        "has_phone":          0,
        "has_email":          0,
        "has_address":        0,
        "has_return_policy":  0,
        "has_privacy_policy": 0,
        "has_tos":            0,
        "has_social_links":   0,
        "has_payment_badges": 0,
        "trust_score":        0,
    }

    if not html:
        return defaults

    try:
        soup   = BeautifulSoup(html, "lxml")
        text   = _text(soup)

        # Contact info
        defaults["has_phone"]   = int(bool(PHONE_RE.search(text)))
        defaults["has_email"]   = int(bool(EMAIL_RE.search(text)))
        defaults["has_address"] = int(any(kw in text for kw in ADDRESS_KW))

        # Policy pages — check link text and href
        all_links = [(a.get_text(" ", strip=True).lower(), (a.get("href") or "").lower())
                     for a in soup.find_all("a", href=True)]

        for field, keywords in POLICY_KW.items():
            defaults[field] = int(
                any(
                    any(kw in link_text or kw in href for kw in keywords)
                    for link_text, href in all_links
                )
            )

        # Social links
        defaults["has_social_links"] = int(
            any(domain in href for _, href in all_links for domain in SOCIAL_DOMAINS)
        )

        # Payment badges — check images alt/src and visible text
        img_alts = " ".join(
            (img.get("alt") or "").lower() + " " + (img.get("src") or "").lower()
            for img in soup.find_all("img")
        )
        combined = text + " " + img_alts
        defaults["has_payment_badges"] = int(
            any(kw in combined for kw in PAYMENT_KW)
        )

        defaults["trust_score"] = sum(
            v for k, v in defaults.items() if k.startswith("has_")
        )

    except Exception as e:
        log.warning(f"[Trust] parsing failed → {e}")

    return defaults
