# PROVENANCE — c59f8b2a-0606-5f02-bed5-52937e5ab468

**Task.** Receiver-antenna phase-centre correction from IGS20 ANTEX — the antenna's mean
phase-centre offset projected onto the line of sight in the local North/East/Up frame, plus
the phase-centre variation interpolated bilinearly on that antenna's azimuth × zenith-angle
grid at the same frequency (`antenna-phase-centre-correction`).

## Result

| arm | n | per-run reward | mean | pass@1 |
|---|---|---|---|---|
| no-skill | 5 | 0.0, 0.0, 0.0, 0.0, 0.0 | **0.000** | **0/5** |
| with-skill | 5 | 1.0, 1.0, 1.0, 1.0, 1.0 | **1.000** | **5/5** |

**Δ(pass@1) = +1.000** · Fisher exact two-sided **p = 0.0079** · **LABEL: POSITIVE**
Wilson 95%: no-skill (0.00, 0.43), with-skill (0.57, 1.00).

Model `claude-opus-4-8` via the local OAuth bridge; agent `claude-agent-acp`; sandbox
docker. Every timeout was left at the task's declared value (`agent.timeout_sec` 3600,
idle watchdog 600) so neither arm could drift. The arms differ in `--skill-mode` /
`--skills-dir` and nothing else — asserted, not assumed: every `config.json` field outside
the six skill fields is identical across all ten runs.

## Frozen bytes

- **`task_digest` recorded by all 10 runs:** `sha256:e91ff8a3f1c611214e235b48c1b35a5070826b3cb7794b193f7e06483be79e54` — a single value across both arms (X-01), and equal to `bench tasks digest` over the shipped bundle, so these runs are evidence for exactly these bytes.
- **Canonical content hash (cch):** `15de7995c587abdd9ea1c2fd07851becc8f341a1d5cb5822aff01ca06d17b9b8`
- **task_id:** `c59f8b2a-0606-5f02-bed5-52937e5ab468` = `uuid5(forge_ns, cch)` under `forge.task_id.v1`; manifest carries 43 files. Re-verified after packaging: the copy in `dataset/` reproduces this id from its own bytes.
- Supersedes `92a6df11-cc8f-5452-b466-41852261f357`.

## Egress gate — why this matters for this pilot

Every task declares `network_mode: no-network`, but benchflow does **not** apply the
container network block to LLM agent arms: `sandbox/setup.py:652` flips `allow_internet`
to true whenever `preserve_agent_network` is set, and `rollout/__init__.py:557` ties that
to `BENCHFLOW_DISALLOW_WEB_TOOLS`, substituting agent-layer web-*tool* blocking that does
nothing about `curl` from the Terminal tool.

All ten runs above were therefore executed with
`harness/erza_harbor/egress/firewall.py` enabled (`ERZA_EGRESS_FIREWALL=1`), which clamps
egress after the agent bootstrap and before the agent acts, and is fail-closed. Each run
carries its own `egress/probe.txt`:

```
inet=BLOCKED:URLError
gateway=OK:192.168.65.254
```

**10/10 runs carry that proof.** This is load-bearing rather than ceremonial: on the same
day, the sibling task `sensor-band-radiance-integration` scored **1.000** no-skill with
egress open — the agent downloaded ESA's published response-function workbook — and
**0.000** with egress blocked. An ungated no-skill arm is not a baseline.

## Parity

- **Prompt byte-identical across all 10 runs** (`sha256:1839a23a9e74…`). The Skill arrives
  only by filesystem mount (`skill_source: task_bundled`, `skills_sandbox_dir: /skills`),
  never by prompt injection, and the prompt never names a skill.
- **Arms balanced at n=5.** The no-skill arm produced a sixth healthy trial when a
  long-running earlier run landed alongside its replacement; the surplus was dropped by
  **trial order, never by reward** (all six were 0.0000, so no selection was possible).
  Excluded separately: `with-skill run_2`, which produced no `results.json` — a
  non-measurement, not a zero, since `test.sh` seeds `reward.txt` to 0.0000 before pytest.

## Gates

- **Gate 1 (oracle).** Reward **1.0000** in docker with `NetworkMode=none` — the oracle arm
  is genuinely air-gapped, verified by `docker inspect`.
- **Kill gate.** One `no-skill` run alone, scored 0.0000 with a well-formed wrong answer
  (all 12 scored assertions failed on value, not on a missing file). The base model does
  not solve this unaided, so the task is above the bar.
- **Verifier recomputes.** `verifier/test_outputs.py` derives each reference from the
  shipped ANTEX record rather than comparing against a stored key — the defect class that
  hid a wrong golden in `999a91d3` through authoring, a 10-run pilot, Gate 1 and
  publication.
- **Stage-4 negative fixtures** all seen to fire; `verifier/process/TRUTH.md` verified
  answer-free against the golden ledger; every deterministic rubric criterion pairs with a
  `test_<id>` (no silent abstention).

## Limitations

- Δ is **not** a contamination-free measure: training-set membership of IGS20 ANTEX is
  unknown. Carry that caveat.
- n=5 per arm is the floor and the target; a paired-bootstrap CI is not implemented
  anywhere in the repo yet, so the Wilson intervals above are per-arm, not paired.
- No control arm (length-matched irrelevant text / retrieval-only) was recorded, so this
  isolates *Skill vs no Skill*, not *procedure vs context*.
