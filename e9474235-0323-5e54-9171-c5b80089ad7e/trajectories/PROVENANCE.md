# Provenance — e9474235 run records

State of this bundle's measurement evidence, recorded 2026-08-05. It separates what the records establish from what they do not. `trajectories/` sits outside this bundle's content seal, so nothing here affects any hash.

## What the records contain

| | |
|---|---|
| Model | claude-opus-4-8 |
| Arms | `no-skill` 3 runs, `with-skill` 3 runs |
| `task_digest` | one digest across both arms |
| Scores `no-skill` | 0.0833, 0.0833, 0.0833 |
| Scores `with-skill` | 1.0000, 1.0000, 1.0000 |

## Source tree: reconstructed, not recovered

All 6 runs record `Ethara-Ai/erza-harness` at `90a5d0a34f3f`, path `tasks/tidal-harmonic-prediction`, with `source.dirty: true` on 6 of 6.

That path **does not exist at that commit and was never committed at any point in that repository's history**. The tree was an uncommitted working directory. Its provenance is therefore not recoverable, and no `source` block was invented to suggest otherwise.

The *bytes* are reconstructed content-addressed at `harness/tasks-archive/e9474235-0323-5e54-9171-c5b80089ad7e/`, rebuilt from the sha256 values these records carry and re-verified against them: **38 of 38 files**. See its `MANIFEST.json`.
