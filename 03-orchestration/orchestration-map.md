# Orchestration Map: Cortex PM Chief-of-Staff Agent

> Module 3 · Orchestration & Subagents, ★ Deliverable 3
>
> ✅ **What this validates:** nothing advances unchecked, by the end you'll have proven a justified topology, a roster, and a validator with a defined fail action.
>
> Builds on your M2 Loop Spec. Only split one agent into a team when there's a real reason, coordination has a cost.

## 1. Why split? (or why not)

**Decision: split, but only once.** Cortex stays a single agent plus **one** validating subagent, the critic.

**One-line design:** Cortex gathers, analyzes and drafts the status update and stories, then a separate critic checks the draft (max 2 fix rounds) before it's held for PM review.

| Reason | Applies? | Why / why not |
|---|---|---|
| Independent validator | Yes | Can't grade its own homework. False negatives are a big gap. |
| Separation of concerns | No | Gather, analyze and draft feed one draft and share one trace. Splitting them adds hand-offs without stopping any real contamination. |
| Parallelism | No | It's one brief and one project, and the pulls are fast. Parallel briefs are planned for M6. |
| Context-window pressure | No, for now | The trace fits and a run costs about $0.12. Revisit when real data sources replace the fixtures. |

## 2. Topology

**Pattern:** single + subagents (one agent, one validating subagent)

```
[PM brief] → dedupe (repeat → skip, $0)
          → [Cortex: gather → analyze → draft update + stories]
          → [Critic: re-pulls, checks]
              ├ fail / fixes → Cortex (max 2) → at cap: escalate, hold draft
              └ pass → [PM review checkpoint] → saved, stories queued, nothing posted
```

## 3. Roster

| Agent / subagent | Responsibility | Runs which Loop Spec |
|---|---|---|
| Cortex | drafts the update and stories, applies fixes | M2 loop, stages 1–3 |
| Critic | validates the draft | M2 loop, stage 4 |

## 4. Communication & hand-offs

In-process Python calls; no MCP or A2A.

- **Cortex → critic:** the draft plus the trace (the brief and every tool call and result).
- **Critic → Cortex:** a JSON verdict with its reasons and fix requests.
- **To the PM:** a markdown draft that carries the critic's flags.

## 5. The validator

- **What the critic checks:** (1) every claim, number, date and status color traces to data the critic re-pulls itself · (2) correct status call ("Status unknown" if no data; "merged", not "shipped") · (3) no committed dates or launch gates; confidential items counted, never named · (4) nothing posted; stories only queued, ≤10, no launch stories · (5) failed pulls flagged; jailbreak refused and escalated
- **Fail action:** revise. The draft goes back to Cortex with the failures; anything Cortex can't fix is flagged for the PM.
- **Revision cap:** 2 rounds, then escalate and hold the last draft as "escalated", never "approved".
- **Pass action:** advances to the PM review checkpoint; never auto-sent.

## 6. State: shared vs isolated

- **Shared:** the brief, the raw tool results, and the draft.
- **Isolated:** Cortex's prompt and reasoning; the critic never sees them. The critic's prompt, re-pulls and reasoning stay with the critic; only its verdict goes back.
- **Across runs:** only the dedupe ledger and saved drafts. Nothing confidential persists.

## 7. Cost & latency budget

The critic adds about 2 model calls per draft (one round of re-pulls, then the verdict). A clean pass is about $0.12 per run. At the revision cap (2 rounds) it was $0.43, close to the $0.50 cost cap, so the cost cap is the backstop. The critic adds about 30–60 s per review, so a run at the revision cap takes a few minutes before the PM sees it. These are bounds to enforce in M5.
