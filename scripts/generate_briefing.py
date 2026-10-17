import os
import json
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

    response = client.models.generate_content(
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

    briefings = [b for b in briefings if b.get("date") != today_str]
    briefings.insert(0, new_briefing)
    briefings = briefings[:10]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(briefings, f, indent=2, ensure_ascii=False)

    print(f"Updated {json_path} with briefing: {new_briefing['title']}")

if __name__ == "__main__":
    update_briefings_json()
