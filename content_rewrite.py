import asyncio
import json
import os
import re
import tempfile
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

# Types: ToolData is Dict[str, Any]; slug is str; prompts are str.
# This script assumes you have optionally installed the `openai` package and set OPENAI_API_KEY.
# pip install openai pyyaml

try:
    from openai import AsyncOpenAI
    _openai_available = True
except ImportError:  # optional dependency — allow offline import/test
    AsyncOpenAI = None  # type: ignore
    _openai_available = False
    print("openai not installed: LLM rewrite disabled (pip install openai to enable)")

if _openai_available:
    try:
        client: Optional[Any] = AsyncOpenAI() if os.getenv("OPENAI_API_KEY") else None
        if client is None:
            print("OPENAI_API_KEY not set: client disabled until configured")
    except Exception as e:
        print(f"OpenAI client init failed ({e}): running in disabled mode")
        client = None
else:
    client = None

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

async def rewrite_tool(slug: str, tool_data: Dict[str, Any]) -> None:
    print(f"Rewriting: {tool_data['name']}...")
    # FIX: was lowercase closure-captured var vs SYSTEM_PROMPT constant.
    # Use explicit `system_prompt` and pass to _call_llm to avoid shadowing/closure bug.
    system_prompt: str = SYSTEM_PROMPT.format(
        tool_name=tool_data['name'],
        category=tool_data.get('category', 'Utility'),
        description=tool_data.get('description', '')
    )

    async def _call_llm(prompt: str, system_prompt: str) -> Dict[str, Any]:
        if client is None:
            raise RuntimeError("OpenAI client not available (missing package or API key)")
        resp = await client.chat.completions.create(
            model="gpt-4o",  # Or gemini-1.5-pro via compatible endpoint
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.4
        )
        return json.loads(resp.choices[0].message.content)

    try:
        # Run concurrently
        faqs_res, howto_res, about_res = await asyncio.gather(
            _call_llm(FAQS_PROMPT.format(tool_name=tool_data['name']), system_prompt),
            _call_llm(HOWTO_PROMPT.format(tool_name=tool_data['name']), system_prompt),
            _call_llm(ABOUT_PROMPT.format(tool_name=tool_data['name']), system_prompt)
        )

        tool_data['faqs'] = faqs_res.get('faqs', tool_data.get('faqs', []))
        tool_data['howto_steps'] = howto_res.get('howto_steps', tool_data.get('howto_steps', []))
        tool_data['about_body'] = about_res.get('about_body', tool_data.get('about_body', ''))
        tool_data['howto_calculate'] = about_res.get('howto_calculate', tool_data.get('howto_calculate', ''))

        print(f"\u2705 Success: {tool_data['name']}")
    except Exception as e:
        print(f"\u274c Error rewriting {tool_data['name']}: {e}")


def _atomic_write_yaml(yaml_path: Path, payload: Any) -> None:
    """Atomically write YAML (temp file + os.replace) to avoid partial writes."""
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(yaml_path.parent), prefix=yaml_path.stem + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            yaml.dump(payload, f, sort_keys=False, allow_unicode=True)
        os.replace(tmp_name, yaml_path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass

async def main() -> None:
    yaml_path = Path("data/tools.yaml")
    if not yaml_path.exists():
        print("tools.yaml not found!")
        return

    with open(yaml_path, 'r', encoding='utf-8') as f:
        tools = yaml.safe_load(f)

    # Process in batches to avoid rate limits
    batch_size = 5
    # Support both list-style and {"tools": {...}} shapes
    if isinstance(tools, dict) and "tools" in tools and isinstance(tools["tools"], dict):
        items: List[Dict[str, Any]] = list(tools["tools"].values())
    elif isinstance(tools, list):
        items = tools
    elif isinstance(tools, dict):
        items = list(tools.values())
    else:
        print("Unknown tools.yaml shape")
        return
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        # slug may be inside item or key; fall back to name
        tasks = [rewrite_tool(t.get('slug', t.get('name', f"tool-{i+j}")), t) for j, t in enumerate(batch)]
        await asyncio.gather(*tasks)

        # Save incrementally via atomic write
        _atomic_write_yaml(yaml_path, tools)

        print(f"--- Saved batch {i//batch_size + 1} ---")
        await asyncio.sleep(2)  # Rate limit cooldown

if __name__ == "__main__":
    asyncio.run(main())
