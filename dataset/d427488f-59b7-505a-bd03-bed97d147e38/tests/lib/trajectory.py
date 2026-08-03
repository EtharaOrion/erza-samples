"""Load an Erza run directory into a normalised trajectory object.

An Erza run directory (`trajectories/<task>/<model>/<arm>/run_N/`) holds
`trajectory/llm_trajectory.jsonl`: one JSON object per API call, each carrying
the *entire* message history sent on that call plus the response. The last line
therefore already contains the full conversation; the final assistant turn lives
in that line's response body.

This module turns that into the views both verifier channels read:

  * `turns`       - ordered [{role, type, text}] over the whole conversation
  * `commands`    - every shell command the agent actually issued
  * `file_writes` - (path, content) for every file the agent wrote
  * `agent_code`  - all source the agent authored (writes + heredoc'd commands)
  * `agent_prose` - everything the agent said or thought, minus tool plumbing
  * `transcript`  - a flat readable rendering, for the LLM judge

Nothing here interprets the task. Task-specific claims live in `rubrics.json`
and are checked by `test_trajectory.py` (deterministic) or the judge
(non-deterministic).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


def _text_of(block: dict) -> str:
    """Best-effort text for one content block, whatever shape it arrived in."""
    t = block.get("type")
    if t == "text":
        return block.get("text", "")
    if t == "tool_use":
        return json.dumps(block.get("input", {}), ensure_ascii=False)
    if t == "tool_result":
        content = block.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        return ""
    if t == "thinking":
        return block.get("thinking", "") or ""
    return ""


@dataclass
class Turn:
    role: str
    type: str
    text: str
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)


@dataclass
class Trajectory:
    run_dir: str
    turns: list[Turn]
    reward: float | None
    pass_at_1: int | None

    # ---------------- derived views ----------------

    @property
    def commands(self) -> list[str]:
        """Every shell command string the agent issued, in order."""
        out = []
        for t in self.turns:
            if t.type != "tool_use":
                continue
            inp = t.tool_input
            for key in ("command", "cmd", "script"):
                v = inp.get(key)
                if isinstance(v, str):
                    out.append(v)
        return out

    @property
    def file_writes(self) -> list[tuple[str, str]]:
        """(path, content) for every file the agent wrote via a write/edit tool."""
        out = []
        for t in self.turns:
            if t.type != "tool_use":
                continue
            inp = t.tool_input
            path = inp.get("file_path") or inp.get("path") or ""
            content = (
                inp.get("content")
                or inp.get("file_text")
                or inp.get("new_string")
                or ""
            )
            if path and content:
                out.append((str(path), str(content)))
        return out

    @property
    def agent_code(self) -> str:
        """All source the agent authored: file writes plus heredoc'd commands.

        This is what the deterministic channel greps. It is deliberately a
        superset - a convention that appears in a discarded draft still counts
        as the agent having considered it.
        """
        parts = [c for _p, c in self.file_writes]
        parts += self.commands
        return "\n\n".join(parts)

    @property
    def tool_results(self) -> list[str]:
        """Every tool_result body the run saw, in order.

        These are bytes the run's own container produced - the `cat
        /root/results.json` it echoed back, a solver's stdout - not verifier
        artifacts. The answer-shaped guardrails read this as the last route to
        the answer the run actually emitted, so the check stays independent of
        run-directory layout and of the recorded reward.
        """
        return [t.text for t in self.turns if t.type == "tool_result"]

    @property
    def agent_prose(self) -> str:
        """Everything the agent said or thought, excluding tool plumbing."""
        return "\n\n".join(
            t.text for t in self.turns
            if t.role == "assistant" and t.type in ("text", "thinking")
        )

    @property
    def transcript(self) -> str:
        """Flat readable rendering for the judge."""
        lines = []
        for i, t in enumerate(self.turns):
            head = f"--- [{i}] {t.role}/{t.type}"
            if t.tool_name:
                head += f" ({t.tool_name})"
            lines.append(head + " ---")
            lines.append(t.text)
        return "\n".join(lines)


def _read_reward(run_dir: str, name: str):
    p = os.path.join(run_dir, "verifier", name)
    try:
        with open(p) as f:
            return f.read().strip()
    except OSError:
        return None


def load(run_dir: str) -> Trajectory:
    path = os.path.join(run_dir, "trajectory", "llm_trajectory.jsonl")
    with open(path) as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    if not lines:
        raise ValueError(f"empty trajectory: {path}")

    last = json.loads(lines[-1])
    messages = last["request"]["body"]["messages"]

    turns: list[Turn] = []
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content")
        if isinstance(content, str):
            turns.append(Turn(role, "text", content))
            continue
        for block in content or []:
            if not isinstance(block, dict):
                continue
            turns.append(
                Turn(
                    role=role,
                    type=block.get("type", "?"),
                    text=_text_of(block),
                    tool_name=block.get("name", ""),
                    tool_input=block.get("input", {}) or {},
                )
            )

    # final assistant turn: it is the response of the last recorded call, and so
    # never appears in any request's message list
    body = last.get("response", {}).get("body", {}) or {}
    final = ""
    for choice in body.get("choices", []) or []:
        c = (choice.get("message") or {}).get("content")
        if isinstance(c, str):
            final += c
    if not final:  # native anthropic response shape
        for block in body.get("content", []) or []:
            if isinstance(block, dict):
                final += _text_of(block)
    if final:
        turns.append(Turn("assistant", "text", final))

    reward = _read_reward(run_dir, "reward.txt")
    if reward is None:
        # a handful of recorded runs carry the score under a different name
        # (verifier/score.md, e.g. "1.0000"); without this fallback those runs
        # have reward None and silently drop out of every reward-keyed check
        reward = _read_reward(run_dir, "score.md")
    p1 = _read_reward(run_dir, "pass_at_1.txt")
    return Trajectory(
        run_dir=run_dir,
        turns=turns,
        reward=float(reward) if reward else None,
        pass_at_1=int(p1) if p1 else None,
    )
