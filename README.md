# VeritasAgent

VeritasAgent reviews written conversations and points out where the text itself looks risky or unreliable.

It focuses on **what is said**, not who said it.

## What it looks for

- **Factual claims**: statements that can be true or false (not questions or opinions).
- **Contradictions**: two parts of the conversation that can’t both be true at the same time.
- **Missing support**: confident statements that aren’t backed up by evidence in the conversation.
- **Misleading framing**: selective summaries or overconfident “always/never/everyone” style claims.
- **Nonsense / category errors**: sentences that don’t make coherent sense as written.
- **Weak reasoning**: “because/therefore” arguments that don’t actually follow.
- **Context mistakes**: ignoring corrections, time changes, or earlier details.

## How to read its output

VeritasAgent produces structured findings that:

- keep **severity** separate from **confidence**
- include the **supporting text snippets** it relied on
- clearly mark things as **unverified** when the conversation doesn’t contain enough evidence

## Evaluation (What the UI shows)

This repo includes a small web UI that lets you browse evaluation datasets:

- the raw conversation
- which checks/categories are expected for that conversation (if the dataset includes labels)
- quick filtering and full-screen detail modals

The UI is a dataset explorer; tracked While runs and charts live in the While dashboard.
