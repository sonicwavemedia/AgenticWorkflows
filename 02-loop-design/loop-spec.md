# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> ✅ **What this validates:** the agent knows when to run and when to stop, by the end you'll have proven a one-page Loop Spec with a trigger, a definition of "done," and explicit stop conditions.
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.

## 1. Trigger & loop type

**Chosen type:** hook

**Fires on:** an inbound PM brief, or a manual prompt from the PM. One run per brief; a brief that fires twice is deduped by its brief ID (a hash of the brief text), so Cortex never drafts two updates for the same request. A ledger in `run-output/` records each drafted brief. A repeat is skipped before any model call, so it costs $0, unless the PM re-runs it on purpose with `--force`.

**Ruled out:** a heartbeat is wasted spend when nobody is asking. A cron would draft updates nobody requested and still miss off-cycle asks. A goal loop isn't needed because the critic, not Cortex, decides "done" (§2).

## 2. Goal / definition of done

After the trigger, the Cortex orchestrator runs five stages:

1. **Gather.** Pull the current sprint, repository activity, the format of the last update, Northstar roadmap goals, current sprint goals, and norms and patterns from other updates. Each pull gets an error threshold. A transient failure (an error that might clear, or empty data) is retried up to 2 times. A hard error such as `project_not_found` gets no retry, since the answer won't change. Either way, the pull is then flagged as a loop failure and the run moves on. A **known gap** (no tool provides the item, such as sprint goals) is flagged with a labeled stand-in instead; it doesn't make the status yellow or trigger an escalation by itself. All flags are surfaced once gathering is complete.
2. **Analyze.** Organize what was gathered and propose stories from it, as drafts only. Nothing is created or posted. Stories are build work only, with no rollout, release or launch stories, since humans own launches.
3. **Draft.** Write the status update:
   - Red or yellow for blockers, impediments, loop failures, or anything that needs human input. Green only when no relevant loop or process has a blocker.
   - **Status unknown**, with no color, when the project's own state or activity can't be pulled (such as `project_not_found`). Red would tell leadership the project is failing.
   - Call out high-status or high-blast-radius inputs in the status indicators.
   - Describe work only as far as the data shows: merged PRs are "merged", not "shipped" or "live", unless the data shows a release or rollout.
   - Add follow-up actions and the next logical stories from the PRD.
   - The update's "Next" line names only approved or in-progress work. Proposed stories stay in their own section until they're approved.
   - Add a short **left out** section covering what was excluded, especially borderline items.
   - The leadership update comes first, in the shape and length of the last update, with the status stated once. Details, stories, flags and exclusions follow below it, then a compact sources list with one line per section.
4. **Critic review.** An independent critic reviews the process, reasoning, flags, and draft, including escalated drafts. It re-pulls the dynamic sources itself, using read-only tools: project, activity and past updates. It checks the static ones, roadmap and norms, against the full copy already in the trace, and re-pulls those only if that copy is missing. It confirms each re-pull worked and the data is coherent. Factual problems go back to Cortex as fix requests: Cortex re-pulls only the specific data needed, corrects the draft, and the critic reviews it again (2 rounds max). Only what Cortex can't resolve (decisions, owners, approvals, missing data) is flagged to the user.
5. **Hand off to the human review checkpoint.** Everything stays in draft form; nothing is posted, published, created, or modified externally. The saved draft carries the critic's flags for the PM. The run reports its cost and the cost cap.

**Done =** a critic-passed draft update and queued story proposals, held for PM review, with the run cost reported.

## 3. Stop conditions

| Condition | What it looks like | What happens |
|---|---|---|
| **Success** | The critic passes the draft (`verdict: pass`). | Stop at the human review checkpoint. The draft is saved to `run-output/`, nothing is posted, and cost plus cap are shown. |
| **Stuck / give up** | A pull fails or is empty after 2 retries, or hits a hard error once (flagged, run continues). Or the critic rejects the draft 2x, the run hits 8 iterations, or the run hits the $0.50 cost cap. | For a failed pull: flag it in the draft. For the others: halt, hold the last draft, and log why. |
| **Escalate to human** | Sev-1 or launch_hold, an unconfirmed date needed, confidential or embargoed content involved, the story batch over the cap of 10, a prompt injection in the brief (stories may still be proposed from real project data, labeled as coming from a flagged brief), or a required pull failed after retries. A known gap with a labeled stand-in is not an escalation. | Cortex ends with `ESCALATE:`. Once the critic checks it, the draft is held at the human review checkpoint and labeled as escalated, not approved. |

## 4. State

**Within a run:** the trace (brief + every tool call and result), retry counters, revision count, cost meter, last draft, and the critic's flags. Critic fix requests feed back to Cortex inside the run.

**Across runs (today):** only the dedupe ledger (`run-output/processed-briefs.json`) and saved drafts in `run-output/`.

**Across runs (planned, M4):** a PM-approved lessons list (corrections the PM made, or fix requests the critic raised repeatedly and the PM approved), read at Gather. Cortex never writes to it on its own.

**Scope:** one brief, one project. Nothing confidential persists: saved drafts say "1 confidential item excluded" without naming it.

## 5. The five things a loop can lean on

| Component | For Cortex |
|---|---|
| **Work tree** (isolated workspace per run, a git worktree) | Not needed yet, because Cortex only reads data and writes one draft per brief, with no code edits to isolate. Revisit for parallel briefs in M6. |
| **Skills** (reusable capabilities) | Not needed yet, because there's one workflow and it lives in `CORTEX_SYSTEM`. A second update type would make the format-matching step a skill. |
| **Plugins / connectors** (tools & access, optional if you don't have one yet) | None: mock tools over dummy fixture data. A real activity source (GitHub/Jira) comes later, read-only, with no posting connector ever. |
| **Subagents** (independent check when the loop can't grade itself) | **Critic.** A separate model call that never saw the drafting. It re-pulls data through read-only tools and sends fix requests back, with a cap of 2 revision rounds. Full map in M3. |
| **State tracking** | The dedupe ledger, the saved drafts (with cost, state and critic flags), and the per-run cost meter. |

> Context plan (M4) and the hand-off to bounds & evals (M5) come in later modules, you'll add them to their own deliverables then, not here.

## Link to live loop

`00-build/agent.py` (loop) · `00-build/prompts.py` (stages + critic) · `00-build/critic.py` (critic re-pulls)
