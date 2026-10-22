# Context Engineering & Memory: Cortex PM Chief-of-Staff Agent

> Module 4 · Context Engineering & Memory
>
> ✅ **What this validates:** the agent reasons on the right, safe inputs, by the end you'll have proven a context budget, per-source retrieve-vs-long-context decisions, and a memory map with risk mitigations.
>
> 🗂️ **How the lab maps to this file:** In **Part A** (before the lecture) you don't edit this file, you rough-draft on scratch, focused on the per-source calls in **section 2** plus a quick remember/forget + "how it rots" sketch. In **Part B** (after the lecture) you complete **all five sections**; the Lab Guide's guided builder writes this file for you to copy in and commit.

## 1. Context budget

Each loop iteration gets, in priority order (first kept, last trimmed when space runs short):

1. **Task brief**: the whole brief, every run. It defines the job.
2. **Team norms**: the whole playbook, pulled fresh every run. These are the rules, and missing one breaks the update.
3. **This project's activity**: only the project in the brief. This is the evidence every claim must cite.
4. **Roadmap slice**: this project's rows only, with confidential items filtered out before Cortex sees them.
5. **Past updates**: the last 1–2 updates for the same project, for tone and precedent. Trimmed first.

Rules and evidence come before style. Other projects, confidential items and old history are never loaded.

## 2. Retrieve vs. long-context: per source

For each data source, decide: **retrieve** (narrow a large/changing corpus to the relevant slice) or **long-context** (just include a bounded set you can reason over).

| Source | Size / volatility | Decision | Why (deciding factor) |
|---|---|---|---|
| Task brief (`get_task`) | One small doc, fixed for the run | Long-context | **Size**: it's small; reason over the whole thing. |
| Team norms / playbook (`get_norms`) | Medium, must stay current | Long-context | **Volatility**: probably not too big, and we don't want to miss key principles. Pulled fresh every run, never from a stored copy. |
| GitHub/Jira activity (`get_activity`) | Large, grows daily | Retrieve | **Size**: large data set. Pull only this project's activity; every claim cites a PR or issue ID. |
| Roadmap (`get_roadmap`) | Medium, slow-changing, has confidential items | Retrieve | **Citation/audit**: confidential data must be protected. A filter removes confidential items before they reach the model, which is more robust at scale than trusting reasoning every run. The critic double-checks drafts as a backstop. |
| Past updates + decisions (`search_past_updates`) | Unbounded, grows weekly | Retrieve | **Size**: large data set. Only the last 1–2 updates on the same project matter. |

> *Build note:* the build still returns the whole roadmap today (long-context). The filter is the planned production change; for now the critic enforces the rule.

## 3. Retrieval quality plan

| Source | Failure mode | Routing | Grading | Reranking | Self-verification | Caching |
|---|---|---|---|---|---|---|
| Activity | Wrong project; invented metric or PR | ✅ Project ID from the brief only | ✅ This week's window only | ✅ Sev-1s and blockers first | ✅ Critic re-pulls independently (built) | ❌ Must be live; Sev-1s can appear mid-run |
| Roadmap | Confidential leak; another project's date committed | ✅ This project's rows only | ✅ Confidential filter drops flagged rows | – | ✅ Critic scans the draft for confidential names | ❌ No cache, so grading always sees live flags |
| Past updates | Irrelevant or other-project precedent sets the tone | – | ✅ Drop other-project matches; no match → return nothing | ✅ Newest first, keep 1–2 | – | ✅ Safe: old updates never change |

**Why:**
- **Activity:** reranking is useful as it scales. Today's volume is small, but a Sev-1 buried in a busy week is the miss that matters.
- **Roadmap:** confidentiality is handled in layers: routing narrows to this project, grading drops flagged rows, and the critic does a final check. No cache, because a copy from before a new flag (like Pulsar) would let grading pass it.
- **Past updates:** grading drops irrelevant matches. That fixes the current naive fallback (`corpus[:2]` returns unrelated updates when nothing matches).

> No retrieved source is naive RAG: each one is at least graded.

## 4. Memory map (your PM brain)

| Memory type | What Cortex stores | Read / write | Scope / TTL |
|---|---|---|---|
| **Working** (in-loop) | Brief, tool results, draft, critic feedback for this run | Cortex and critic read and write | This run only; wiped when the run ends |
| **Episodic** (past runs) | Approved past updates and decisions; processed-briefs log; saved drafts | Cortex reads; written only after PM approval | Approved updates: 2 quarters or until the norms change, whichever comes first, as tone examples (kept for audit). Brief log: 30 days. Unapproved drafts: 7 days |
| **Semantic** (durable facts/prefs) | Team norms, roadmap facts, PM preferences ("merged, not shipped") | Cortex reads only; people edit the source files | No expiry, always pulled live; learned preferences reviewed quarterly |
| **Shared** (across agents) | Run trace from Cortex to the critic; critic verdict | Cortex writes; critic reads but re-pulls rather than trusting it | This run only; verdict logged with the brief for audit |

> Read/write scope follows the M1 agent line: Cortex proposes, the PM approves, and only approved work becomes memory. The lifetimes become M5 bounds.

## 5. Memory risks & mitigations

| Risk | Where it hits Cortex | Mitigation |
|---|---|---|
| **Drift** | Past updates slowly change tone and wording ("shipped" crept in) | Norms always win over precedent; the critic checks against the norms. Updates are tagged with their norms version, and older ones stop being retrieved as examples once a norm changes. Spot-check 5 drafts a month (M5 eval). |
| **Poisoning** | A bad input is saved and trusted later: an injected brief, a wrong figure, an untagged confidential item | Only PM-approved updates are saved; injected briefs are held, not stored; facts are re-pulled live. Every roadmap item has a PM owner responsible for its confidential tag. |
| **Staleness** | An old status, metric or confidential list is reused (the Pulsar case) | Facts are never cached; episodic memory is for tone only, never facts; lifetimes as in §4. |
| **PII / retention** | Briefs and activity may hold names, customer details or embargoed info; drafts persist | Confidential items are counted, never named, in anything saved; no customer personal data in drafts; drafts deleted after 7 days; the brief log stores IDs only. |
