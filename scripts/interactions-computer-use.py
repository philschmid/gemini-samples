"""
Gemini Interactions API + Computer Use + Playwright

Browser automation agent using Gemini's Computer Use tool.

Requirements:
    pip install google-genai playwright
    playwright install chromium
"""

import base64
import time
from playwright.sync_api import sync_playwright
from google import genai

client = genai.Client()

SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900


def denormalize(x: int, y: int) -> tuple[int, int]:
    """Convert normalized coordinates (0-999) to pixels."""
    return int(x / 1000 * SCREEN_WIDTH), int(y / 1000 * SCREEN_HEIGHT)


def execute_action(page, function_call) -> dict:
    """Execute a Computer Use action on the browser."""
    name = function_call.name
    args = function_call.arguments or {}
    
    print(f"  → {name}")
    
    if name == "click_at":
        x, y = denormalize(args.get("x", 0), args.get("y", 0))
        page.mouse.click(x, y)
        
    elif name == "type_text_at":
        x, y = denormalize(args.get("x", 0), args.get("y", 0))
        page.mouse.click(x, y)
        if args.get("clear_before_typing", True):
            page.keyboard.press("Meta+A")
            page.keyboard.press("Backspace")
        page.keyboard.type(args.get("text", ""))
        if args.get("press_enter", True):
            page.keyboard.press("Enter")
            
    elif name == "scroll_document":
        key = {"down": "PageDown", "up": "PageUp"}.get(args.get("direction", "down"), "PageDown")
        page.keyboard.press(key)
        
    elif name == "scroll_at":
        x, y = denormalize(args.get("x", 500), args.get("y", 500))
        direction = args.get("direction", "down")
        delta = int(args.get("magnitude", 800) / 1000 * SCREEN_HEIGHT)
        page.mouse.move(x, y)
        if direction in ("down", "up"):
            page.mouse.wheel(0, delta if direction == "down" else -delta)
        else:
            page.mouse.wheel(delta if direction == "right" else -delta, 0)
            
    elif name == "hover_at":
        x, y = denormalize(args.get("x", 0), args.get("y", 0))
        page.mouse.move(x, y)
        
    elif name == "key_combination":
        page.keyboard.press(args.get("keys", ""))
        
    elif name == "navigate":
        page.goto(args.get("url", ""))
        
    elif name == "go_back":
        page.go_back()
        
    elif name == "go_forward":
        page.go_forward()
        
    elif name == "search":
        page.goto("https://www.google.com")
        
    elif name == "drag_and_drop":
        start_x, start_y = denormalize(args.get("x", 0), args.get("y", 0))
        end_x, end_y = denormalize(args.get("destination_x", 0), args.get("destination_y", 0))
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        page.mouse.move(end_x, end_y)
        page.mouse.up()
        
    elif name == "wait_5_seconds":
        time.sleep(5)
        
    elif name == "open_web_browser":
        pass  # Already open
    
    # Wait for page to settle
    page.wait_for_load_state("networkidle", timeout=5000)
    time.sleep(0.5)
    
    return {}


def check_safety(function_call) -> tuple[bool, bool]:
    """Check if action needs user confirmation. Returns (proceed, needs_ack)."""
    args = function_call.arguments or {}
    safety = args.get("safety_decision")
    
    if not safety or safety.get("decision") != "require_confirmation":
        return True, False
    
    print(f"\n⚠️  Safety: {safety.get('explanation', '')}")
    response = input("   Proceed? [y/N]: ").strip().lower()
    return (True, True) if response in ("y", "yes") else (False, False)


def run_agent(task: str, start_url: str = "https://www.google.com", max_turns: int = 25):
    """Run the Computer Use agent."""
    print(f"🎯 Task: {task}\n")
    
    # Start browser
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_context(viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT}).new_page()
    page.goto(start_url)
    
    previous_id = None
    turn = 0
    
    while turn < max_turns:
        turn += 1
        
        # Capture screenshot
        screenshot = page.screenshot(type="png")
        
        # Build input
        if previous_id is None:
            # Initial request with task
            input_content = [
                {"type": "text", "text": task},
                {"type": "image", "data": base64.b64encode(screenshot).decode(), "mime_type": "image/png"}
            ]
        else:
            # Continue with function results
            input_content = 
            
            
            function_results + [
                {"type": "image", "data": base64.b64encode(screenshot).decode(), "mime_type": "image/png"}
            ]
        
        # Call the model
        interaction = client.interactions.create(
            model="gemini-3-flash-preview",
            input=input_content,
            tools=[{"type": "computer_use", "environment": "browser"}],
            previous_interaction_id=previous_id,
        )
        previous_id = interaction.id
        
        print(f"── Turn {turn} ({interaction.status}) ──")
        
        # Check if done
        if interaction.status == "completed":
            for output in interaction.outputs:
                if output.type == "text":
                    print(f"\n✅ {output.text}")
            break
        
        # Get function calls
        function_calls = [o for o in interaction.outputs if o.type == "function_call"]
        if not function_calls:
            for output in interaction.outputs:
                if output.type == "text":
                    print(f"   {output.text}")
            break
        
        # Execute actions
        function_results = []
        for fc in function_calls:
            proceed, needs_ack = check_safety(fc)
            
            if not proceed:
                print("   🛑 Blocked")
                function_results.append({
                    "type": "function_result",
                    "call_id": fc.id,
                    "name": fc.name,
                    "result": [{"type": "text", "text": "Error: Blocked by user"}],
                    "is_error": True
                })
                continue
            
            execute_action(page, fc)
            
            result = {"url": page.url}
            if needs_ack:
                result["safety_acknowledgement"] = True
                
            function_results.append({
                "type": "function_result",
                "call_id": fc.id,
                "name": fc.name,
                "result": "result"
            })
    
    else:
        print(f"\n⚠️ Max turns ({max_turns}) reached")
    
    browser.close()
    playwright.stop()


if __name__ == "__main__":
    run_agent(
        task="Go to google.com and search for 'Gemini API documentation'. Click on the first result and summarize what the page is about.",
        start_url="https://www.google.com"
    )
