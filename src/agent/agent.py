"""
agent.py — SiteCheck reasoning agent

Uses OpenAI-compatible SDK (OpenRouter + DeepSeek R1 for dev,
swap to Azure OpenAI for submission via env vars).

Flow:
  1. geocode_address(address) → lat/lng
  2. query_overlays(lat, lng) → overlays + zone + council
  3. retrieve KB clauses per overlay lps_ref
  4. Generate mode + intent specific plain-English response (all claims cited)
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

from src.tools.geocoder import geocode_address, AddressNotFoundError, OutsideTasmaniaError
from src.tools.thelist import query_overlays
from src.tools.retriever import retrieve, retrieve_by_ref
from src.tools.schemas import ALL_TOOLS

load_dotenv()

SYSTEM_PROMPT = """You are SiteCheck, a Tasmanian property planning assistant.

Your job: given a property address, its planning overlays, zone, and relevant planning clauses, produce a plain-English summary tailored to the user's mode and intent.

STRICT RULES:
- Every claim must be supported by a cited clause reference (e.g. "Hobart LPS C12.0") or statute (e.g. "LUPAA s.57").
- Never estimate costs, fees, or timelines unless directly stated in a cited clause.
- Never predict council decisions ("likely approved/refused").
- If information is not available in the provided clauses, say so explicitly and direct the user to their council.
- For cost or fee questions, cite the fee schedule source and year, or redirect: "Contact your council for current fees."
- Never provide legal or engineering advice.

OUTPUT FORMAT:
- Lead with overlay flags found (or "No overlays found — clean site.")
- For each overlay: plain-English explanation + cited clause reference
- Zone: what zone, what it means for the intent
- Permit pathway: permitted or discretionary, statutory timeframe if applicable
- End with: "For professional advice, contact a building designer or your council."
"""

TOOL_FUNCTIONS = {
    "geocode_address": geocode_address,
    "query_overlays": lambda lat, lng: query_overlays(lat, lng),
}


def _call_tool(name: str, args: dict) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = fn(**args)
        return json.dumps(result, ensure_ascii=False)
    except (AddressNotFoundError, OutsideTasmaniaError) as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Tool error: {str(e)}"})


def _enrich_with_kb(overlay_result: dict) -> str:
    """Retrieve KB clauses for each overlay lps_ref and append to context."""
    council = overlay_result.get("council", {}).get("name")
    overlays = overlay_result.get("overlays", [])
    zone = overlay_result.get("zone")

    kb_context = []

    try:
        for overlay in overlays:
            lps_ref = overlay.get("lps_ref")
            overlay_code = overlay.get("code")

            if lps_ref:
                clauses = retrieve_by_ref(lps_ref, council=council)
                if not clauses:
                    clauses = retrieve(
                        f"{overlay_code} {lps_ref}",
                        council=council,
                        overlay_code=overlay_code,
                        top_k=3,
                    )
                for c in clauses[:2]:
                    kb_context.append(f"[{c['clause_ref']}] {c['heading']}\n{c['text'][:500]}\nSource: {c['source']}")

        if zone and zone.get("lps_ref"):
            zone_clauses = retrieve(
                f"zone {zone.get('zone')} permitted discretionary use",
                council=council,
                top_k=3,
            )
            for c in zone_clauses[:2]:
                kb_context.append(f"[{c['clause_ref']}] {c['heading']}\n{c['text'][:500]}\nSource: {c['source']}")

    except Exception:
        return "KB unavailable — responding from overlay data only."

    return "\n\n---\n\n".join(kb_context) if kb_context else "No matching KB clauses found."


def run(address: str, mode: str, intent: str) -> dict:
    """
    Run SiteCheck agent.

    Args:
        address: Tasmanian property address
        mode:    "buyer" | "construction" | "da_owner"
        intent:  "just_checking" | "granny_flat" | "extension" | "additional_storey" | "new_dwelling" | "outbuilding"

    Returns:
        dict with keys: address, overlays, zone, council, mode, intent, response, error
    """
    client = OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    model = os.environ.get("LLM_MODEL", "deepseek/deepseek-r1")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Address: {address}\n"
                f"Mode: {mode}\n"
                f"Intent: {intent}\n\n"
                "Step 1: geocode the address. Step 2: query overlays. Step 3: I will provide KB clauses. Step 4: generate your response."
            ),
        },
    ]

    # Agent loop — tool calling
    overlay_result = None
    for _ in range(5):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=ALL_TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            break

        messages.append(msg)

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = _call_tool(name, args)

            if name == "query_overlays":
                overlay_result = json.loads(result)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    # Enrich with KB clauses
    if overlay_result:
        kb_context = _enrich_with_kb(overlay_result)
        messages.append({
            "role": "user",
            "content": f"Here are the relevant planning clauses from the knowledge base:\n\n{kb_context}\n\nNow generate your response for mode={mode}, intent={intent}. Cite every claim.",
        })

        final = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        response_text = final.choices[0].message.content
    else:
        response_text = msg.content if msg else "Unable to process address."

    return {
        "address": address,
        "mode": mode,
        "intent": intent,
        "council": overlay_result.get("council") if overlay_result else None,
        "zone": overlay_result.get("zone") if overlay_result else None,
        "overlays": overlay_result.get("overlays", []) if overlay_result else [],
        "kingborough_interim": overlay_result.get("kingborough_interim", False) if overlay_result else False,
        "response": response_text,
        "error": None,
    }


if __name__ == "__main__":
    result = run(
        address="8 Nelson Road Sandy Bay 7005",
        mode="buyer",
        intent="just_checking",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
