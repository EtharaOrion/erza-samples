# SUPERSEDED — these runs do not measure the current bundle

**Task:** `ghg-conversion-factor-vintage`
**Directory id (pre-repair):** `3c4a9e2d-9ac7-5281-866b-c25c151097e9`
**Current bundle task_id:** `cdd29a66-5a50-577a-972d-fadf12b3f45a`
**Delta as recorded here:** +0.976190 (no-skill n=3, with-skill n=3)

## These runs were SOUND. They simply measure bytes that no longer ship.

Stated plainly because the first version of this note implied otherwise: the leak in the
pre-repair prompt was **symmetric** - `prompts.json` is byte-identical across the no-skill and
with-skill arms, verified per task. A term present in both arms cancels in a difference, so the
Delta recorded below was not biased by it. With the selection rule handed to it in the prompt,
the no-skill arm still scored at or near zero, which is itself evidence that the lever is the
withheld VALUES rather than the rule.

So this is not a retracted measurement. It is a correct measurement of a task that has since
been changed.

## Why it is nonetheless not a live result

These runs were recorded against the bundle as it stood before the repair in `dataset` commit
`e512b11` ("Repair six measured bundles against REQUIREMENTS §4/§5/§6/§9"). That commit changed
the **agent-visible** surface of this task — `task.md` and files under `environment/` — so the
bytes the agent read are not the bytes it would read today.

The most consequential class of change was that the prompt had been stating the very rule the
process instrument grades as its crux. Removing it changes what the task asks of an unaided run,
which is exactly what the no-skill arm measures.

**A recorded run is evidence and is never rewritten or deleted, so these stay exactly as they
are.** They are simply not evidence *about the current bundle*, and the directory keeps its
pre-repair id so that stays legible rather than being laundered by a rename onto the new id.

## What replaces it

A fresh paired pilot against the repaired bytes, published under `cdd29a66-5a50-577a-972d-fadf12b3f45a`. Until that exists,
this task has **no current measured Delta** and must not be reported as though it does.
