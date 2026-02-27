"""
collectors/behavioral.py
Uses Playwright (async) to simulate a real user session and collect:

Behavioral:
    popup_count, has_guest_checkout, click_depth_to_checkout, cart_persistence

Functional:
    has_search_autosuggest, has_quick_buy, broken_link_count, is_mobile_responsive

Strategy:
- Navigates homepage, dismisses overlays, finds a product link, traverses to checkout
- All actions are best-effort; failures degrade gracefully to -1 / 0
- Handles SPAs (React/Next.js etc.) by waiting for network idle
"""

import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

from config import (
    HEADLESS, PAGE_TIMEOUT_MS, ACTION_TIMEOUT_MS,
    VIEWPORT_DESKTOP, VIEWPORT_MOBILE, USER_AGENT, SCREENSHOT_PATH
)

log = logging.getLogger(__name__)

# ── Selectors (ordered by specificity — first match wins) ─────────────────────
CLOSE_OVERLAY_SELECTORS = [
    "[aria-label*='close' i]", "[aria-label*='dismiss' i]",
    "button:has-text('×')", "button:has-text('✕')",
    "button:has-text('Close')", "button:has-text('No thanks')",
    "button:has-text('Maybe later')", ".modal-close", ".popup-close",
    "#onetrust-accept-btn-handler",          # OneTrust cookie banner
    ".cc-btn.cc-dismiss",                    # Cookie Consent
    "[data-testid='close-button']",
    "[class*='close']", "[id*='close']",
]

CART_SELECTORS = [
    "a[href*='cart']", "a[href*='basket']", "a[href*='bag']",
    "[aria-label*='cart' i]", "[aria-label*='basket' i]",
    "[data-testid*='cart']", ".cart-icon", "#cart",
]

CHECKOUT_SELECTORS = [
    "a[href*='checkout']", "button:has-text('Checkout')",
    "button:has-text('Proceed to checkout')", "button:has-text('Go to checkout')",
    "a:has-text('Checkout')",
]

GUEST_CHECKOUT_SELECTORS = [
    "button:has-text('Guest')", "a:has-text('Guest')",
    "button:has-text('Continue as guest')", "a:has-text('Continue as guest')",
    "input[value*='guest' i]", "[data-testid*='guest']",
]

ADD_TO_CART_SELECTORS = [
    "button:has-text('Add to cart')", "button:has-text('Add to bag')",
    "button:has-text('Add to basket')", "button:has-text('Buy now')",
    "[data-testid*='add-to-cart']", ".add-to-cart", "#add-to-cart",
    "button[name*='add']",
]

PRODUCT_LINK_PATTERNS = re.compile(
    r"/(product|item|p|shop|detail|goods|pd)/", re.IGNORECASE
)

SEARCH_INPUT_SELECTORS = [
    "input[type='search']", "input[name='q']", "input[name='query']",
    "input[placeholder*='search' i]", "[aria-label*='search' i] input",
    "#search", ".search-input",
]

AUTOSUGGEST_SELECTORS = [
    ".suggestions", ".autocomplete", "[role='listbox']",
    "[data-testid*='suggest']", "[class*='suggest']", "[class*='autocomplete']",
    "[class*='dropdown']",
]

QUICK_BUY_SELECTORS = [
    "button:has-text('Buy now')", "button:has-text('Buy Now')",
    "[data-testid*='buy-now']", "[class*='buy-now']", ".quick-buy",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _safe_click(page: Page, selectors: list[str]) -> bool:
    """Try each selector; return True if one worked."""
    for sel in selectors:
        try:
            el = page.locator(sel).first
            await el.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
            await el.click(timeout=ACTION_TIMEOUT_MS)
            return True
        except Exception:
            continue
    return False


async def _dismiss_overlays(page: Page) -> int:
    """Close any popups/banners. Returns count of overlays dismissed."""
    count = 0
    for _ in range(5):          # up to 5 rounds
        dismissed = False
        for sel in CLOSE_OVERLAY_SELECTORS:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=1_500):
                    await el.click(timeout=ACTION_TIMEOUT_MS)
                    count += 1
                    dismissed = True
                    await page.wait_for_timeout(500)
                    break
            except Exception:
                continue
        if not dismissed:
            break
    return count


async def _find_product_url(page: Page, base_url: str) -> str | None:
    """
    Tries multiple strategies to find a product detail page URL:
    1. Click a clearly labelled product link
    2. Scan anchors for URL patterns that look like PDPs
    3. Click the first non-nav image link
    """
    # Strategy 1 — links whose href matches product patterns
    anchors = await page.locator("a[href]").all()
    for a in anchors[:60]:
        try:
            href = await a.get_attribute("href", timeout=500)
            if href and PRODUCT_LINK_PATTERNS.search(href):
                return urljoin(base_url, href)
        except Exception:
            continue

    # Strategy 2 — links inside product grid containers
    grid_selectors = [
        "[class*='product'] a", "[class*='item'] a",
        "[data-testid*='product'] a", ".card a", ".tile a",
    ]
    for sel in grid_selectors:
        try:
            el = page.locator(sel).first
            href = await el.get_attribute("href", timeout=1_000)
            if href:
                return urljoin(base_url, href)
        except Exception:
            continue

    # Strategy 3 — any anchor that isn't nav/footer
    for a in anchors[5:30]:
        try:
            href = await a.get_attribute("href", timeout=500)
            if href and href.startswith(("/", base_url)) and "#" not in href:
                return urljoin(base_url, href)
        except Exception:
            continue

    return None


async def _count_broken_links(page: Page, base_url: str) -> int:
    """Sample up to 10 internal nav links and count 404 responses."""
    broken = 0
    seen   = set()
    origin = urlparse(base_url).netloc

    try:
        anchors = await page.locator("nav a[href], header a[href], [class*='menu'] a[href]").all()
        for a in anchors[:10]:
            try:
                href = await a.get_attribute("href", timeout=500)
                if not href or href in seen or href.startswith(("#", "mailto:", "tel:")):
                    continue
                full = urljoin(base_url, href)
                if urlparse(full).netloc != origin:
                    continue
                seen.add(href)
                resp = await page.request.get(full, timeout=8_000)
                if resp.status == 404:
                    broken += 1
            except Exception:
                continue
    except Exception:
        pass

    return broken


# ── Main collector ─────────────────────────────────────────────────────────────

async def get_behavioral_metrics(url: str) -> dict:
    defaults = {
        "popup_count":            0,
        "has_guest_checkout":     0,
        "click_depth_to_checkout":-1,
        "cart_persistence":       0,
        "has_search_autosuggest": 0,
        "has_quick_buy":          0,
        "broken_link_count":      0,
        "is_mobile_responsive":   0,
        "page_html":              "",   # passed to trust collector
    }

    async with async_playwright() as pw:
        # ── Desktop browser ────────────────────────────────────────────────────
        browser = await pw.chromium.launch(headless=HEADLESS)
        ctx     = await browser.new_context(
            viewport=VIEWPORT_DESKTOP,
            user_agent=USER_AGENT,
            ignore_https_errors=True,
        )
        page = await ctx.new_page()
        page.set_default_timeout(PAGE_TIMEOUT_MS)

        try:
            # ── 1. Load homepage ───────────────────────────────────────────────
            await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT_MS)
            defaults["popup_count"] += await _dismiss_overlays(page)
            defaults["page_html"]    = await page.content()

            # ── 2. Broken links ────────────────────────────────────────────────
            defaults["broken_link_count"] = await _count_broken_links(page, url)

            # ── 3. Search autosuggest ──────────────────────────────────────────
            for sel in SEARCH_INPUT_SELECTORS:
                try:
                    inp = page.locator(sel).first
                    if await inp.is_visible(timeout=2_000):
                        await inp.click(timeout=ACTION_TIMEOUT_MS)
                        await inp.type("shirt", delay=80)
                        await page.wait_for_timeout(1_200)
                        for asel in AUTOSUGGEST_SELECTORS:
                            try:
                                if await page.locator(asel).first.is_visible(timeout=1_000):
                                    defaults["has_search_autosuggest"] = 1
                                    break
                            except Exception:
                                continue
                        await inp.fill("")
                        break
                except Exception:
                    continue

            # ── 4. Quick buy ───────────────────────────────────────────────────
            for sel in QUICK_BUY_SELECTORS:
                try:
                    if await page.locator(sel).first.is_visible(timeout=1_000):
                        defaults["has_quick_buy"] = 1
                        break
                except Exception:
                    continue

            # ── 5. Navigate to a product page ──────────────────────────────────
            product_url = await _find_product_url(page, url)
            click_depth = 1

            if product_url and product_url != url:
                try:
                    await page.goto(product_url, wait_until="networkidle",
                                    timeout=PAGE_TIMEOUT_MS)
                    defaults["popup_count"] += await _dismiss_overlays(page)
                    click_depth += 1

                    # Quick buy on PDP
                    if not defaults["has_quick_buy"]:
                        for sel in QUICK_BUY_SELECTORS:
                            try:
                                if await page.locator(sel).first.is_visible(timeout=1_000):
                                    defaults["has_quick_buy"] = 1
                                    break
                            except Exception:
                                continue

                    # ── 6. Add to cart ─────────────────────────────────────────
                    added = await _safe_click(page, ADD_TO_CART_SELECTORS)

                    if added:
                        await page.wait_for_timeout(1_500)
                        click_depth += 1

                        # ── 7. Go to cart ──────────────────────────────────────
                        cart_reached = await _safe_click(page, CART_SELECTORS)
                        if cart_reached:
                            await page.wait_for_load_state("networkidle",
                                                           timeout=PAGE_TIMEOUT_MS)
                            defaults["popup_count"] += await _dismiss_overlays(page)
                            click_depth += 1

                            # ── 8. Go to checkout ──────────────────────────────
                            checkout_reached = await _safe_click(page, CHECKOUT_SELECTORS)
                            if checkout_reached:
                                await page.wait_for_load_state("networkidle",
                                                               timeout=PAGE_TIMEOUT_MS)
                                defaults["popup_count"] += await _dismiss_overlays(page)
                                click_depth += 1
                                defaults["click_depth_to_checkout"] = click_depth

                                # ── 9. Guest checkout ───────────────────────────
                                for sel in GUEST_CHECKOUT_SELECTORS:
                                    try:
                                        if await page.locator(sel).first.is_visible(
                                                timeout=2_000):
                                            defaults["has_guest_checkout"] = 1
                                            break
                                    except Exception:
                                        continue

                except Exception as e:
                    log.debug(f"[Behavioral] checkout traversal failed: {e}")

            # ── 10. Screenshot for Gemini ──────────────────────────────────────
            try:
                await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT_MS)
                await page.screenshot(path=SCREENSHOT_PATH, full_page=False)
            except Exception:
                pass

        except Exception as e:
            log.warning(f"[Behavioral] fatal for {url}: {e}")

        finally:
            await ctx.close()

        # ── 11. Cart persistence test (fresh context = new browser session) ────
        ctx2 = await browser.new_context(
            viewport=VIEWPORT_DESKTOP,
            user_agent=USER_AGENT,
            ignore_https_errors=True,
        )
        page2 = await ctx2.new_page()
        try:
            cart_url = urljoin(url, "/cart")
            await page2.goto(cart_url, wait_until="networkidle",
                             timeout=PAGE_TIMEOUT_MS)
            body = (await page2.inner_text("body")).lower()
            # If cart page references items / quantity it likely persisted via cookies
            if any(kw in body for kw in ["item", "product", "quantity", "subtotal"]):
                defaults["cart_persistence"] = 1
        except Exception:
            pass
        finally:
            await ctx2.close()

        # ── 12. Mobile responsiveness ──────────────────────────────────────────
        ctx3 = await browser.new_context(
            viewport=VIEWPORT_MOBILE,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            ignore_https_errors=True,
        )
        page3 = await ctx3.new_page()
        try:
            await page3.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT_MS)
            # Check for horizontal scroll (a sign of broken mobile layout)
            scroll_width  = await page3.evaluate("document.body.scrollWidth")
            viewport_width = VIEWPORT_MOBILE["width"]
            defaults["is_mobile_responsive"] = int(scroll_width <= viewport_width + 20)
        except Exception:
            pass
        finally:
            await ctx3.close()
            await browser.close()

    return defaults
