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

Given planning data and clause text, write a plain-English summary focused on the user's INTENT.

CITATION RULES (strictly enforced):
- Every factual claim MUST end with a citation: [clause_ref — Source]
  Examples: [C6.2.1 — SPP 2024]  [HOB-S7.0 — Hobart LPS 2025]  [Z8.4.1 — SPP 2024]
- Only cite clause references from the CLAUSE blocks provided. DO NOT invent references.
- If no clause supports a claim, omit it or say "Confirm with your council."
- Never estimate costs, fees, or timelines unless an exact figure appears in a clause.
- Never predict council decisions. Never give legal or engineering advice.

INTENT-SPECIFIC GUIDANCE:
- granny_flat / ancillary dwelling: state whether it's permitted/discretionary, cite setback and site coverage standards if present.
- extension / alterations: state whether exempt or requires permit, cite relevant threshold.
- additional_storey: cite building height limit for the zone.
- new_dwelling: state permitted/discretionary status, cite key standards (setback, height, coverage).
- outbuilding: state whether exempt, cite size/height thresholds if present.
- just_checking: summarise zone purpose and overlay constraints.

OUTPUT STRUCTURE:
**Zone:** Zone name + what it allows/restricts for this intent + citation.
**Overlays:** List each with plain-English meaning + citation, or "No overlays."
**Permit Pathway:** Permitted / Discretionary / Exempt — cite the clause that determines this.
**Key Standards:** Any setbacks, height limits, or site coverage thresholds from the clauses.
**What This Means for You:** 2-3 sentences directly addressing the stated intent.
End with: "For professional advice, contact a building designer or your council."
"""

# Maps theLIST zone names (ZONE field) to KB clause_ref prefixes (Z8, Z9, …)
ZONE_CODE_MAP = {
    "General Residential":       "Z8",
    "Inner Residential":         "Z9",
    "Low Density Residential":   "Z10",
    "Rural Living":              "Z11",
    "Village":                   "Z12",
    "Urban Mixed Use":           "Z13",
    "Local Business":            "Z14",
    "General Business":          "Z15",
    "Central Business":          "Z16",
    "Commercial":                "Z17",
    "Light Industrial":          "Z18",
    "General Industrial":        "Z19",
    "Rural":                     "Z20",
    "Agriculture":               "Z21",
    "Landscape Conservation":    "Z22",
    "Environmental Management":  "Z23",
    "Major Tourism":             "Z24",
}

INTENT_QUERIES = {
    "granny_flat":       "ancillary dwelling secondary dwelling setback site coverage permit",
    "extension":         "alterations additions extension dwelling setback building height permit",
    "additional_storey": "building height additional storey storey setback",
    "new_dwelling":      "single dwelling new dwelling permitted use setback site coverage",
    "outbuilding":       "outbuilding garage shed carport exempt permitted development",
    "just_checking":     "permitted use discretionary prohibited zone purpose",
}

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


def _enrich_with_kb(overlay_result: dict, intent: str = "just_checking") -> str:
    """Retrieve KB clauses for each overlay and zone, intent-aware."""
    council = overlay_result.get("council", {}).get("name")
    overlays = overlay_result.get("overlays", [])
    zone = overlay_result.get("zone")
    intent_terms = INTENT_QUERIES.get(intent, "permitted use development")

    kb_context = []
    seen_refs: set[str] = set()

    def _append(clauses: list[dict], limit: int = 3) -> None:
        for c in clauses[:limit]:
            ref = c.get("clause_ref", "")
            if ref not in seen_refs:
                seen_refs.add(ref)
                kb_context.append(
                    f"CLAUSE REF: {ref}\n"
                    f"SOURCE: {c['source']}\n"
                    f"HEADING: {c['heading']}\n"
                    f"TEXT: {c['text'][:1000]}"
                )

    try:
        # 1. Overlay clauses — intent-aware fallback query
        for overlay in overlays:
            lps_ref = overlay.get("lps_ref")
            overlay_code = overlay.get("code")
            overlay_name = overlay.get("ov_name") or overlay_code or ""

            if lps_ref:
                clauses = retrieve_by_ref(lps_ref, council=council)
                if not clauses:
                    clauses = retrieve(
                        f"{overlay_name} {intent_terms}",
                        council=council,
                        overlay_code=overlay_code,
                        top_k=5,
                    )
                _append(clauses, limit=3)

        # 2a. Zone use table — intent-aware
        if zone:
            zone_name = zone.get("zone", "")
            zone_code = ZONE_CODE_MAP.get(zone_name)

            q_uses = f"{zone_name} {intent_terms} permitted discretionary prohibited"
            _append(retrieve(q_uses, council=council, zone_code=zone_code, top_k=5), limit=3)

            # 2b. Zone development standards — setbacks, height, site coverage
            q_dev = f"{zone_name} development standards setback building height site coverage floor area"
            _append(retrieve(q_dev, council=council, zone_code=zone_code, top_k=5), limit=3)

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
        kb_context = _enrich_with_kb(overlay_result, intent=intent)

        final = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Address: {address}\n"
                        f"User intent: {intent.replace('_', ' ').upper()}\n"
                        f"Mode: {mode}\n\n"
                        f"Council: {overlay_result.get('council', {}).get('name')}\n"
                        f"Zone: {overlay_result.get('zone', {})}\n"
                        f"Overlays: {overlay_result.get('overlays', [])}\n\n"
                        f"PLANNING CLAUSES FROM KNOWLEDGE BASE:\n{kb_context}\n\n"
                        f"Answer specifically for intent '{intent.replace('_', ' ')}'. "
                        "Cite every factual claim. Write your cited plain-English summary now."
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
