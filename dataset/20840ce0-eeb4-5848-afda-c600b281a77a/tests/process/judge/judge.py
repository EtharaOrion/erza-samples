"""Non-deterministic channel: an LLM judge over the agent's trajectory.

These are the process questions no regex can decide - "did the run treat the two
earlier collection periods as needing different corrections", "did it verify
against something that could actually disagree". The judge reads the whole trajectory plus the answer-free
TRUTH.md and returns one Yes/No verdict per criterion, with a rationale.

Design notes
------------
* Verdicts are strictly binary. No 0.7s. A criterion is satisfied or it is not.
* A panel of N independent judges votes; the verdict is the majority. With
  --judges 1 it degrades to a single judge (cheap, for iteration).
* Every judge sees the same trajectory and the same criteria in the same order,
  so the run is reproducible modulo model sampling.
* `--offline` skips the API entirely and emits `voted: false` for every
  criterion, so the scoring path can be verified end-to-end without credentials.
* TRUTH.md is answer-free by construction (Stage 1), which is what makes it safe
  to hand to the judge: there is no golden value in it to grade against.

Usage
-----
    python judge/judge.py --run-dir <erza run dir> [--judges 3] [--out results/x.json]
    python judge/judge.py --run-dir <erza run dir> --offline
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "verifier"))
import trajectory as T  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

MODEL = "claude-opus-4-8"

SYSTEM = """\
You are grading the PROCESS an AI agent followed on a technical task, not the \
final numbers it produced. You are given the agent's full trajectory - its \
reasoning, the code it wrote, the commands it ran, and the tool output it saw - \
and a numbered rubric of criteria about that process.

For each criterion, decide whether it is satisfied by the trajectory.

Rules:
- Judge only what the trajectory shows. Absence of evidence is NOT satisfaction. \
If the agent plausibly did something but the trajectory does not show it, the \
criterion is not satisfied.
- SATISFIED always reflects the criterion text literally. A criterion marked \
GUARDRAIL describes a failure mode: SATISFIED: Yes means the failure mode \
ACTUALLY OCCURRED in this trajectory.
- Equivalent constructions count. If a criterion describes a procedure and the \
agent achieved the same thing by a different but genuinely equivalent route, it \
is satisfied. Say so in the rationale.
- Do not reward confident phrasing. An agent that asserts a scale-harmonisation \
convention without applying it has not applied it.
- One verdict per criterion, in the given order, no skipping.

Emit exactly this format, wrapped in <judgment></judgment>:

N. <verbatim criterion id>
[[RATIONALE: one or two sentences citing what in the trajectory decided it]]
[[SATISFIED: Yes|No]]
"""

USER_TEMPLATE = """\
<ground_truth>
{truth}
</ground_truth>

<agent_trajectory>
{transcript}
</agent_trajectory>

RUBRIC ({n} criteria - produce exactly {n} verdicts, in this order):
{rubric}

Now produce the <judgment>...</judgment> block with exactly {n} verdicts.
"""


def load_criteria() -> list[dict]:
    with open(os.path.join(ROOT, "rubrics.json")) as f:
        spec = json.load(f)
    return [c for c in spec["criteria"] if c["channel"] == "non_deterministic"]


def render_rubric(criteria: list[dict]) -> str:
    out = []
    for i, c in enumerate(criteria, 1):
        tag = "" if c["is_positive"] else " (GUARDRAIL)"
        out.append(f"{i}. {c['id']}{tag}\n   {c['criterion']}")
    return "\n".join(out)


VERDICT_RE = re.compile(
    r"^\s*(\d+)\.\s*(\S+)"
    r".*?\[\[RATIONALE:\s*(.*?)\]\]"
    r".*?\[\[SATISFIED:\s*(Yes|No)\s*\]\]",
    re.S | re.M | re.I,
)


def parse_verdicts(text: str, criteria: list[dict]) -> dict[str, dict]:
    body = text
    m = re.search(r"<judgment>(.*?)</judgment>", text, re.S | re.I)
    if m:
        body = m.group(1)
    got: dict[str, dict] = {}
    for match in VERDICT_RE.finditer(body):
        idx = int(match.group(1)) - 1
        if not (0 <= idx < len(criteria)):
            continue
        got[criteria[idx]["id"]] = {
            "satisfied": match.group(4).strip().lower() == "yes",
            "rationale": " ".join(match.group(3).split()),
        }
    return got


def ask_one(client, truth: str, transcript: str, criteria: list[dict], seed_hint: str,
            attempts: int = 6):
    import time

    import anthropic

    user = USER_TEMPLATE.format(
        truth=truth,
        transcript=transcript,
        rubric=render_rubric(criteria),
        n=len(criteria),
    )
    if seed_hint:
        user += f"\n\n{seed_hint}"

    # The grading instructions are prepended to the user turn rather than sent as
    # system=. The local Erza OAuth proxy injects its own system prompt and rejects
    # a caller-supplied one; inlining is portable and works against the real API too.
    user = SYSTEM + "\n\n---\n\n" + user

    last_err = None
    for attempt in range(attempts):
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=16000,
                thinking={"type": "adaptive"},
                output_config={"effort": "high"},
                messages=[{"role": "user", "content": user}],
            ) as stream:
                msg = stream.get_final_message()
        except (anthropic.RateLimitError, anthropic.APIStatusError,
                anthropic.APIConnectionError) as e:
            last_err = e
            delay = min(2 ** attempt, 30)
            print(f"    {type(e).__name__}; retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)
            continue
        if msg.stop_reason == "refusal":
            return "", {}
        text = "".join(b.text for b in msg.content if b.type == "text")
        return text, parse_verdicts(text, criteria)
    print(f"    giving up after {attempts} attempts: {last_err}", file=sys.stderr)
    return "", {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--judges", type=int, default=3)
    ap.add_argument("--offline", action="store_true",
                    help="skip the API; emit abstentions so scoring can be tested")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    criteria = load_criteria()
    traj = T.load(args.run_dir)
    with open(os.path.join(ROOT, "TRUTH.md")) as f:
        truth = f.read()

    per_judge: list[dict[str, dict]] = []
    raw: list[str] = []

    if not args.offline:
        import anthropic

        client = anthropic.Anthropic(max_retries=8, timeout=900.0)
        # perspective-diverse panel: same rubric, different reading stance, so the
        # judges fail differently rather than agreeing by construction
        stances = [
            "",
            "Read as a sceptic: your default is No. Only answer Yes where the "
            "trajectory contains explicit evidence you can quote.",
            "Read as a domain reviewer: give credit for equivalent constructions "
            "that reach the same harmonised distribution by different but valid arithmetic.",
        ]
        for i in range(args.judges):
            text, verdicts = ask_one(
                client, truth, traj.transcript, criteria, stances[i % len(stances)]
            )
            raw.append(text)
            per_judge.append(verdicts)
            print(f"  judge {i + 1}: {len(verdicts)}/{len(criteria)} verdicts parsed",
                  file=sys.stderr)

    results = []
    for c in criteria:
        votes = [j[c["id"]]["satisfied"] for j in per_judge if c["id"] in j]
        rationales = [j[c["id"]]["rationale"] for j in per_judge if c["id"] in j]
        if not votes:
            results.append({
                **{k: c[k] for k in ("id", "weight", "is_positive", "criterion")},
                "voted": False, "satisfied": None,
                "votes": [], "rationales": [],
                "resolution": "abstained",
            })
            continue
        yes = sum(votes)
        satisfied = yes * 2 > len(votes)
        results.append({
            **{k: c[k] for k in ("id", "weight", "is_positive", "criterion")},
            "voted": True,
            "satisfied": satisfied,
            "votes": votes,
            "rationales": rationales,
            "resolution": "unanimous" if yes in (0, len(votes)) else "majority",
        })

    out = {
        "run_dir": os.path.abspath(args.run_dir),
        "channel": "non_deterministic",
        "model": MODEL,
        "judges": 0 if args.offline else args.judges,
        "offline": args.offline,
        "criteria": results,
    }
    payload = json.dumps(out, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            f.write(payload + "\n")
        if raw:
            with open(args.out + ".raw.txt", "w") as f:
                f.write("\n\n===== JUDGE =====\n\n".join(raw))
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
