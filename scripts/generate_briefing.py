import os
import json
import time
import datetime
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class ExecutiveBriefing(BaseModel):
    title: str = Field(description="Board-level headline for the weekly briefing.")
    slug: str = Field(description="URL-safe slug identifier, e.g. 'edge-ai-roi-2026'.")
    date: str = Field(description="Date formatted as YYYY-MM-DD.")
    summary: str = Field(description="2-sentence executive summary.")
    tags: list[str] = Field(description="3-4 topical tags, e.g. ['Enterprise AI', 'Cloud Architecture', 'Fractional CIO'].")
    read_time: str = Field(description="Estimated read time, e.g. '3 min'.")
    content_html: str = Field(
        description="The full body formatted in clean HTML paragraphs (<p>), subheadings (<h3>), and lists (<ul><li>)."
    )

SYSTEM_PROMPT = """
You are the Executive Content Intelligence Agent for Riky Tran, Global Executive Director of IT and Fractional CIO.
Writing voice:
- Authoritative, strategic, pragmatic, and focused on real-world enterprise execution.
- Bridging high-level strategy with operational reality: enterprise AI systems, regulated life-sciences IT, edge compute, and scalable governance.
- Avoid hollow buzzwords ("game-changer", "revolutionary", "delve").
- Article structure inside content_html:
  1. <h3>The Executive Shift</h3> (The core strategic friction point).
  2. <h3>Operational Friction</h3> (Why conventional or hype-driven approaches fail).
  3. <h3>The Pragmatic Playbook</h3> (3 clear, decisive action steps for leadership).
  4. <h3>Strategic Takeaway</h3> (Concluding executive guidance).
"""

def generate_content_with_retry(client, **kwargs):
    """
    Retries transient 503 (high demand) and 429 (rate-limit) errors with exponential backoff.
    """
    max_retries = 5
    delay = 6  # Start waiting 6s, then 12s, 24s, 48s...
    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(**kwargs)
        except Exception as e:
            err_msg = str(e).upper()
            is_transient = "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
            if is_transient and attempt < max_retries:
                print(f"[Attempt {attempt}/{max_retries}] Gemini API high demand/rate limit encountered. Waiting {delay}s before retry...")
                time.sleep(delay)
                delay *= 2
            else:
                raise e

def update_briefings_json():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY environment variable.")

    client = genai.Client(api_key=api_key)
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    prompt = f"""
    Write a Fractional CIO executive briefing for the week of {today_str}.
    Date field: {today_str}.
    Topic scope: Select a timely enterprise IT challenge (e.g., enterprise shadow AI governance, cost realities of edge vs. cloud AI inference, balancing rapid AI deployment with ISO/GxP validation, or optimizing fractional tech leadership).
    """

    print(f"Generating executive briefing for {today_str} using gemini-3.8-flash...")
    response = generate_content_with_retry(
        client,
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ExecutiveBriefing,
            temperature=0.7,
        ),
    )

    new_briefing = response.parsed.model_dump()

    os.makedirs("data", exist_ok=True)
    json_path = "data/briefings.json"

    briefings = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                briefings = json.load(f)
        except json.JSONDecodeError:
            briefings = []

    # Replace entry if generated today, prepend newest, and retain exactly the latest 6
    briefings = [b for b in briefings if b.get("date") != today_str]
    briefings.insert(0, new_briefing)
    briefings = briefings[:6]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(briefings, f, indent=2, ensure_ascii=False)

    print(f"Successfully updated {json_path} with briefing: {new_briefing['title']} (Retaining latest {len(briefings)} entries)")

if __name__ == "__main__":
    update_briefings_json()
