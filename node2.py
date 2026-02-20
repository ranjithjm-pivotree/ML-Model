import re
import requests
from bs4 import BeautifulSoup
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

# ==========================================
# 1. DEFINE THE STATE
# This acts as our "memory" passing through the pipeline
# ==========================================
class ScraperState(TypedDict):
    url: str
    has_return_policy: bool
    has_privacy_policy: bool
    has_terms_of_service: bool
    emails: List[str]
    phone_numbers: List[str]
    social_links: List[str]
    errors: List[str]

# ==========================================
# 2. DEFINE NODE 2: TRUST SIGNALS
# ==========================================
def check_trust_signals(state: ScraperState):
    print(f"--- Running Node 2: Trust Signals for {state['url']} ---")
    
    # Initialize default values for the state we are about to extract
    updates = {
        "has_return_policy": False,
        "has_privacy_policy": False,
        "has_terms_of_service": False,
        "emails": [],
        "phone_numbers": [],
        "social_links": [],
        "errors": state.get("errors", [])
    }
    
    try:
        # Fetch the HTML
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(state["url"], headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # A. Find Emails via Regex (Extracting from mailto: links and raw text)
        email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        updates["emails"] = list(set(re.findall(email_regex, soup.get_text())))
        
        # B. Find Phone Numbers via Regex (Basic US/International format match)
        phone_regex = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        updates["phone_numbers"] = list(set(re.findall(phone_regex, soup.get_text())))

        # C. Scan all Links for Policies and Social Proof
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            
            # Policy Checks
            if "return" in text or "refund" in text or "return" in href:
                updates["has_return_policy"] = True
            if "privacy" in text or "privacy" in href:
                updates["has_privacy_policy"] = True
            if "terms" in text or "conditions" in text or "terms" in href:
                updates["has_terms_of_service"] = True
                
            # Social Proof Checks
            if any(social in href for social in ["instagram.com", "facebook.com", "twitter.com", "tiktok.com", "x.com"]):
                if href not in updates["social_links"]:
                    updates["social_links"].append(href)

    except Exception as e:
        print(f"Error fetching HTML: {e}")
        updates["errors"].append(str(e))

    # Return the updated dictionary to LangGraph
    return updates

# ==========================================
# 3. BUILD AND COMPILE THE LANGGRAPH
# ==========================================
# Initialize the graph with our state structure
workflow = StateGraph(ScraperState)

# Add our Node 2 to the graph
workflow.add_node("trust_checker", check_trust_signals)

# Define the flow (Start -> trust_checker -> End)
workflow.set_entry_point("trust_checker")
workflow.add_edge("trust_checker", END)

# Compile the graph
app = workflow.compile()

# ==========================================
# 4. RUN THE GRAPH (TEST)
# ==========================================
if __name__ == "__main__":
    # Define our starting state with just the target URL
    initial_state = {
        "url": "https://www.myntra.com/", # Replace with a target site
        "has_return_policy": False,
        "has_privacy_policy": False,
        "has_terms_of_service": False,
        "emails": [],
        "phone_numbers": [],
        "social_links": [],
        "errors": []
    }
    
    # Execute the graph
    final_state = app.invoke(initial_state)
    
    print("\n--- Final Extracted Data ---")
    for key, value in final_state.items():
        print(f"{key}: {value}")