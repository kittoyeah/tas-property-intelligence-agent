"""
agent.py — CanIBuild reasoning agent

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

TOOL_SYSTEM_PROMPT = """You are CanIBuild, a Tasmanian property planning assistant.
Use the provided tools to look up planning data for the given address. Call geocode_address first, then query_overlays."""

RESPONSE_SYSTEM_PROMPT = """You are CanIBuild, a Tasmanian property planning assistant.

Given planning overlay data and relevant clause text, write a plain-English summary for the user.

CITATION RULES (strictly enforced):
- Every factual claim MUST end with a citation in this exact format: [clause_ref — Source]
  Examples: [C6.2.1 — SPP 2024]  [HOB-S7.0 — Hobart LPS 2025]
- Only cite clause references that appear in the CLAUSE blocks provided below.
- DO NOT invent clause references or URLs.
- If no clause supports a claim, omit the claim or say "Confirm with your council."
- Never estimate costs, fees, or timelines unless the exact figure is in a provided clause.
- Never predict council decisions. Never give legal or engineering advice.

OUTPUT STRUCTURE:
Overlays: list each with plain-English meaning + citation, or "No overlays — clean site."
Zone: zone name, what it means for the stated intent + citation.
Permit Pathway: Permitted / Discretionary / Exempt — cite the determining clause.
What This Means for You: 2-3 sentences tailored to mode and intent.
End with: "For professional advice, contact a building designer or your council."
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
                    kb_context.append(
                        f"CLAUSE REF: {c['clause_ref']}\n"
                        f"SOURCE: {c['source']}\n"
                        f"HEADING: {c['heading']}\n"
                        f"TEXT: {c['text'][:600]}"
                    )

        if zone and zone.get("lps_ref"):
            zone_clauses = retrieve(
                f"zone {zone.get('zone')} permitted discretionary use",
                council=council,
                top_k=3,
            )
            for c in zone_clauses[:2]:
                kb_context.append(
                    f"CLAUSE REF: {c['clause_ref']}\n"
                    f"SOURCE: {c['source']}\n"
                    f"HEADING: {c['heading']}\n"
                    f"TEXT: {c['text'][:600]}"
                )

    except Exception:
        return "KB unavailable — responding from overlay data only."

    return "\n\n---\n\n".join(kb_context) if kb_context else "No matching KB clauses found."


def run(address: str, mode: str, intent: str) -> dict:
    """
    Run CanIBuild agent.

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
        {"role": "system", "content": TOOL_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Address: {address}\nMode: {mode}\nIntent: {intent}",
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

        final = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Address: {address}\nMode: {mode}\nIntent: {intent}\n\n"
                        f"Council: {overlay_result.get('council', {}).get('name')}\n"
                        f"Zone: {overlay_result.get('zone', {})}\n"
                        f"Overlays: {overlay_result.get('overlays', [])}\n\n"
                        f"PLANNING CLAUSES FROM KNOWLEDGE BASE:\n{kb_context}\n\n"
                        "Write your cited plain-English summary now."
                    ),
                },
            ],
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
