# E-Commerce Website Data Collection Pipeline

Collects 25+ features per website for ML-based "good vs bad" classification.

## Quick Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Set your API keys (or edit config.py directly)
export PAGESPEED_API_KEY="your_key_here"
export GEMINI_API_KEY="your_key_here"

# 3. Add URLs to urls.txt (one per line)

# 4. Run the pipeline
python main.py --urls urls.txt --output ecommerce_dataset.csv

# Single URL test
python main.py --url https://www.nike.com

# 5. Label the results interactively
python label.py --input ecommerce_dataset.csv
```

## Output CSV Columns

| Column | Type | Description |
|--------|------|-------------|
| url | str | Website URL |
| popup_count | int | # of overlays dismissed |
| has_guest_checkout | 0/1 | Guest checkout available |
| click_depth_to_checkout | int | Clicks from homepage to payment (-1 if unreachable) |
| cart_persistence | 0/1 | Cart survives new browser session |
| has_search_autosuggest | 0/1 | Dropdown suggestions on search |
| has_quick_buy | 0/1 | Buy Now button bypasses cart |
| broken_link_count | int | # of nav links returning 404 |
| is_mobile_responsive | 0/1 | No horizontal overflow on 390px |
| lcp_ms | float | Largest Contentful Paint (ms) |
| cls | float | Cumulative Layout Shift |
| tbt_ms | float | Total Blocking Time (ms) |
| ttfb_ms | float | Time to First Byte (ms) |
| performance_score | float | PageSpeed score 0-100 |
| has_phone | 0/1 | Phone number present |
| has_email | 0/1 | Email address present |
| has_address | 0/1 | Physical address present |
| has_return_policy | 0/1 | Return/refund policy link |
| has_privacy_policy | 0/1 | Privacy policy link |
| has_tos | 0/1 | Terms of service link |
| has_social_links | 0/1 | Social media links present |
| has_payment_badges | 0/1 | Visa/PayPal/etc logos visible |
| trust_score | int | Sum of 8 trust signals (0-8) |
| visual_clutter_score | 1-10 | 1=clean, 10=cluttered |
| visual_modern_score | 1-10 | 1=outdated, 10=modern |
| visual_image_quality | 1-10 | Product image quality |
| visual_overall | 1-10 | Overall visual trustworthiness |
| label | str | "good" or "bad" (manual) |

## Architecture

```
main.py
├── collectors/behavioral.py  ← Playwright (dynamic browser)
├── collectors/performance.py ← PageSpeed Insights API  
├── collectors/trust.py       ← BeautifulSoup (HTML parsing)
└── collectors/visual.py      ← Gemini 2.5 Flash (vision)
```

## Tips

- Run with `HEADLESS=False` in `config.py` to watch the browser during debugging
- Sites may block headless browsers; the pipeline handles failures gracefully (returns -1)
- Aim for 50-100 labelled URLs minimum before training a model
- Balance your dataset: roughly equal "good" and "bad" examples
