# PROVENANCE — 6f76812f-83f9-5f56-9b63-38a56548fc24

**Task.** Ionospheric vertical TEC from dual-frequency GNSS code observables: apply the
per-satellite and per-receiver differential code biases before forming the ionospheric
observable, then map slant to vertical along each arc
(`ionosphere-arc-vtec-calibration`).

## Result

| arm | n | per-run reward | mean | pass@1 |
|---|---|---|---|---|
| no-skill | 5 | 0.0, 0.0, 0.0, 0.0, 0.0 | **0.000** | **0/5** |
| with-skill | 5 | 1.0, 1.0, 1.0, 1.0, 1.0 | **1.000** | **5/5** |

**Δ(pass@1) = +1.000** · Fisher exact two-sided **p = 0.0079** · **LABEL: POSITIVE**
Wilson 95%: no-skill (0.00, 0.43), with-skill (0.57, 1.00).

Model `claude-opus-4-8` via the local OAuth bridge; agent `claude-agent-acp`; sandbox
docker. Every timeout left at the task's declared value (`agent.timeout_sec` 3600, idle
watchdog 600) so neither arm could drift. The arms differ in `--skill-mode` /
`--skills-dir` and nothing else — asserted field-by-field across all ten `config.json`.

## Frozen bytes

- **`task_digest` recorded by all 10 runs:** `sha256:deff60c608232070c79fede890f904adc62ddf4fe26cf6b83224bf8428edf5b9` — one value across both arms (X-01), equal to `bench tasks digest` over the shipped bundle, so these runs are evidence for exactly these bytes.
- **Canonical content hash (cch):** `cff341113487298c0f073f2566cd0706cab719eab5b9f73e0b9392fe7a0cda9b`
- **task_id:** `6f76812f-83f9-5f56-9b63-38a56548fc24` = `uuid5(forge_ns, cch)` under `forge.task_id.v1`; manifest carries 63 files. Re-verified after packaging: the `dataset/` copy reproduces this id from its own bytes.
- Original bundle — supersedes nothing.

**Constants provenance.** The bias values derive from the CAS/IGG multi-GNSS DCB product
`CAS0MGXRAP_20221000000_01D_01D_DCB.BSX` (Bias-SINEX 1.00). Satellites and receivers are
carried in agent-visible data under opaque labels only (`SV-*`, `RX-*`), so the
site-specific bias table is not addressable from the observables alone.

## Egress gate

benchflow does **not** apply the declared `network_mode: no-network` block to LLM agent
arms: `sandbox/setup.py:652` flips `allow_internet` to true whenever
`preserve_agent_network` is set, and `rollout/__init__.py:557` ties that to
`BENCHFLOW_DISALLOW_WEB_TOOLS`, substituting agent-layer web-*tool* blocking that does
nothing about `curl` from the Terminal tool.

All ten runs were therefore executed with `harness/erza_harbor/egress/firewall.py` enabled
(`ERZA_EGRESS_FIREWALL=1`), which clamps egress after the agent bootstrap and before the
agent acts, and is fail-closed. **10/10 runs carry `egress/probe.txt`** reading:

```
inet=BLOCKED:URLError
gateway=OK:192.168.65.254
```

This is load-bearing, not ceremonial. On the same day the sibling task
`sensor-band-radiance-integration` scored **1.000** no-skill with egress open — the agent
downloaded a published reference workbook — and **0.000** blocked. An ungated no-skill arm
is not a baseline.

## Parity

- **Prompt byte-identical across all 10 runs** (`sha256:788eda669c06…`). The Skill arrives
  only by filesystem mount (`skill_source: task_bundled`, `skills_sandbox_dir: /skills`),
  never by prompt injection, and the prompt never names a skill.
- Arms balanced at n=5. Two no-skill trials were excluded as `provider_rate_limit`
  infrastructure failures — non-measurements, not zeros — and replaced by re-running only
  those trials, never the arm.

## Gates

- **Gate 1 (oracle).** Reward **1.0000** in docker with `NetworkMode=none`; the oracle arm
  is genuinely air-gapped, verified by `docker inspect`.
- **Kill gate.** One `no-skill` run alone scored 0.0000 with a well-formed wrong answer
  (12 scored assertions failed on value, not on a missing file). The base model does not
  solve this unaided.
- **Verifier recomputes** each reference from the shipped observables and bias tables
  rather than comparing against a stored key — the defect class that hid a wrong golden in
  `999a91d3` through authoring, a 10-run pilot, Gate 1 and publication.
- **Stage-4 negative fixtures** 18/18 pass, every detector seen to fire;
  `verifier/process/TRUTH.md` verified answer-free; every deterministic rubric criterion
  pairs with a `test_<id>`, so the deterministic channel cannot silently abstain.

## Limitations

- Δ is **not** a contamination-free measure: training-set membership of the CAS/IGG DCB
  product is unknown. Carry that caveat.
- n=5 per arm is the floor and the target; paired-bootstrap CIs are not implemented
  anywhere in the repo, so the Wilson intervals are per-arm, not paired.
- No control arm (length-matched irrelevant text / retrieval-only) was recorded, so this
  isolates *Skill vs no Skill*, not *procedure vs context*.
