import asyncio
import json
import os
import re
import yaml
from pathlib import Path

# This script assumes you have installed the `openai` package and set OPENAI_API_KEY.
# pip install openai pyyaml

try:
    from openai import AsyncOpenAI
except ImportError:
    print("Please install openai: pip install openai")
    exit(1)

client = AsyncOpenAI()

# The E-E-A-T Master Prompt
SYSTEM_PROMPT = """
You are an authoritative domain expert. We are rewriting content for a tool called "{tool_name}" (Category: {category}).
Description: {description}

You must demonstrate deep Expertise, Experience, Authoritativeness, and Trustworthiness (E-E-A-T) to pass Google's Helpful Content Update.
- NEVER use generic boilerplate.
- DO NOT use phrases like "standard mathematical formulas", "free to use", or "click calculate".
- Speak directly to a professional user trying to solve a complex, domain-specific problem.
"""

FAQS_PROMPT = """
Generate 4-6 highly specific frequently asked questions for {tool_name}.
Rules:
1. Questions must reflect real-world professional problems.
2. Answers must contain specific benchmarks, edge cases, formulas, or expert insights.
3. Do not include questions about privacy, cost, or basic usability.
Output strictly as a JSON object: {"faqs": [{"q": "...", "a": "..."}]}
"""

HOWTO_PROMPT = """
Write 3-5 actionable steps for using {tool_name} to solve a real-world problem.
Rules:
1. Incorporate real-world intent. Instead of "Enter values", say "Input your multi-channel ad spend...".
2. Explain the 'why' behind the steps.
Output strictly as a JSON object: {"howto_steps": [{"title": "...", "desc": "..."}]}
"""

ABOUT_PROMPT = """
Write the 'about' and 'methodology' text for {tool_name}.
Rules:
1. Explain the exact mathematical formulas, industry standards, or logic the tool uses.
2. Establish trust by explaining edge cases.
3. Output strictly as a JSON object: {"about_body": "...", "howto_calculate": "..."}
"""

async def rewrite_tool(slug, tool_data):
    print(f"Rewriting: {tool_data['name']}...")
    sys_prompt = SYSTEM_PROMPT.format(
        tool_name=tool_data['name'], 
        category=tool_data.get('category', 'Utility'),
        description=tool_data.get('description', '')
    )

    async def _call_llm(prompt):
        resp = await client.chat.completions.create(
            model="gpt-4o", # Or gemini-1.5-pro via compatible endpoint
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.4
        )
        return json.loads(resp.choices[0].message.content)

    try:
        # Run concurrently
        faqs_res, howto_res, about_res = await asyncio.gather(
            _call_llm(FAQS_PROMPT.format(tool_name=tool_data['name'])),
            _call_llm(HOWTO_PROMPT.format(tool_name=tool_data['name'])),
            _call_llm(ABOUT_PROMPT.format(tool_name=tool_data['name']))
        )

        tool_data['faqs'] = faqs_res.get('faqs', tool_data.get('faqs', []))
        tool_data['howto_steps'] = howto_res.get('howto_steps', tool_data.get('howto_steps', []))
        tool_data['about_body'] = about_res.get('about_body', tool_data.get('about_body', ''))
        tool_data['howto_calculate'] = about_res.get('howto_calculate', tool_data.get('howto_calculate', ''))

        print(f"✅ Success: {tool_data['name']}")
    except Exception as e:
        print(f"❌ Error rewriting {tool_data['name']}: {e}")

async def main():
    yaml_path = Path("data/tools.yaml")
    if not yaml_path.exists():
        print("tools.yaml not found!")
        return

    with open(yaml_path, 'r', encoding='utf-8') as f:
        tools = yaml.safe_load(f)

    # Process in batches to avoid rate limits
    batch_size = 5
    for i in range(0, len(tools), batch_size):
        batch = tools[i:i+batch_size]
        tasks = [rewrite_tool(t['slug'], t) for t in batch]
        await asyncio.gather(*tasks)
        
        # Save incrementally
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(tools, f, sort_keys=False, allow_unicode=True)
            
        print(f"--- Saved batch {i//batch_size + 1} ---")
        await asyncio.sleep(2)  # Rate limit cooldown

if __name__ == "__main__":
    asyncio.run(main())
