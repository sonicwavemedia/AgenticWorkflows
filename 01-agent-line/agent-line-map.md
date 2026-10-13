# Agent Line Map: Cortex PM Chief-of-Staff Agent

> Module 1 · The Agent Line
>
> ✅ **What this validates:** every risky action has a clear owner, by the end you'll have proven an above/below-the-line map with HITL checkpoints, scored on reversibility, blast radius, and measurability.

## The workflow, decision by decision

List every discrete decision or action in your agent's workflow, then score each one and place it **above** the line (a human owns it) or **below** (the agent owns it). Borderline calls get an HITL checkpoint.

| Decision / action | Reversibility (H/M/L) | Blast radius (H/M/L) | Measurability (H/M/L) | Above / Below | HITL? |
|---|---|---|---|---|---|
| Pull project state + activity | H | L | H | Below | · |
| Decide relevant context | H | M | M | Below | required: review sources used and left out, with the draft |
| Draft the update | H | L | M | Below | required: PM reviews every draft before posting |
| Decide tone | H | L | M | Below | spot-check, while reviewing the draft |
| Decide commitment level | L | H | L | Above | human owns |
| Flag at-risk / escalation | H | M | M | Below | spot-check green runs for missed flags |
| Choose what to escalate | L | H | L | Above | human owns |
| Propose a story batch (capped) | H | L | H | Below | · (approving stories stays human) |
| Post an update / approve a company-wide one | L | H | M | Above | human owns |

## Agent anatomy (sketch)

- **Model:** Claude Opus 5.5 for both the drafter and the independent critic, at about $0.11 per run. No step-up to another model yet: for a weekly update the cost isn't worth trading quality for, and there is no eval data yet to show a cheaper model (Haiku 5.5) holds up. Revisit with evidence in M5.
- **Tools:** five read-only lookups (project, engineering activity, past-update search, roadmap, team norms) and one capped proposal tool (propose stories, which queues a batch for approval and creates nothing). There is no publish tool.
- **Memory:** keep across runs: past updates (tone and precedent), team norms, the roadmap, and PM decisions on earlier drafts. Drop after each run: the task brief, raw pulled activity, rejected drafts, and anything confidential or embargoed, which must never be copied into what persists. Today nothing persists; each run starts from fixtures.
- **Loop:** _placeholder, defined in M2 loop-spec.md_
- **Bounds:** _placeholder, defined in M5 bounds-and-evals.md_
- **Evals:** _placeholder, defined in M5 bounds-and-evals.md_

## The golden rule, applied

1. **Pull project state + activity** sits below the line because it's easy to reverse, has a low blast radius, and is easy to verify, deciding factor: reversibility (read-only, so a wrong pull is simply redone).
2. **Decide relevant context** sits below the line with a required review because it's easy to reverse, has a medium blast radius, and is only partly verifiable, deciding factor: blast radius (costly omissions and misinformation originate here).
3. **Draft the update** sits below the line with a required review because it's easy to reverse, has a low blast radius, and is only partly verifiable, deciding factor: reversibility (it is still a draft).
4. **Decide tone** sits below the line with a spot-check because it's easy to reverse, has a low blast radius, and is only partly verifiable, deciding factor: reversibility (tone is cheap to fix in review).
5. **Decide commitment level** sits above the line because it's hard to reverse, has a high blast radius, and is hard to verify, deciding factor: reversibility (firm wording sets larger expectations that are hard to walk back).
6. **Flag at-risk / escalation** sits below the line with a spot-check because it's easy to reverse, has a medium blast radius, and is only partly verifiable, deciding factor: blast radius (a flag only reaches the PM, who controls what happens with it).
7. **Choose what to escalate** sits above the line because it's hard to reverse, has a high blast radius, and is hard to verify, deciding factor: reversibility (a false positive can't be de-escalated easily).
8. **Propose a story batch (capped)** sits below the line because it's easy to reverse, has a low blast radius, and is easy to verify, deciding factor: blast radius (no tickets are created; it is a list only the PM sees).
9. **Post an update / approve a company-wide one** sits above the line because it's hard to reverse, has a high blast radius, and is only partly verifiable, deciding factor: reversibility (a posted update can't be unsent).

## Hardest call

**Decide relevant context.** It initially seemed a simple early data aggregation with some small judgment calls, but the potential blast radius of omitted context rippling out to potentially uncaught red flags prompted a HITL moment after the draft once I traced the risk back to this moment. Deciding axis: blast radius.
