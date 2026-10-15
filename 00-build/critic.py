"""Independent validator (M3). A separate model call that never saw the drafting
context, so it can't inherit the draft's blind spots. Returns a pass/fail verdict.
The revision cap that stops a critic<->drafter loop lives in `agent.py`.
"""

from __future__ import annotations

import json

from prompts import CRITIC_SYSTEM

# The critic may re-pull data, but only through these read-only tools.
READ_ONLY_TOOLS = ["get_project", "get_activity", "search_past_updates",
                   "get_roadmap", "get_norms"]
MAX_CRITIC_TURNS = 4  # tool rounds before the critic must give its verdict


def _parse_verdict(text: str) -> dict:
    try:
        verdict = json.loads(text[text.index("{"):text.rindex("}") + 1])
        if verdict.get("verdict") not in ("pass", "fail"):
            raise ValueError
    except ValueError:
        return {"verdict": "fail", "reasons": ["critic returned unparseable output"]}
    return verdict


def review(client, model: str, proposed_output: str, source_data: str,
           tool_schemas: list, tool_fns: dict) -> dict:
    """Return {"verdict": "pass"|"fail", "reasons", "reruns", "flags_for_user"}.
    The critic can re-pull data through read-only tools to double-check claims."""
    schemas = [t for t in tool_schemas if t["name"] in READ_ONLY_TOOLS]
    messages = [{"role": "user", "content":
                 f"CORTEX TRACE (brief + every tool call and result):\n{source_data}\n\n"
                 f"CORTEX PROPOSED OUTPUT:\n{proposed_output}"}]
    usage = {"prompt": 0, "completion": 0, "cache_write": 0, "cache_read": 0}

    for turn in range(MAX_CRITIC_TURNS + 1):
        # On the last turn, withhold tools so the critic has to give its verdict.
        kwargs = {"tools": schemas} if turn < MAX_CRITIC_TURNS else {}
        resp = client.messages.create(model=model, max_tokens=4000,
                                      system=CRITIC_SYSTEM, messages=messages,
                                      cache_control={"type": "ephemeral"}, **kwargs)
        usage["prompt"] += resp.usage.input_tokens
        usage["completion"] += resp.usage.output_tokens
        usage["cache_write"] += resp.usage.cache_creation_input_tokens or 0
        usage["cache_read"] += resp.usage.cache_read_input_tokens or 0

        calls = [b for b in resp.content if b.type == "tool_use"]
        if not calls:
            verdict = _parse_verdict("".join(b.text for b in resp.content if b.type == "text"))
            verdict["_usage"] = usage
            return verdict

        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for call in calls:
            result = tool_fns[call.name](**call.input) if call.name in READ_ONLY_TOOLS \
                else {"error": "not_permitted", "tool": call.name}
            print(f"[critic rerun] {call.name}({call.input})")
            print(f"          -> {json.dumps(result)[:200]}")
            results.append({"type": "tool_result", "tool_use_id": call.id,
                            "content": json.dumps(result)})
        messages.append({"role": "user", "content": results})

    verdict = {"verdict": "fail", "reasons": ["critic did not reach a verdict"]}
    verdict["_usage"] = usage
    return verdict
