# pip install google-genai fastmcp
# requires Python 3.13+
import os
import asyncio
import logging
from datetime import datetime
from google import genai
from uuid import uuid4
from fastmcp import Client

# Suppress all logging
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("google").setLevel(logging.CRITICAL)
logging.getLogger("mcp").setLevel(logging.CRITICAL)
logging.getLogger("fastmcp").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)


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


# Create Gemini instance LLM class
client = genai.Client()

mcp_client = Client(
    {
        "mcpServers": {
            "pipedream": {
                "transport": "http",
                "url": "https://remote.mcp.pipedream.net",
                "headers": {
                    # note if you don't have Pipedream Developer credentials, you can use a temporary, short-lived token for development
                    # this will create a ephemeral account for you, which will be deleted after a short time.
                    # refer to Pipedream docs for more information: https://pipedream.com/docs/connect/mcp/developers
                    "Authorization": f"Bearer {os.environ.get('PIPEDREAM_API_KEY',f'devtok_{uuid4()}')}",
                    # see here for available apps: https://pipedream.com/docs/connect/mcp/app-discovery
                    "x-pd-app-slug": "gmail, google_calendar",
                },
            }
        }
    }
)


async def run():
    async with mcp_client:
        config = genai.types.GenerateContentConfig(
            temperature=0,
            tools=[mcp_client.session],
            system_instruction=f"""Very important: The user's timezone is {datetime.now().strftime("%Z")}. The current date is {datetime.now().strftime("%Y-%m-%d")}. 
Any dates before this are in the past, and any dates after this are in the future. When dealing with modern entities/companies/people, and the user asks for the 'latest', 'most recent', 'today's', etc. don't assume your knowledge is up to date; 
You can and should speak any language the user asks you to speak or use the language of the user.""",
        )

        print(f"{Colors.BOLD}{Colors.PURPLE}🤖 Gemini MCP Agent Ready{Colors.RESET}")
        print(f"{Colors.GRAY}Type 'exit' to quit{Colors.RESET}\n")

        chat = client.aio.chats.create(model="gemini-2.5-flash", config=config)

        while True:
            user_input = input(f"{Colors.BOLD}{Colors.BLUE}You: {Colors.RESET}")
            if user_input.lower() == "exit":
                print(f"\n{Colors.GRAY}Goodbye!{Colors.RESET}")
                break

            response = await chat.send_message_stream(user_input)
            print(
                f"{Colors.BOLD}{Colors.GREEN}Gemini: {Colors.RESET}",
                end="",
                flush=True,
            )

            async for chunk in response:
                print(f"{Colors.GREEN}{chunk.text}{Colors.RESET}", end="", flush=True)
            print("\n")


if __name__ == "__main__":
    asyncio.run(run())
