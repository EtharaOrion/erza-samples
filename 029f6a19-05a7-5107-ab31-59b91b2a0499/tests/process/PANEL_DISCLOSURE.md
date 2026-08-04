# Panel disclosure — judged channel

Recorded per REQUIREMENTS.md section 9: *"self-judging seats and single-vendor
limitations disclosed beside any judged score"*. It describes the panel behind the
`S_N` figures in this bundle's `trajectories/**/verifier/process/score.json`.

## Seats

| Model | Stance |
| :---- | :----- |
| `gpt-5.6-sol` | single |

Panel size 1 (odd). Graded runs are `claude-opus-4-8`. 6 judged runs, 4 judged criteria, 24 verdicts, 0 abstentions.

## Limitations, stated because the score cannot carry them

- **No self-judging seat.** The graded runs are `claude-opus-4-8` and no seat
  shares that family, so the self-leniency section 9 warns about does not apply
  to these scores. This is the one limitation the panel does *not* have.
- **Single vendor.** Every seat is a `gpt` model, so the panel shares
  that vendor's blind spots and cannot detect an error the vendor's models make in
  common. Section 9 prefers a cross-vendor panel.
- **Panel of one — no vote aggregation.** With a single seat there is no majority:
  the seat's verdict *is* the verdict. A panel exists so one anomalous read can be
  outvoted, and that margin does not exist here — judge noise passes into `S_N`
  undamped.
- **No stance diversity.** One seat means no sceptic/advocate contrast, so this
  panel produces no intra-panel disagreement signal at all. Nothing here measures
  how much of a verdict is the criterion and how much is the reader.
- **One panel per run.** `S_N` is a single draw. Repeat panels on this instrument have
  moved a channel score by roughly 5 points and have returned contradictory unanimous
  verdicts on the same trajectory. Two runs whose `S_N` differ by less than that are
  not distinguishable, and no repeat-panel stability measurement is shipped here.

`score.py` emits an equivalent `panel_disclosure` block on every score it writes,
computed from that run's own votes; this file is the standing summary across runs.
