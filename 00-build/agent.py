"""Cortex, a minimal, explicit agent loop you (and your coding agent) can read end
to end. This is the agent you ship: your PM chief-of-staff. You build it by
directing your coding agent (Claude Code / Cursor / Codex) to shape this file. You
never have to hand-write it.

Every bound the course talks about is visible right here in code, not buried in a
framework: the max-iteration counter, the cost cap, the revision cap, the
stop/escalate conditions, the auto-queue cap, and the absence of any publish tool.

Usage (ask your coding agent to run these for you, or run them yourself):
    python agent.py                # runs the happy-path task (weekly status update)
    python agent.py missing-data   # the stuck/escalate case
    python agent.py jailbreak       # the prompt-injection refusal case
    python agent.py happy --force   # re-draft a brief that was already drafted

Every run ends by showing the drafted status update in a FINAL STATUS UPDATE block
(or LAST DRAFT, held, if a bound trips), and saves it to run-output/. That file is
always a draft held for a human, it is never posted, there is no publish tool.

Requires ANTHROPIC_API_KEY in your environment (see .env.example). Model and bounds
are read from env so you can tune them, that tuning is your M5 deliverable.

The loop is deliberately transparent (hand-written tool-calling on the anthropic
client) so a grader can see the machinery. Keep the bounds explicit if you rework it.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
import sys
from pathlib import Path

import anthropic

import tools
from critic import review
from prompts import CORTEX_SYSTEM

try:  # load .env if python-dotenv is installed; harmless if it isn't
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# --- Bounds (your M5 deliverable: tune these and justify them) ----------------
MODEL = os.environ.get("CORTEX_MODEL", "claude-opus-5-5")
MAX_ITERATIONS = int(os.environ.get("CORTEX_MAX_ITERATIONS", "8"))
MAX_REVISIONS = int(os.environ.get("CORTEX_MAX_REVISIONS", "2"))
COST_CAP_USD = float(os.environ.get("CORTEX_COST_CAP_USD", "0.50"))
MAX_QUEUE_ITEMS = int(os.environ.get("CORTEX_MAX_QUEUE_ITEMS", "10"))
# Gather error threshold (M2 loop spec): 1 try + this many retries per tool, then flag.
MAX_PULL_RETRIES = int(os.environ.get("CORTEX_MAX_PULL_RETRIES", "2"))
# Rough $ per 1M tokens for your chosen model, set to match its pricing.
PRICE_IN = float(os.environ.get("CORTEX_PRICE_IN_PER_M", "4.00"))
PRICE_OUT = float(os.environ.get("CORTEX_PRICE_OUT_PER_M", "20.00"))
# Prompt caching multipliers on the input price (Opus 5.5: 5-min write 1.25x, read 0.05x).
CACHE_WRITE_MULT = float(os.environ.get("CORTEX_CACHE_WRITE_MULT", "1.25"))
CACHE_READ_MULT = float(os.environ.get("CORTEX_CACHE_READ_MULT", "0.05"))
# Per-response output ceiling (not a spend bound; the cost cap above is).
MAX_TOKENS = int(os.environ.get("CORTEX_MAX_TOKENS", "16000"))

TOOL_SCHEMAS = [
    {
        "name": "get_project", "description": "Look up a project by its ID (status, flags, linked PRD).",
        "input_schema": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}},
    {
        "name": "get_activity",
        "description": "Pull recent engineering activity for a project (merged PRs, open issues, Sev-1s).",
        "input_schema": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}},
    {
        "name": "search_past_updates",
        "description": "Search previous status updates and decisions for tone and precedent.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}},
    {
        "name": "get_roadmap",
        "description": "Return the roadmap. Some items are flagged confidential/embargoed.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}},
    {
        "name": "get_norms", "description": "Return the team norms / PM playbook the agent must follow.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}},
    {
        "name": "propose_stories",
        "description": "Queue a set of backlog stories for human approval (creates nothing; rejected above the item cap).",
        "input_schema": {"type": "object", "properties": {
            "project_id": {"type": "string"},
            "stories": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"}}, "required": ["project_id", "stories"]}},
]


# Hard errors won't change on retry, so they get no retries (loop spec §2).
HARD_ERRORS = {"project_not_found", "invalid_stories"}


def _is_bad_pull(result: dict) -> bool:
    """A pull counts against the error threshold if it errored or came back empty."""
    return "error" in result or result.get("activity") == [] or result.get("matches") == []


class Bounds:
    """Tracks spend and trips the cost cap. This is enforced OUTSIDE the model."""

    def __init__(self):
        self.cost = 0.0

    def add(self, usage) -> None:
        self.add_tokens(usage.input_tokens, usage.output_tokens,
                        usage.cache_creation_input_tokens or 0,
                        usage.cache_read_input_tokens or 0)

    def add_tokens(self, uncached: int, output: int, cache_write: int = 0,
                   cache_read: int = 0) -> None:
        self.cost += (uncached * PRICE_IN
                      + cache_write * PRICE_IN * CACHE_WRITE_MULT
                      + cache_read * PRICE_IN * CACHE_READ_MULT
                      + output * PRICE_OUT) / 1_000_000

    def over_cap(self) -> bool:
        return self.cost >= COST_CAP_USD


OUTPUT_DIR = Path(__file__).parent / "run-output"
# Dedupe ledger (loop spec §1): brief ID -> the draft already produced for it.
LEDGER = OUTPUT_DIR / "processed-briefs.json"


def brief_id(body: str) -> str:
    """Fixtures carry no ID field, so the brief's ID is a hash of its text."""
    return hashlib.sha256(body.strip().encode()).hexdigest()[:12]


def _load_ledger() -> dict:
    try:
        return json.loads(LEDGER.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def record_brief(bid: str, which: str, state: str, cost: float) -> None:
    ledger = _load_ledger()
    ledger[bid] = {"fixture": which, "state": state, "cost": round(cost, 4),
                   "draft": f"run-output/status-update-{which}.md",
                   "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    OUTPUT_DIR.mkdir(exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=1))


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n{text}\n{'=' * 64}")


def emit_deliverable(which: str, draft: str, *, accepted: bool,
                     reason: str, cost: float, flags: list | None = None,
                     bid: str | None = None) -> None:
    """Surface AND persist Cortex's drafted status update so it can't get lost in
    the scroll-back. This is still a DRAFT held for human review, never a post,
    there is no publish tool, and an escalated run is held on purpose.

    Runs on every exit: an accepted pass prints the FINAL update; a bound trip or
    escalation prints the LAST draft it managed to write plus why it was held.
    """
    banner("FINAL STATUS UPDATE (draft, validator-approved, NOT posted)" if accepted
           else "LAST DRAFT (held, NOT posted, escalated to a human)")
    if draft.strip():
        print(draft.rstrip())
    else:
        print("(Cortex stopped before it produced a draft, nothing to show.)")
    if not accepted:
        print(f"\nWhy it was held: {reason}")
    # Loop spec stage 4: what only the PM can resolve travels with the draft.
    flags_md = ""
    if flags:
        flags_md = "\n\n---\n\n**Critic flags for you**\n" + "".join(
            f"- {f}\n" for f in flags)
        print(flags_md.rstrip())
    print(f"\nRun cost ≈ ${cost:.4f} (cap ${COST_CAP_USD:.2f})")

    if draft.strip():
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"status-update-{which}.md"
        state = "accepted by validator" if accepted else "HELD, escalated"
        out.write_text(
            f"<!-- Cortex draft, {state}; NOT posted. Run cost ~ ${cost:.4f}. -->\n"
            f"<!-- {reason} -->\n\n{draft.rstrip()}{flags_md}\n", encoding="utf-8")
        if bid:
            record_brief(bid, which, state, cost)
        print(f"\nSaved draft -> {out.relative_to(Path(__file__).parent)}  "
              f"(for your review, nothing was posted)")


def run(which: str = "happy", force: bool = False) -> None:
    task = tools.get_task(which)
    if "error" in task:
        print(task)
        return

    bid = brief_id(task["body"])
    seen = _load_ledger().get(bid)
    if seen and not force:
        banner(f"DUPLICATE BRIEF {bid}, already drafted ({seen['state']}) at "
               f"{seen['at']} -> {seen['draft']}. Skipping, no model calls, $0. "
               f"Use --force to re-draft.")
        return

    client = anthropic.Anthropic()
    bounds = Bounds()

    banner(f"CORTEX RUN, fixture: task-{which}, brief {bid}  "
           f"(auto-queue cap {MAX_QUEUE_ITEMS} items)")
    print(task["body"])

    messages = [
        {"role": "user", "content": f"PM task brief:\n\n{task['body']}"},
    ]
    source_log: list[str] = [task["body"]]
    revisions = 0
    last_draft = ""
    last_flags: list = []
    bad_pulls: dict[str, int] = {}  # tool name -> failed/empty pulls so far

    for step in range(1, MAX_ITERATIONS + 1):
        if bounds.over_cap():
            reason = f"cost cap ${COST_CAP_USD} hit at ${bounds.cost:.4f}"
            banner(f"BOUND TRIPPED, {reason}. Halting and escalating to a human.")
            emit_deliverable(which, last_draft, accepted=False,
                             reason=reason, cost=bounds.cost,
                             flags=last_flags, bid=bid)
            return

        resp = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, system=CORTEX_SYSTEM,
            messages=messages, tools=TOOL_SCHEMAS,
            # Auto-cache the growing trace so each loop turn re-reads it at 0.05x.
            cache_control={"type": "ephemeral"})
        bounds.add(resp.usage)

        if resp.stop_reason == "refusal":
            reason = "model declined the request (refusal)"
            banner("MODEL REFUSED. Halting and escalating to a human.")
            emit_deliverable(which, last_draft, accepted=False,
                             reason=reason, cost=bounds.cost,
                             flags=last_flags, bid=bid)
            return

        tool_calls = [b for b in resp.content if b.type == "tool_use"]
        if tool_calls:
            # Echo the full content back (thinking blocks included), then return
            # every tool result in ONE user message.
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for call in tool_calls:
                fn, args = call.name, call.input
                if bad_pulls.get(fn, 0) > MAX_PULL_RETRIES:
                    result = {"error": "retry_limit_reached", "tool": fn,
                              "action": "flag this gather as failed and move on"}
                else:
                    result = tools.TOOLS[fn](**args)
                    if result.get("error") in HARD_ERRORS:
                        bad_pulls[fn] = MAX_PULL_RETRIES + 1
                    elif _is_bad_pull(result):
                        bad_pulls[fn] = bad_pulls.get(fn, 0) + 1
                source_log.append(f"{fn}({args}) -> {json.dumps(result)}")
                print(f"\n[step {step}] TOOL {fn}({args})")
                print(f"          -> {json.dumps(result)[:300]}")
                results.append({"type": "tool_result", "tool_use_id": call.id,
                                "content": json.dumps(result)})
            messages.append({"role": "user", "content": results})
            continue

        # No tool calls => Cortex produced a proposed output. Validate it.
        proposed = "".join(b.text for b in resp.content if b.type == "text")
        last_draft = proposed
        print(f"\n[step {step}] PROPOSED OUTPUT:\n{proposed}")

        banner("CRITIC, independent validation")
        verdict = review(client, MODEL, proposed, "\n".join(source_log),
                         TOOL_SCHEMAS, tools.TOOLS)
        # Estimate critic spend too.
        u = verdict["_usage"]
        bounds.add_tokens(u["prompt"], u["completion"], u["cache_write"], u["cache_read"])
        print(json.dumps({k: v for k, v in verdict.items() if k != "_usage"}, indent=2))
        last_flags = verdict.get("flags_for_user") or []

        fixes = verdict.get("fix_requests") or []
        if verdict["verdict"] == "pass" and fixes and revisions < MAX_REVISIONS:
            # Loop spec stage 4: the critic's fixable findings go back to Cortex for a
            # targeted re-pull and correction before anything reaches the PM.
            revisions += 1
            print(f"\n-> critic sent {len(fixes)} fix request(s); revision "
                  f"{revisions}/{MAX_REVISIONS}")
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content":
                             "The critic sent these fix requests. For each one, re-pull "
                             "only the specific data it needs (if any), then correct the "
                             "claim or keep it and say why. Return the full corrected "
                             f"output:\n{json.dumps(fixes, indent=1)}"})
            continue

        if verdict["verdict"] == "pass" and proposed.lstrip().startswith("ESCALATE"):
            reason = "Cortex escalated (critic confirmed the draft is safe to hold)"
            banner(f"HITL CHECKPOINT, escalated to you. Nothing posted, no commitments "
                   f"made. Run cost ≈ ${bounds.cost:.4f} (cap ${COST_CAP_USD:.2f})")
            emit_deliverable(which, proposed, accepted=False,
                             reason=reason, cost=bounds.cost,
                             flags=last_flags, bid=bid)
            return

        if verdict["verdict"] == "pass":
            banner(f"HITL CHECKPOINT, status update + any proposed stories queued for "
                   f"your review. Nothing posted, no commitments made. "
                   f"Run cost ≈ ${bounds.cost:.4f} (cap ${COST_CAP_USD:.2f})")
            emit_deliverable(which, proposed, accepted=True,
                             reason="validator passed", cost=bounds.cost,
                             flags=last_flags, bid=bid)
            return

        if revisions >= MAX_REVISIONS:
            reason = f"validator rejected {MAX_REVISIONS}x (revision cap)"
            banner(f"REVISION CAP hit ({MAX_REVISIONS}). Escalating to a human "
                   f"instead of looping. Run cost ≈ ${bounds.cost:.4f}")
            emit_deliverable(which, last_draft, accepted=False,
                             reason=reason, cost=bounds.cost,
                             flags=last_flags, bid=bid)
            return

        revisions += 1
        print(f"\n-> critic rejected; revision {revisions}/{MAX_REVISIONS}")
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content":
                         "A validator rejected that for these reasons: "
                         f"{verdict['reasons']}. Fix it or escalate."})

    banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) reached without finishing. "
           f"Escalating. Run cost ≈ ${bounds.cost:.4f}")
    emit_deliverable(which, last_draft, accepted=False,
                     reason=f"max iterations ({MAX_ITERATIONS}) reached",
                     cost=bounds.cost,
                             flags=last_flags, bid=bid)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    run(args[0] if args else "happy", force="--force" in sys.argv[1:])
