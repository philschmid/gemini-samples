"""
Gemini Browser Agent: Gemini 2.5 Flash can interact and control a web browser using browser_use.

Usage Examples:

1. Single Query Mode:
   Run a specific query on a starting URL and exit.
   python scripts/gemini-browser-use.py --url https://www.google.com/search?q=google+gemini+2.5+flash --query "Summarize the key features of Gemini 2.5 Flash."

2. Interactive Mode:
   Start an interactive session, optionally with a starting URL.
   python scripts/gemini-browser-use.py
   (You will be prompted to enter queries repeatedly)

Sample query for getting an overview of Gemini 2.5 Flash:
    "What is Gemini 2.5 Flash? When was it launched and what are its key capabilities
    compared to previous models? Summarize the main features and improvements."

Command-line options:
    --model: The Gemini model to use (default: gemini-2.5-flash-preview-04-17)
    --planner-model: The Gemini model to use for planning (defaults to the main model).
    --headless: Run the browser in headless mode
    --url: Starting URL for the browser to navigate to before processing the query
    --query: Run a single query and exit (instead of interactive mode)

challenging queries:
    "How many individual plastic Fimir miniatures were included in the original HeroQuest Game System board game (not including expansions) released in North America in 1990?"
    python scripts/gemini-browser-use.py --query "How many individual plastic Fimir miniatures were included in the original HeroQuest Game System board game (not including expansions) released in North America in 1990?" --url "https://www.google.com"
    Answer: 3
"""

import os
import asyncio
import argparse
import logging  # Added for logging
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser, BrowserContextConfig, BrowserConfig
from browser_use.browser.browser import BrowserContext
from pydantic import SecretStr
from dotenv import load_dotenv

# --- Setup Logging ---
# You can customize the logging level further if needed
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s"
)
logger = logging.getLogger("GeminiBrowserAgent")
# # Silence noisy loggers if desired
# logging.getLogger("browser_use").setLevel(logging.WARNING)
# logging.getLogger("playwright").setLevel(logging.WARNING)
# --- End Logging Setup ---


async def setup_browser(headless: bool = False):
    """Initialize and configure the browser"""
    browser = Browser(
        config=BrowserConfig(
            headless=headless,
            # Consider deterministic rendering if running headless for consistency
            # deterministic_rendering=headless,
        ),
    )
    context_config = BrowserContextConfig(
        wait_for_network_idle_page_load_time=3.0,  # Increased wait time
        highlight_elements=True,  # Keep highlighting for headed mode debugging
        # save_recording_path="./recordings", # Keep recording if needed
        viewport_expansion=500,  # Include elements slightly outside the viewport
    )
    browser_context = BrowserContext(browser=browser, config=context_config)
    return browser, browser_context


RECOVERY_PROMPT = """
IMPORTANT RULE: If an action fails multiple times consecutively (e.g., 3 times) or if the screenshot you receive is not changing after 3 attempts,
DO NOT simply repeat the exact same action. 
Instead use the `go_back` action and try navigating to the target differently. 
If that doesn't work, try a different search query on google.
"""
# --- End Failure Recovery Prompt ---


async def agent_loop(llm, planner_llm, browser_context, query, initial_url=None):
    """Run agent loop with optional initial URL, memory, planner, and logging."""
    # Set up initial actions if URL is provided
    initial_actions = None
    if initial_url:
        initial_actions = [
            {"open_tab": {"url": initial_url}},
        ]

    agent = Agent(
        task=query,
        llm=llm,
        browser_context=browser_context,
        use_vision=True,
        generate_gif=True,
        initial_actions=initial_actions,
        enable_memory=True,
        planner_llm=planner_llm,
        planner_interval=3,  # Run planner every 3 steps
        use_vision_for_planner=False,  # Planner usually doesn't need vision
        extend_system_message=RECOVERY_PROMPT,  # Add extended prompt
        max_failures=3,
    )

    # Start Agent and browser, passing the logging hook
    result_history = await agent.run()

    final_result = result_history.final_result() if result_history else None
    success_status = result_history.is_successful() if result_history else "Unknown"
    logger.info(
        f"Agent finished. Success status: {success_status}. Final Result: {final_result}"
    )
    return final_result


async def main():
    # Load environment variables
    load_dotenv()

    # Disable telemetry
    os.environ["ANONYMIZED_TELEMETRY"] = "false"

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Run Gemini agent with browser interaction."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash-preview-04-17",
        help="The Gemini model to use for main tasks.",
    )
    parser.add_argument(
        "--planner-model",
        type=str,
        default="gemini-2.5-flash-preview-04-17",
        help="The Gemini model to use for planning (defaults to main model if not specified).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser in headless mode.",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Starting URL for the browser to navigate to before user query.",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="The query to process.",
    )
    args = parser.parse_args()

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("GEMINI_API_KEY not found in environment variables.")
        return

    llm = ChatGoogleGenerativeAI(
        model=args.model,
        api_key=SecretStr(gemini_api_key),
    )
    planner_llm = ChatGoogleGenerativeAI(
        model=args.planner_model,
        api_key=SecretStr(gemini_api_key),
    )

    # Setup browser
    browser, context = await setup_browser(headless=args.headless)

    if args.query:
        result = await agent_loop(
            llm, planner_llm, context, args.query, initial_url=args.url
        )
        print("\n--- FINAL RESULT ---")
        print(result if result else "Agent finished without a final result.")
        print("--------------------")
    else:
        while True:
            try:
                # Get user input and check for exit commands
                user_input = input("\nEnter your prompt (or 'quit' to exit): ")
                if user_input.lower() in ["quit", "exit", "q"]:
                    break

                # Process the prompt and run agent loop
                result = await agent_loop(
                    llm, planner_llm, context, user_input, initial_url=args.url
                )

                # Clear URL after first use to avoid reopening same URL in subsequent queries
                args.url = None

                # Display the final result with clear formatting
                print("\n📊 FINAL RESULT:")
                print("=" * 50)
                print(result if result else "Agent finished without a final result.")
                print("=" * 50)

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"\nError occurred: {e}")

    # Ensure browser is closed properly
    try:
        await browser.close()
        print("Browser closed successfully.")
    except Exception as e:
        print(f"\nError closing browser: {e}")


if __name__ == "__main__":
    # Ensure the event loop is managed correctly, especially for interactive mode
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting program.")
