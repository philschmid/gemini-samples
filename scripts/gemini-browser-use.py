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
    --headless: Run the browser in headless mode
    --url: Starting URL for the browser to navigate to before processing the query
    --query: Run a single query and exit (instead of interactive mode)
"""

import os
import asyncio
import argparse
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser, BrowserContextConfig, BrowserConfig
from browser_use.browser.browser import BrowserContext
from pydantic import SecretStr
from dotenv import load_dotenv


async def setup_browser(headless: bool = False):
    """Initialize and configure the browser"""
    browser = Browser(
        config=BrowserConfig(
            headless=headless,
        ),
    )
    context_config = BrowserContextConfig(
        wait_for_network_idle_page_load_time=5.0,
        highlight_elements=True,
        save_recording_path="./recordings",
    )
    return browser, BrowserContext(browser=browser, config=context_config)


async def agent_loop(llm, browser_context, query, initial_url=None):
    """Run agent loop with optional initial URL"""
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
    )

    # Start Agent and browser
    result = await agent.run()

    return result.final_result() if result else None


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
        help="The Gemini model to use.",
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
    # --- End Argument Parsing ---

    # Initialize the Gemini model
    llm = ChatGoogleGenerativeAI(
        model=args.model,
        api_key=SecretStr(os.getenv("GEMINI_API_KEY")),
    )

    # Setup browser
    browser, context = await setup_browser(headless=args.headless)

    if args.query:
        result = await agent_loop(llm, context, args.query, initial_url=args.url)
        print(result)
        return
    else:
        # Get search queries from user
        while True:
            try:
                # Get user input and check for exit commands
                user_input = input("\nEnter your prompt (or 'quit' to exit): ")
                if user_input.lower() in ["quit", "exit", "q"]:
                    break

                # Process the prompt and run agent loop with initial URL if provided
                result = await agent_loop(
                    llm, context, user_input, initial_url=args.url
                )

                # Clear URL after first use to avoid reopening same URL in subsequent queries
                args.url = None

                # Display the final result with clear formatting
                print("\n📊 Search Results:")
                print("=" * 50)
                print(result if result else "No results found")
                print("=" * 50)

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"\nError occurred: {e}")

    print("Closing browser")
    # Ensure browser is closed properly
    await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
