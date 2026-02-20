import os
import requests
from dotenv import load_dotenv
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

# Load environment variables from the .env file
load_dotenv()

# ==========================================
# 1. EXPAND THE STATE
# ==========================================
class ScraperState(TypedDict):
    url: str
    lcp: Optional[float]
    cls: Optional[float]
    tbt: Optional[float]
    ttfb: Optional[float]
    errors: List[str]

# ==========================================
# 2. DEFINE NODE 1: PERFORMANCE METRICS
# ==========================================
def get_performance_metrics(state: ScraperState):
    print(f"\n--- Running Node 1: Performance Metrics for {state['url']} ---")
    
    updates = {
        "lcp": None,
        "cls": None,
        "tbt": None,
        "ttfb": None,
        "errors": state.get("errors", [])
    }
    
    api_key = os.getenv("PAGESPEED_API_KEY")
    if not api_key:
        updates["errors"].append("PAGESPEED_API_KEY is missing from environment variables.")
        return updates

    # Construct the API Request URL
    # We use strategy=mobile as mobile performance is the industry standard benchmark
    endpoint = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={state['url']}&strategy=mobile&key={api_key}"
    
    try:
        # The PageSpeed API can take up to 30 seconds to run a fresh Lighthouse audit
        response = requests.get(endpoint, timeout=45)
        response.raise_for_status()
        data = response.json()
        
        # Navigate the JSON response to extract the exact Lighthouse audits
        audits = data.get("lighthouseResult", {}).get("audits", {})
        
        # A. Largest Contentful Paint (Convert ms to seconds)
        if "largest-contentful-paint" in audits:
            raw_lcp = audits["largest-contentful-paint"].get("numericValue", 0)
            updates["lcp"] = round(raw_lcp / 1000, 2)
            
        # B. Cumulative Layout Shift (Already a flat score)
        if "cumulative-layout-shift" in audits:
            updates["cls"] = round(audits["cumulative-layout-shift"].get("numericValue", 0), 3)
            
        # C. Total Blocking Time (Keep in ms for granularity)
        if "total-blocking-time" in audits:
            updates["tbt"] = round(audits["total-blocking-time"].get("numericValue", 0), 2)
            
        # D. Time to First Byte / Server Response Time (Keep in ms)
        if "server-response-time" in audits:
            updates["ttfb"] = round(audits["server-response-time"].get("numericValue", 0), 2)

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        updates["errors"].append(f"PageSpeed API Error: {str(e)}")
    except KeyError as e:
        print(f"JSON Parsing Error: {e}")
        updates["errors"].append(f"Unexpected JSON structure: missing {str(e)}")

    return updates

# ==========================================
# 3. BUILD AND COMPILE THE LANGGRAPH
# ==========================================
workflow = StateGraph(ScraperState)
workflow.add_node("performance_checker", get_performance_metrics)
workflow.set_entry_point("performance_checker")
workflow.add_edge("performance_checker", END)
app = workflow.compile()

# ==========================================
# 4. RUN THE GRAPH (TEST)
# ==========================================
if __name__ == "__main__":
    initial_state = {
        "url": "https://www.gymshark.com/", 
        "lcp": None,
        "cls": None,
        "tbt": None,
        "ttfb": None,
        "errors": []
    }
    
    final_state = app.invoke(initial_state)
    
    print("\n--- Final Extracted State ---")
    print(f"URL: {final_state['url']}")
    print(f"LCP (Seconds): {final_state['lcp']}")
    print(f"CLS (Score): {final_state['cls']}")
    print(f"TBT (ms): {final_state['tbt']}")
    print(f"TTFB (ms): {final_state['ttfb']}")
    print(f"Errors: {final_state['errors']}")