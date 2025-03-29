import os
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser, BrowserContextConfig, BrowserConfig
from browser_use.browser.browser import BrowserContext
from pydantic import SecretStr
from dotenv import load_dotenv


async def setup_browser():
    """Initialize and configure the browser"""
    browser = Browser(config=BrowserConfig())
    context_config = BrowserContextConfig(
        wait_for_network_idle_page_load_time=5.0,
        highlight_elements=True,
        save_recording_path="./recordings",
    )
    return browser, BrowserContext(browser=browser, config=context_config)


async def agent_loop(llm, browser_context, query):
    """Run agent loop"""
    agent = Agent(
        task=query,
        llm=llm,
        browser_context=browser_context,
        use_vision=True,
    )

    # Start Agent and browser
    result = await agent.run()

    return result.final_result() if result else None


async def main():
    # Load environment variables
    load_dotenv()

    # Disable telemetry
    os.environ["ANONYMIZED_TELEMETRY"] = "false"

    # Initialize the Gemini model
    llm = ChatGoogleGenerativeAI(
        model="gemma-3-27b-it",
        api_key=SecretStr(os.getenv("GEMINI_API_KEY")),
        # model="gemini-2.0-flash", api_key=SecretStr(os.getenv("GEMINI_API_KEY"))
    )

    # Setup browser
    browser, context = await setup_browser()

    # Get search queries from user
    while True:
        try:
            # Get user input and check for exit commands
            user_input = input("\nEnter your prompt (or 'quit' to exit): ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            # Process the prompt and run agent loop
            result = await agent_loop(llm, context, user_input)

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
        finally:
            print("Closing browser")
            # Ensure browser is closed properly
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
