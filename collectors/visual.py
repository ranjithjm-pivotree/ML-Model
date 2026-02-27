"""
collectors/visual.py
Takes a full-page screenshot and asks Gemini to rate UI quality.

Returns:
    visual_clutter_score (1-10, higher = more cluttered),
    visual_modern_score  (1-10, higher = more modern),
    visual_image_quality (1-10),
    visual_overall       (1-10)
"""

import json
import logging
import re
from pathlib import Path

import google.generativeai as genai
from PIL import Image

from config import GEMINI_API_KEY, GEMINI_MODEL, SCREENSHOT_PATH

genai.configure(api_key=GEMINI_API_KEY)
log = logging.getLogger(__name__)

PROMPT = """You are an expert UX auditor evaluating e-commerce websites.
Analyse this full-page screenshot and return ONLY a JSON object (no markdown, no explanation):

{
  "clutter_score":   <1-10, 1=very clean with lots of whitespace, 10=extremely cluttered>,
  "modern_score":    <1-10, 1=looks outdated/amateurish, 10=modern and professional>,
  "image_quality":   <1-10, 1=pixelated/low-res images, 10=crisp high-res product photos>,
  "overall_visual":  <1-10, weighted average reflecting overall visual trustworthiness>
}
"""


def get_visual_scores(screenshot_path: str = SCREENSHOT_PATH) -> dict:
    defaults = {
        "visual_clutter_score": -1,
        "visual_modern_score":  -1,
        "visual_image_quality": -1,
        "visual_overall":       -1,
    }

    try:
        if not Path(screenshot_path).exists():
            log.warning("[Visual] Screenshot not found.")
            return defaults

        img   = Image.open(screenshot_path)
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp  = model.generate_content([PROMPT, img])
        raw   = resp.text.strip()

        # Strip markdown code fences if model wraps in them
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        scores = json.loads(raw)
        return {
            "visual_clutter_score": scores.get("clutter_score",   -1),
            "visual_modern_score":  scores.get("modern_score",    -1),
            "visual_image_quality": scores.get("image_quality",   -1),
            "visual_overall":       scores.get("overall_visual",  -1),
        }

    except Exception as e:
        log.warning(f"[Visual] Gemini scoring failed → {e}")
        return defaults
