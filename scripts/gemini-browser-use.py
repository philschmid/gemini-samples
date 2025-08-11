"""
Gemini Browser Agent: Gemini 2.5 Flash can interact and control a web browser using browser_use.
"""

import os
import asyncio
import argparse
import logging  # Added for logging
from browser_use.llm import ChatGoogle
from browser_use import (
    Agent,
    BrowserSession,
)

# # --- Setup Logging ---
# # You can customize the logging level further if needed
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s"
# )
# logger = logging.getLogger("GeminiBrowserAgent")
# # # Silence noisy loggers if desired
# # logging.getLogger("browser_use").setLevel(logging.WARNING)
# # logging.getLogger("playwright").setLevel(logging.WARNING)
# # --- End Logging Setup ---


# ANSI color codes
class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


async def setup_browser(headless: bool = False):
    """Initialize and configure the browser"""
    browser = BrowserSession(
        headless=headless,
        wait_for_network_idle_page_load_time=3.0,  # Increased wait time
        highlight_elements=True,  # Keep highlighting for headed mode debugging
        # save_recording_path="./recordings", # Keep recording if needed
        viewport_expansion=500,  # Include elements slightly outside the viewport
    )
    return browser


RECOVERY_PROMPT = """
IMPORTANT RULE: If an action fails multiple times consecutively (e.g., 3 times) or if the screenshot you receive is not changing after 3 attempts,
DO NOT simply repeat the exact same action. 
Instead use the `go_back` action and try navigating to the target differently. 
If that doesn't work, try a different search query on google.
"""

SUMMARIZER_PROMPT = """You are an AI assistant specializing in process analysis and summarization. Your task is to read a given text that describes a sequence of events and create a structured summary of the steps an agent took.

Your summary should chronologically detail the agent's actions, observations, and decisions that led to the final outcome.

# Output Format:
Present the summary as a numbered list. Group steps together. Each group must be clearly articulated and follow this strict format:

**Steps [from - to]:**
- **Observation:** Describe what the agent saw, heard, or became aware in these steps.
- **Action:** Describe the specific action(s) the agent performed.
- **Decision/Result:** Explain the decision the agent made based on the observation, or the immediate result of their action.

# Context

{history}"""


async def agent_loop(llm, browser_session, query, initial_url=None):
    """Run agent loop with optional initial URL."""
    # Set up initial actions if URL is provided
    initial_actions = None
    if initial_url:
        initial_actions = [
            {"open_tab": {"url": initial_url}},
        ]

    agent = Agent(
        task=query,
        message_context="The user name is Philipp and he lives in Nuremberg, Today is 2025-07-24.",
        llm=llm,
        browser_session=browser_session,
        use_vision=True,
        generate_gif=True,
        initial_actions=initial_actions,
        extend_system_message=RECOVERY_PROMPT,
        max_failures=3,
    )
    # Start Agent and browser, passing the logging hook
    result_history = await agent.run()

    with open("history.md", "w") as f:
        history = "Here is a history of all steps taken by the Agent to end up with the final result."
        for h in result_history.history:
            # Safely access metadata and step_number
            metadata = getattr(h, "metadata", None)
            step_number = getattr(metadata, "step_number", "N/A")

            # Safely access model_output and thinking
            model_output = getattr(h, "model_output", None)
            thinking = (
                getattr(model_output, "thinking", "No thinking process recorded.")
                or "No thinking process recorded."
            )
            memory = (
                getattr(model_output, "memory", "No memory recorded.")
                or "No memory recorded."
            )
            evaluation = (
                getattr(
                    model_output, "evaluation_previous_goal", "No evaluation recorded."
                )
                or "No evaluation recorded."
            )

            # Safely access result and extracted_content
            result_list = getattr(h, "result", [])
            content_parts = []
            if result_list:
                for res in result_list:
                    extracted = getattr(res, "extracted_content", None)
                    if extracted:
                        content_parts.append(extracted)

            content = (
                "\n".join(content_parts) if content_parts else "No content extracted."
            )

            history += f"""
# Step: {step_number}
## Thinking
{thinking}
## Evaluation
{evaluation}
## Memory
{memory}
## Result
{content}

"""

        f.write(history)

        with open("summary.md", "w") as f:

            response = await llm.get_client().aio.models.generate_content(
                model=llm.model, contents=SUMMARIZER_PROMPT.format(history=history)
            )
            f.write(response.text)

    return result_history.final_result() if result_history else "No result found"


async def main():
    # Disable telemetry
    os.environ["ANONYMIZED_TELEMETRY"] = "false"

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Run Gemini agent with browser interaction."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash",
        help="The Gemini model to use for main tasks.",
    )
    parser.add_argument(
        "--headless",
        default=False,
        # action="store_true",
        # help="Run the browser in headless mode.",
    )
    args = parser.parse_args()

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("GEMINI_API_KEY not found in environment variables.")
        return

    llm = ChatGoogle(
        model=args.model,
        api_key=gemini_api_key,
        config={"automatic_function_calling": {"maximum_remote_calls": 100}},
    )
    browser = await setup_browser(headless=args.headless)

    print(f"{Colors.BOLD}{Colors.PURPLE}🤖 Gemini Browser Agent Ready{Colors.RESET}")
    print(f"{Colors.GRAY}Type 'exit' to quit{Colors.RESET}\n")

    while True:
        try:
            # Get user input and check for exit commands
            user_input = input(f"{Colors.BOLD}{Colors.BLUE}You: {Colors.RESET} ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print(f"\n{Colors.GRAY}Goodbye!{Colors.RESET}")
                break

            print(
                f"{Colors.BOLD}{Colors.GREEN}Gemini: {Colors.RESET}",
                end="",
                flush=True,
            )
            # Process the prompt and run agent loop
            result = await agent_loop(llm, browser, user_input)

            # Display the final result
            print(f"{Colors.GREEN}{result}{Colors.RESET}\n")

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
