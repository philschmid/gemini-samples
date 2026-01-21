from markdownify import markdownify as md
import requests
from google import genai
from pydantic import BaseModel, Field
from datetime import datetime
import json


class Issues(BaseModel):
    issue_urls: list[str] = Field(description="The full url of the issue, e.g. https://news.smol.ai/issues/23-10-20-gemini-2-5-pro-launch")


client = genai.Client()


def extract_markdown(url):
    response = requests.get(url)
    return md(response.text)


import re


def remove_table_of_contents(markdown_text: str) -> str:
    """
    Removes the Table of Contents from a markdown string.

    This function first finds a "Table of Contents" header. If found, it
    removes the header and all subsequent lines that look like ToC entries
    (e.g., "* [Link](#anchor)"). The removal stops at the first line that
    does not match the ToC entry pattern.

    Args:
        markdown_text: The markdown string.

    Returns:
        The markdown string without the Table of Contents.
    """
    # 1. Find the "Table of Contents" header. We'll be case-insensitive.
    toc_header_pattern = re.compile(
        r"^Table of Contents\s*$", re.MULTILINE | re.IGNORECASE
    )
    toc_header_match = toc_header_pattern.search(markdown_text)

    # If no ToC header is found, return the original text.
    if not toc_header_match:
        return markdown_text

    # 2. Split the text into two parts: before the ToC header and from the header onwards.
    text_before_toc = markdown_text[: toc_header_match.start()]
    text_from_toc_header = markdown_text[toc_header_match.start() :]

    # 3. Define the regex for a ToC entry.
    #    This pattern looks for lines starting with a list marker (*, +, -),
    #    optional indentation, and a markdown link like [text](#anchor).
    toc_entry_pattern = re.compile(r"^\s*[+*-]\s+\[.*?\]\(#.*?\)\s*$")

    # 4. Process the lines from the ToC header onwards.
    lines = text_from_toc_header.split("\n")

    content_lines = []
    in_toc_section = True

    # Skip the header line itself
    for line in lines[1:]:
        # If we are in the ToC section, check if the line is a ToC entry.
        if in_toc_section:
            # If line is blank or a ToC entry, we continue to skip.
            if not line.strip() or toc_entry_pattern.match(line):
                continue
            else:
                # First line that is not a ToC entry marks the end of the ToC.
                in_toc_section = False

        content_lines.append(line)

    # 5. Reconstruct the text.
    text_after_toc = "\n".join(content_lines)

    # Combine the part before the ToC with the part after the ToC.
    final_text = text_before_toc.rstrip() + "\n" + text_after_toc.lstrip()

    return final_text.strip()


def clean_crawl_text(text: str) -> str:
    """
    Reduces a markdown text chunk by removing everything from a specific header onwards.

    This function finds the line containing the header
    "Discord: High level Discord summaries" and removes it and all subsequent
    content from the text.

    Args:
        text: The raw markdown string from the crawl.

    Returns:
        str: The cleaned text with the specified section removed.

    Raises:
        ValueError: If the delimiter header is not found in the text.
    """
    # 1. Define the unique phrase that marks the start of the content to be removed.
    delimiter_phrase = "Discord: High level Discord summaries"

    # 2. Find the character position of our delimiter phrase.
    start_pos = text.find(delimiter_phrase)

    # 3. If the delimiter is not found, raise an error as requested.
    if start_pos == -1:
        raise ValueError(
            f"ERROR: Delimiter phrase '{delimiter_phrase}' not found in the text."
        )

    # 4. Find the beginning of the LINE that contains the delimiter.
    # We search backwards from the found position for the last newline character.
    cut_off_index = text.rfind("\n", 0, start_pos)

    # 5. Determine the final text based on the cut-off point.
    if cut_off_index == -1:
        # If no newline is found before it, the delimiter is on the first line.
        # This means we should return an empty string.
        cleaned_text = ""
    else:
        # Slice the text up to the newline character right before the delimiter's line.
        cleaned_text = text[:cut_off_index]

    # Return the result, stripping any trailing whitespace.
    return cleaned_text.strip()


content = extract_markdown("https://news.smol.ai/")

response = client.models.generate_content(
    model="gemini-flash-latest",
    contents=f"Extract all newsletter issues from last 7 days (today is {datetime.now().strftime('%Y-%m-%d')}) from the following markdown of news.smol.ai: {content}",
    config=genai.types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=Issues.model_json_schema(),
    ),
)

smol_last_week = ""

for issue_url in json.loads(response.text)["issue_urls"]:
    smol_last_week += clean_crawl_text(
        remove_table_of_contents(extract_markdown(issue_url))
    )

with open("smol_last_week.md", "w") as f:
    f.write(smol_last_week)

NEWSLETTER_PROMPT = """You are an expert AI newsletter editor specializing in technology and research. Your task is to analyze a provided body of text containing various news items and compile a concise, engaging newsletter summary from it.

You will receive context of markdown text containing news items.

## Output Structure
Your final output must follow this structure exactly:
1.  **Title:** A main title that highlights the most interesting news items, don't exaggerate the news. Try to include at lest 2 news items in the title, but keep it concise.
2.  **Opening Sentence:** A single, introductory sentence that summarizes the most important news (multiple) from the collection. Keep it concise.
3.  **Category Summaries:** The news items, summarized and grouped under the following specific headings:
    - General News
    - Google DeepMind (The priority is Gemini API & AI Studio > Google DeepMind/Google Research > Other Google AI News)
    - Foundation Labs & Model Updates
    - AI Developer Topics
    - Research News
    - Others Topics

## Category Content and Formatting Rules
- **Relevance:** Focus on the most significant updates within each category. Omit minor updates or less relevant information.
- **Conciseness:** Summaries for each news item should be short, concise, and written in an engaging, but none marketing tone. Don't exaggerate the news or make it sound more important than it is.
- **Inline Links:** Links to sources MUST be integrated directly into the summary sentences using markdown format (`[link text](URL)`). Do not list links at the end of a sentence or section.
- **Mandatory Links:** Every summarized news item must include at least one corresponding source link.
- **Source Prioritization:** Prioritize links to official sources (e.g., official blogs, X accounts), followed by reputable news outlets.
- **Linking Related News:** If multiple news items cover the same topic (e.g., multiple updates from the same company), you may combine them into a single, cohesive summary sentence, including links to the different sources.
- **Length:** Each category summary should be approximately 2-5 sentences long, depending on the amount of relevant news.


---
## Example

Use the Example below for wording, tone, style and length of the topics. Don't use any information from the example thats only for demonstration purposes, ther ordering is only demonstration purposes. Only use information form the Context.

**Output:**
```
# OpenAI Restructures for $1.4T Compute Goals, Cursor 2.0 Launches Composer, and Moonshot Debuts Kimi Linear

This week, OpenAI restructured into a Public Benefit Corporation with a trillion-dollar compute roadmap and a private beta for its agentic GPT-5, while Moonshot AI released its Kimi Linear long-context model and Cursor launched its fast Composer-1 coding agent.

## General News
OpenAI has [restructured into a Public Benefit Corporation (PBC)](https://twitter.com/OpenAI/status/1983157159853777086), altering its deal with Microsoft to gain more autonomy in exchange for a [~\$250B Azure commitment](https://twitter.com/koltregaskes/status/1983175578824917210). CEO Sam Altman outlined an ambitious roadmap including a [\$1.4T compute spending plan](https://news.smol.ai/issues/25-10-13-oai-broadcom) and a goal to build an [automated AI researcher by 2028](https://twitter.com/sama/status/1983584366547829073). In funding news, Poolside raised [\$1B at a \$12B valuation](https://x.com/julienblanchon/status/1984337407097909629?s=46), former X.AI researcher Eric Zelikman [secured \$1B for a new venture](https://x.com/annatonger/status/1984318774208782467?s=46), and voice AI company Cartesia announced a [\$100M Series C](https://twitter.com/krandiash/status/1983202316397453676). Elsewhere, a judge allowed a [copyright lawsuit from George R.R. Martin against OpenAI to proceed](https://www.reddit.com/r/OpenAI/comments/1ojloog/this_is_the_type_of_stuff_that_will_stir_up_user/), and Perplexity AI launched a [patent research agent](https://twitter.com/perplexity_ai/status/1983875975877423277) and other [new finance features](https://twitter.com/AravSrinivas/status/1983998749929259378).

## Google DeepMind
Gemini API introduces a [50% reduction for Batch API use and 90% for context caching](https://twitter.com/GoogleAIStudio/status/1983564552408056179). Google AI Studio now supports [logs and dataset exports for evaluations](https://twitter.com/_philschmid/status/1984258488013340826). Google is partnering with Jio in India to [roll out Google AI Pro plans](https://twitter.com/sundarpichai/status/1983922303424471541), including Gemini 2.5 Pro, to eligible users. On the product front, the [Veo 3.1](https://twitter.com/ArtificialAnlys/status/1983938159839998249) video model was updated, and an [early access program for Gemini for Home](https://twitter.com/Google/status/1983246777215033718) was launched in the U.S.

## Foundation Labs & Model Updates
Moonshot AI released its [Kimi Linear model and technical report](https://twitter.com/Kimi_Moonshot/status/1983937694360322136), a hybrid architecture using Kimi Delta Attention (KDA) that achieves up to a [75% KV cache reduction and 6x decoding throughput](https://twitter.com/scaling01/status/1983926811051384965). The company also shipped a new [terminal-native Kimi CLI and "Kimi For Coding" experience](https://twitter.com/Kimi_Moonshot/status/1984207733177090274). OpenAI began a private beta for [Aardvark](https://twitter.com/OpenAI/status/1983956431360659467), a GPT-5-powered "agentic security researcher" that [finds and fixes code vulnerabilities](https://twitter.com/gdb/status/1983971650531160319), and also [open-sourced gpt-oss-safeguard](https://twitter.com/OpenAI/status/1983507392374641071), a pair of safety classification models. In agentic coding, Cursor launched [Cursor 2.0](https://twitter.com/cursor_ai/status/1983567619946147967) with its fast, in-house [Composer-1 model](https://cursor.com/blog/composer), while Cognition released [SWE-1.5 (Windsurf)](https://twitter.com/cognition/status/1983662836896448756), a model co-designed with Cerebras hardware for high-speed coding. Additionally, the [Minimax M2 model is gaining traction](https://twitter.com/omarsar0/status/1983915573215162873) for its strong coding performance and is now [free to try](https://twitter.com/MiniMax__AI/status/1983522475217735915). Anthropic published research on ["signs of introspection in LLMs"](https://www.anthropic.com/research/introspection), and Cartesia launched [Sonic-3](https://twitter.com/ArtificialAnlys/status/1983879759194157194), an SSM-based text-to-speech model.

## AI Developer Topics
Hugging Face released the ["Smol Training Playbook"](https://huggingface.co/spaces/HuggingFaceTB/smol-training-playbook), a comprehensive 200+ page guide covering the entire LLM training pipeline. In agent frameworks, LangChain shipped a new [Deep Agents CLI](https://twitter.com/hwchase17/status/1984303925101735950) and a no-code [Agent Builder in LangSmith](https://twitter.com/LangChainAI/status/1983916519513059728), while VS Code introduced an [Agent Sessions view](https://twitter.com/code/status/1984322058503807066) to manage agents. The vLLM project released [Sleep Mode](https://twitter.com/vllm_project/status/1983069225460650103) for fast, zero-reload model switching in multi-model serving environments. Meanwhile, Confluent is partnering with vector databases like [Weaviate](https://twitter.com/weaviate_io/status/1983921589163835398) and [Qdrant](https://twitter.com/qdrant_engine/status/1983843826436395090) to enable event-driven streaming agents.

## Research News
A new paper sparked discussion by arguing that switching from BF16 to [FP16 for RL fine-tuning](https://twitter.com/iScienceLuvr/status/1984193217617895597) can substantially [reduce numerical divergence between training and inference](https://twitter.com/QPHutu/status/1984258808332550245). In agent research, the [Agent Data Protocol (ADP)](https://twitter.com/yueqi_song/status/1983539504385253684) was introduced as a unified standard for SFT datasets. New benchmarks like [Toolathlon](https://twitter.com/junxian_he/status/1983834164727312391) and ScaleAI's [Remote Labor Index](https://scale.com/leaderboard/rli) revealed that top agents still struggle with complex tool use and real-world tasks. Liquid AI released [LFM2-ColBERT-350M](https://twitter.com/LiquidAI_/status/1983155796071325771), a multilingual late-interaction retriever, while an analysis from Epoch AI suggested that [open-weight models are catching up to closed SOTA in just ~3.5 months](https://twitter.com/EpochAIResearch/status/1983987212183335097).

## Others Topics
OpenAI reported that over [1 million users discuss suicide on ChatGPT weekly](https://www.reddit.com/r/OpenAI/comments/1oi4u53/openai_says_over_1_million_users_discuss_suicide/), sparking debate amid an ongoing lawsuit concerning the platform's safety protocols. On a lighter note, YouTuber PewDiePie showcased his [custom 10x4090 local AI lab](https://twitter.com/Yuchenj_UW/status/1984309989134254493) for running and fine-tuning large models and a member of the /r/LocalLLaMA community shared their experience [building a powerful 8x AMD MI50 rig with 256GB of VRAM for just $3,000](https://www.reddit.com/r/LocalLLaMA/comments/1nhd5ks/completed_8xamd_mi50_256gb_vram_256gb_ram_rig_for/). 
```
---

# Context
"""


def generate_newsletter(content):
    response = client.models.generate_content(
        model="riftrunner",
        contents=NEWSLETTER_PROMPT + content,
    )
    with open("newsletter.md", "w") as f:
        f.write(response.text)
    return response.text


with open("smol_last_week.md", "r") as f:
    content = f.read()
generate_newsletter(content)
