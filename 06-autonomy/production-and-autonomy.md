# Production & Autonomy: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 5, how you'd ship it, govern it, and widen trust over time
>
> ✅ **What this validates:** you can ship it, govern it, and widen trust deliberately, by the end you'll have proven an autonomy dial, a Trust Ladder rung with its eval gate, and a governance plan.

## Autonomy Dial by segment

_Autonomy is a product decision per user, not one global setting._

| Segment | Desired autonomy | Why |
|---|---|---|
| Seasoned PM who owns the project | bounded-autonomous | High context, so they can spot-check Green runs that the critic passed. Non-Green runs, escalations and critic fails are still caught and reviewed in full. |
| New PM / APM taking over a project | supervised | Full review of every draft and context decision: they don't yet know what's missing from the update. |
| Eng lead using the story proposals | assisted | Cortex suggests stories; the eng lead edits the batch before sprint planning, since stories are build commitments they own. |

The dial changes only which below-the-line tasks pause for review. Commitment level, choosing what to escalate, and posting stay human-owned for every segment.

## Trust Ladder

- **Current rung:** supervised. Cortex does the whole job (pulls, drafts, queues stories, critic check), and every run stops at the HITL checkpoint for PM review. Nothing posts.
- **Eval gate to reach the next rung (bounded-autonomous, seasoned-PM segment, Green runs only):** all 6 M5 trajectory evals (EV-1 to EV-6) pass in CI on every prompt, tool or model change, **and** over 6 weeks with at least 20 supervised runs (whichever comes later):
  - EV-4 task completion ≥95%
  - EV-6 grounding: 0 factual errors found by the PM in critic-passed drafts
  - EV-5 safety: 0 unsafe actions and 0 confidential names
  - EV-3 recovery: replay R6 (`get_activity` returns a 500) recorded and passing: ≤2 retries, then escalate with "Status unknown", no invented data, within 8 iterations
- **Not met yet:** EV-3 (recovery) has no recorded run (replay R6 is planned) and the timeout bound isn't built. Plan: record R6, build the 90s / 5-min timeout, then start the 6-week window.
- **Incident record so far:** fixture runs only (M2–M6). 0 unsafe actions, 0 confidential names, 0 runs over the cost cap. One Cortex–critic dispute (Yellow vs Green) hit the revision cap and escalated as designed. That counts as an escalation, not an incident.
- **Clean record for the window:** 0 trust incidents, meaning no unsafe action, no confidential name, no factual error the critic passed, and no run over the cap. Escalations are not incidents.

## Deployment plan

- **Runtime:** serverless function, run on demand when a PM brief arrives. It matches the M2 hook loop (one run per brief, duplicate briefs skipped), and nothing needs to run between briefs.
- **Operator / on-call owner:** Carlos G (Northstar PM) operates it. Escalation path: the product lead who requested the update, then the owner of the Anthropic console key.
- **Rollback:** smallest lever first: (1) drop the dial a rung (bounded-autonomous → supervised); (2) revert the prompt or model (`git revert` of `prompts.py` or `CORTEX_MODEL`); (3) remove a tool from `TOOLS`. Full stop: revoke the API key.
- **Monitoring:** weekly review of four signals: eval pass % (CI), escalation rate, cost per run (alert above $0.40), and trust incidents. Every critic fail or escalation becomes a new replay fixture (M5 rule).

## ROI metrics (beyond adoption & tokens)

| Metric | Target | How it's captured |
|---|---|---|
| Outcome: PM time per weekly update | ≤10 min of review, down from about 45 min by hand | PM logs review time per run |
| Cost to serve | ≤$0.20 per run on average (today $0.11–0.17) | Run cost line Cortex prints on every run |
| Trust incidents | 0 per month (definition in the Trust Ladder) | Logged in the weekly review |

## Widen-autonomy decision rule

Turn the dial up one rung for a segment only after the Trust Ladder gate is met for that segment, and only if no trust incident happened in that window. Any incident drops the dial a rung and restarts the window.

## Governance & forward strategy

- **Compliance:** confidential or embargoed projects are counted, never named, in any saved output. No customer PII enters a prompt (tools return project data only). Pasted notes are treated as unverified.
- **Safety:** above the line for everyone: posting, commitment level, and choosing what to escalate. No write tools exist. Kill switch: revoke the API key or hit the $15 console limit.
- **Reliability:** 8 iterations, 2 critic revisions, $0.75 per run, 10-story queue cap; escalate when stuck. If the model is down, the run fails and escalates, and the PM writes that week's update by hand. Gaps: the 90s per tool call / 5-min per run timeout is planned, and EV-3 recovery (replay R6) isn't recorded yet. Both must be done before the bounded-autonomous window starts.
- **Strategy:** next segment: the new PM, from supervised to bounded-autonomous, gated by the same evals plus 4 weeks of their approved drafts. Next capability: a scoped one-time send to the PM's own team channel, gated by EV-5 and a recorded test of the single-use send credential.
