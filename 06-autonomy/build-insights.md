# Build Insights: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 4, what you learned building it
>
> ✅ **What this validates:** you can reflect on what building it taught you, by the end you'll have proven the friction, the learning, and the aha that changes how you'd design your next agent.

## Friction

Forcing a failure was harder than building the happy path. Weakening the prompt didn't work, because the model refused to invent dates or metrics. I had to inject the fault at the tool layer (a Sev-1 appearing after the first pull). Also: the course assumed OpenAI, so labs needed translating, and clearing the terminal once cost me a re-run.

## Learning

1. Deciding what context goes in is the riskiest below-the-line step, because omissions travel further than mistakes.
2. An independent critic with its own re-pull catches what self-review can't.
3. Bounds and missing tools, not prompts, are what make bad actions impossible.

## Aha moment

Seeing evals actually work in the wild; especially a max-iterations loop cap, showed me how a simple guardrail can drastically improve the cost and effectiveness of a critical review automation. It made me understand the claims that evals are among the most important elements in practice.

## What you'd do differently

Write the evals and replay fixtures first, then refine and optimize a critic escalation path that minimized non-green run costs.
