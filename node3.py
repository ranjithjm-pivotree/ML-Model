import os
import json
import asyncio
from dotenv import load_dotenv
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

# Import Browser-use and LangChain's Google GenAI wrapper
from browser_use import Agent
from browser_use import Agent, ChatGoogle

# Load environment variables from the .env file
load_dotenv()

# ==========================================
# 1. EXPAND THE STATE
# ==========================================
class ScraperState(TypedDict):
    url: str
    clicks_to_checkout: Optional[int]
    guest_checkout_available: Optional[bool]
    screenshot_image: Optional[str]  
    errors: List[str]

# ==========================================
# 2. DEFINE NODE 3: THE FRICTION TESTER
# ==========================================
async def run_friction_tester(state: ScraperState):
    print(f"\n--- Running Node 3: Friction Tester for {state['url']} ---")
    
    updates = {
        "clicks_to_checkout": None,
        "guest_checkout_available": None,
        "screenshot_image": None,
        "errors": state.get("errors", [])
    }
    
    try:
        # Initialize Gemini via LangChain
        # We use gemini-2.5-pro for its strong reasoning and vision capabilities in browser tasks
        llm = ChatGoogle(model="gemini-2.5-flash") 

        task_prompt = f"""
        1. Go to the website: {state['url']}.
        2. Find any physical product and add it to the shopping cart.
        3. Proceed to the final checkout page where payment would be entered.
        4. Count the exact number of clicks it took you to get from the homepage to this checkout screen.
        5. Look at the checkout screen. Is 'Guest Checkout' available without creating an account?
        6. Return EXACTLY a raw JSON string (no markdown formatting or code blocks) containing your findings:
           {{"clicks_to_checkout": <int>, "guest_checkout_available": <bool>}}
        """
        
        # Initialize the browser-use agent with Gemini
        agent = Agent(task=task_prompt, llm=llm)
        
        history = await agent.run()
        
        # A. Extract the JSON text response
        final_text = history.final_result()
        try:
            parsed_data = json.loads(final_text.strip())
            updates["clicks_to_checkout"] = parsed_data.get("clicks_to_checkout")
            updates["guest_checkout_available"] = parsed_data.get("guest_checkout_available")
            print(f"Agent found: {parsed_data}")
        except json.JSONDecodeError:
            print("Failed to parse JSON. Agent returned:", final_text)
            updates["errors"].append("Friction JSON parse failed.")

        # B. Extract the screenshot
        screenshots = history.screenshots()
        if screenshots:
            updates["screenshot_image"] = screenshots[-1] 
            print("Screenshot successfully captured!")

    except Exception as e:
        print(f"Error during browser interaction: {e}")
        updates["errors"].append(str(e))

    return updates

# ==========================================
# 3. BUILD AND COMPILE THE LANGGRAPH
# ==========================================
workflow = StateGraph(ScraperState)
workflow.add_node("friction_tester", run_friction_tester)
workflow.set_entry_point("friction_tester")
workflow.add_edge("friction_tester", END)
app = workflow.compile()

# ==========================================
# 4. RUN THE GRAPH (TEST)
# ==========================================
async def main():
    # Verify the Google API key loaded correctly from .env
    if not os.getenv("GOOGLE_API_KEY"):
        print("WARNING: GOOGLE_API_KEY not found. Please check your .env file.")
        return
        
    initial_state = {
        "url": "https://www.myntra.com/", 
        "clicks_to_checkout": None,
        "guest_checkout_available": None,
        "screenshot_image": None,
        "errors": []
    }
    
    final_state = await app.ainvoke(initial_state)
    
    print("\n--- Final Extracted State ---")
    print(f"URL: {final_state['url']}")
    print(f"Clicks to Checkout: {final_state['clicks_to_checkout']}")
    print(f"Guest Checkout Available: {final_state['guest_checkout_available']}")
    print(f"Screenshot Captured: {bool(final_state['screenshot_image'])}")
    print(f"Errors: {final_state['errors']}")

if __name__ == "__main__":
    asyncio.run(main())