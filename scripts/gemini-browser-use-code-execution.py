import asyncio
import os
from datetime import datetime
from browser_use import Agent, ChatGoogle


llm = ChatGoogle(model="gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY"))

task = f"Extract all newsletter urls from the last 7 days from https://news.smol.ai/, Today is {datetime.now().strftime('%Y-%m-%d')}"


def run_search():
    agent = Agent(
        task=task,
        llm=llm,
        use_vision=True,
        generate_gif=True,
        extend_system_message="Use the execute_js tool for extracting data/information from websites.",
        max_failures=3,
    )
    history = agent.run_sync(max_steps=25)
    return history.final_result()


if __name__ == "__main__":
    res = run_search()
    print(res)


# INFO     [Agent]   🎯 Next goal: Extract newsletter URLs for the last 7 days (Sep 11, 2025 - Sep 17, 2025) using a refined JavaScript code, then save the extracted URLs to a file.
# INFO     [Agent]   🦾 [ACTION 1/1] execute_js: code: (function()     const urls = [];    const targetDates = [        Sep 11, Sep 12, Sep 13, Sep 14, Sep 15
# INFO     [tools] Code: (function() {    const urls = [];    const targetDates = [        'Sep 11', 'Sep 12', 'Sep 13', 'Sep 14', 'Sep 15', 'Sep 16', 'Sep 17'    ];    document.querySelectorAll('a').forEach(link => {        const text = link.textContent.trim();        for (const dateStr of targetDates) {            if (text.startsWith(dateStr)) {                urls.push(link.href);                break;            }        }    });    return JSON.stringify(urls);})()
# Result: ["https://news.smol.ai/issues/25-09-17-not-much","https://news.smol.ai/issues/25-09-16-not-much","https://news.smol.ai/issues/25-09-15-gpt5-codex","https://news.smol.ai/issues/25-09-12-not-much","https://news.smol.ai/issues/25-09-11-qwen3-next","https://news.smol.ai/issues/24-09-16-ainews-a-quiet-weekend","https://news.smol.ai/issues/24-09-13-ainews-learnings-from-o1-ama","https://news.smol.ai/issues/24-09-12-ainews-o1-openais-new-general-reasoning-models","https://news.smol.ai/issues/24-09-11-ainews-pixtral-12b-mistral-beats-llama-to-multimodality","https://news.smol.ai/issues/24-09-10-ainews-not-much-happened-today-ainews-podcast"]
# Successfully extracted all newsletter URLs from news.smol.ai for the last 7 days (Sep 11, 2025 - Sep 17, 2025). The extracted URLs are available in the attached file 'newsletter_urls.txt'.

# Attachments:

# newsletter_urls.txt:
# https://news.smol.ai/issues/25-09-17-not-much
# https://news.smol.ai/issues/25-09-16-not-much
# https://news.smol.ai/issues/25-09-15-gpt5-codex
# https://news.smol.ai/issues/25-09-12-not-much
# https://news.smol.ai/issues/25-09-11-qwen3-next
