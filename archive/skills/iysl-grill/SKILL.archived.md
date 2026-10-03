---
name: iysl-grill
description: A relentless, user-invoked interview to sharpen a plan, decision, or design.
disable-model-invocation: true
---

Interview the user relentlessly until reaching a shared understanding. Map the
subject as a **decision tree**: every decision branches into the decisions that
depend on it.

Work the tree in **rounds**. The **frontier** is every decision whose
prerequisites are already settled—the questions that can be asked now without
guessing at answers not yet given. Ask the whole frontier in one round: number
each question and give a recommended answer. Then wait for the user's answers
before the next round.

Format each question like this:

```text
❓ **Q1** - **<question title>**: <question body, including choices when useful>

➡️ <recommended answer>
```

Let each answer reshape the tree. Settled decisions push the frontier outward
and unblock questions that depend on them. Recompute the frontier before every
round. Keep a question for a later round when its answer depends on another
question that is still open in the current round.

Find facts instead of asking the user for them. When a frontier question needs
a fact from the environment, use the filesystem and tools or dispatch a bounded
subagent to find it. Treat a running exploration as an unsettled prerequisite:
hold only its downstream questions and ask the rest of the frontier now. Put
the decisions to the user and wait for their answers.

Finish only when the frontier is empty: every branch of the decision tree has
been visited and nothing remains silently assumed. Keep the session stateless;
do not write plans, specs, tickets, ADRs, or code. Do not act on the result until
the user confirms shared understanding.
