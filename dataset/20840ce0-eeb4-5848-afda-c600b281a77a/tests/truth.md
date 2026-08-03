# truth.md — information-return-brecord-emission (grader-side)

Grader-side dossier. Goldens are permitted in this file. It is never mounted
into the agent's container: `environment/Dockerfile` copies `data/` and nothing
else, and `/verifier` is in the recorded `sandbox_locked_paths`.

## Delta-lever

Each payee's details must be written into the 750-position payee detail record
at the absolute character positions Publication 1220 fixes for Form 1099-MISC —
including the reserved runs at 271-286 and 408-447 that separate fields which
look adjacent, and the return-specific tail at 544-750 — rather than packed in
field order; the default places the opening correctly and slides everything past
the payment amounts.

Gap type **(b)**, a published positional map the model cannot reproduce past its
opening. Failure family **F7**, format and serialisation.

## What the agent is given, and what it is not

Given: the whole semantic record for each payee — name control, identification
number and its kind, account number, office code, correction status, payment
amounts by amount code, name lines, address, city, state, postal code, sequence
number, the notice and sales indicators, withholding, the programme code — plus
the identity and revision of the specification, the record's length, the return
type, and the output contract. A comma-delimited rendering of the same data is
supplied, plainly labelled as orientation.

Not given: the field map. It is not recoverable from the payee data either. The
data is roughly ten semantic values per payee and the withheld object is a
positional table of forty-nine rows; no quantity of payment detail identifies a
byte offset. **And there is no worked example record anywhere in the agent's
surface** — not in `task.md`, not in `environment/data/`, not in the skill. That
is the only channel through which a position could leak, because one correct
record lets the name block's start be counted straight off it. Its absence is
asserted on every graded run by
`test_outputs.py::test_no_assembled_record_reaches_the_agent`, which slides a
forty-character window over every golden record and requires no substantial run
to appear in any agent-visible file.

## Derivation

Every graded case is a count, not a value. For one payee and one field group,
the grader slices each field of that group out of the submitted record at that
field's own published positions, decodes it back to a semantic value according
to its field class, and compares that value with what the payee entry carries.
The graded quantity is **the number of fields in the group that come back out as
they went in**, so a group's reference is its own field count and the tolerance
admits no shortfall. For the single file-level case the quantity is the number
of well-formed records: one entry per payee reference and no others, each a
string of exactly 750 characters, printable, upper case where alphabetic, and
terminated by either two blanks or a carriage return and line feed.

Counted as conformance rather than as faults deliberately. A uniform reference
of zero collides with the zero-dollar amounts the payee data legitimately
carries — the leak scanners cannot tell a golden of `0.0` from an amount of
`0.00`, and reported thirty-one false leaks — and a reference that is a property
of the group cannot be reached by a submission that fails to parse at all.

Field classes and their decode rules, all from Publication 1220 Part C, Sec. 3:

```
alphanumeric     left justified, blank filled
payment amount   12 positions, right justified, zero filled, whole cents, unsigned
sequence number   8 positions, right justified, zero filled
postal code       9 positions; a five-digit code left justified, blank filled
reserved run     blanks
indicator        one position, a code from that field's own table, or a blank
account number   20 positions, left OR right justified, blank filled
terminator       two blanks, or a carriage return and line feed
```

The record is 750 positions: 1-543 common to every return type, 544-750
specific to Form 1099-MISC.

## Golden

Frozen in `expected_values.json`, which is authoritative wherever it and this
file disagree. The three golden records are stored there in full under
`golden_records`; they are not reproduced here, because this file is a
grader-side dossier and reproducing a record in a second place is a second thing
to keep in step.

Each field group's reference is that group's own field count, and it is the same
for all three payees. Tolerance 0.500 on every case.

| graded case (per payee) | positions | fields | reference |
|---|---|---|---|
| `head_1_54` | 1-54 | 9 | 9 |
| `amounts_55_270` | 55-270 | 18 | 18 |
| `reserved_and_first_name_271_327` | 271-327 | 3 | 3 |
| `second_name_and_address_328_407` | 328-407 | 2 | 2 |
| `reserved_and_city_408_487` | 408-487 | 2 | 2 |
| `state_and_postal_488_498` | 488-498 | 2 | 2 |
| `reserved_and_counter_499_543` | 499-543 | 3 | 3 |
| `indicators_and_reserved_544_662` | 544-662 | 5 | 5 |
| `free_text_and_state_withholding_663_734` | 663-734 | 2 | 2 |
| `local_withholding_and_program_code_735_750` | 735-750 | 3 | 3 |
| `answer_file_shape_and_charset` (once, not per payee) | whole file | 3 records | 3 |

30 field-group cases plus 1 file-level case: 31 in total. 31 is prime, so no
partial score lands on a round fraction. 8 of the 10 field groups begin past
position 247, and 480 of the record's 750 positions sit past it.

### Why the golden is trustworthy

Not by asking the oracle's code whether it agrees with itself. Three separate
things anchor it, and all three run on every graded run rather than only at
build time:

1. **A second formulation.** `verifier/brecord_layout.py` is an independent
   transcription of the same published table, written as absolute
   `(first, last)` position pairs with the published length beside them, where
   the oracle's table is a cursor over a list of lengths. It never renders a
   record. `test_frozen_golden_records_decode_to_the_payee_data` slices every
   frozen golden apart at that table's offsets and requires every field to
   decode back to the value the shipped payee entry carries.
2. **A standing tripwire on the transcription itself.**
   `test_field_table_is_contiguous_and_totals_750` asserts that every published
   length equals its own position range, that the ranges are contiguous and
   non-overlapping, and that they total exactly 750. A mistyped start needs a
   compensating mistyped length to survive the first assertion, and that
   compensation is caught by the second.
3. **A third transcription.**
   `verifier/process/verification/rederivation_test.py` carries the table a
   third time, as an ordered list of `(field, published length)` pairs with the
   start positions computed by accumulation, and asserts it reproduces the
   verifier's spans row for row. Three transcriptions that agree cannot all be
   the same typo.

The permitted-variant check is measured rather than asserted:
`test_permitted_readings_of_the_specification_do_not_false_fail` rebuilds each
golden with the issuer's account number right-justified and with the record
terminated by a carriage return and line feed — both readings the publication
explicitly allows — and requires every field to still decode.

## Plausibility envelope

Every graded value must sit inside these bounds, and the golden does. Asserted
in `test_plausibility_envelope_and_guess_resistance`.

| quantity | envelope | why |
|---|---|---|
| field-group conformance | 0 to the number of fields in that group, at most 18 | it is a count over the group's own fields |
| answer-file conformance | 0 to 3 | one per payee reference |
| record length | exactly 750 characters | the specification declares it and `question.json` states it |
| characters | printable ASCII, alphabetic characters upper case | Part C, Sec. 3: all alpha characters must be upper case |

The reference sits at the TOP of every envelope, which is what a byte-exact task
means: the target is not a measurement with spread, it is conformance. A
submission cannot land above it, and every recorded wrong route lands below it
by more than the tolerance.

## Wrong paths

Measured live from the shipped payee data, in tolerance units, by
`test_control_paths_are_measured_live_and_clear_the_tolerance`. The multiple is
the worst field group's fault count divided by the tolerance. Keys match
`expected_values.json#control_gaps` exactly.

| key | route | separation |
|---|---|---|
| `shifted_name_and_address_block` | opening and payment amounts correct, then the payee identification block packed straight on with no reserved run before the name lines and none before the city — **the nearest real competitor** | 6.00x, 24 of 31 cases failed |
| `comma_delimited_instead_of_fixed_width` | emit the delimited extract the payables system supplies, padded to length | 36.00x, 30 of 31 |
| `left_justified_amount_fields` | amounts as dollars-and-cents text, left justified and blank filled | 36.00x, 9 of 31 |
| `missing_form_specific_tail` | the block common to every return type, then blanks | 4.00x, 9 of 31 |
| `reserved_runs_zero_filled` | zero-fill every reserved run instead of blank-filling it | 4.00x, 18 of 31 |
| `nec_tail_instead_of_misc` | the neighbouring return type's tail table, which runs blanks where this one carries its chapter-4 indicator | 2.00x, 1 of 31 — **measured non-discriminating on two of the three payees** |

`nec_tail_instead_of_misc` is recorded rather than hidden. The two tails are
adjacent sections of the same publication and differ at exactly one position, so
on the two payees with no chapter-4 requirement the two tables agree position for
position and the route is a free pass. It separates only on the payee that does
carry the requirement, and there by a single field, which is why it sits at the
2x floor rather than above it. The alternative — dropping the entry — would make
the ledger look stronger than the task is.

One free pass was found by measurement and removed rather than documented away.
Under an earlier grouping the reserved runs at 271-286, 408-447 and 549-662 were
graded as cases of their own, and a submission of 750 blanks collected fourteen
of forty-one cases for nothing. Every reserved run is now carried in the same
graded group as a neighbouring field that holds content for every payee, and a
blank submission collects one case out of thirty-one: the answer-file shape
case, which exists so that a run able to commit to a well-formed answer is
scoreable at all (L-04). That single case is measured, not assumed:
`test_plausibility_envelope_and_guess_resistance` requires 750 blanks to reach
it and to reach nothing else, and requires the Z placeholder, 750 zeros and the
orientation extract to miss even that.

## Tolerance rationale

Reference: full conformance for the case — the group's own field count, or 3
well-formed records for the file-level case. Tolerance 0.500 fields, on every
case, which admits no shortfall.

**Lower bound: zero, measured.** The publication fixes one spelling for every
graded field except two, and both of those are graded by decoding rather than by
byte comparison: the issuer's account number may be justified either way, and
the last two positions may carry blanks or a carriage return and line feed. Both
readings were rebuilt and re-graded and neither loses a field, so the spread
between two faithful readings of the specification is 0.000 and is recorded as
`published_precision_ambiguity_mismatches_maxabs`.

**Upper bound: 2.00 tolerances.** That is `nec_tail_instead_of_misc`, the
one-position route described above and disclosed as thin. The nearest real
competitor, `shifted_name_and_address_block`, sits at 6.00x, and the delimited
route at 36.00x.

The tolerance is a positive band rather than an equality test so that the ledger
arithmetic V-04 performs has something to divide by; it admits no fault, which
is the right reading of a conformance task.

## Citations

- Internal Revenue Service, **Publication 1220**, *Specifications for Electronic
  Filing of Forms 1097, 1098, 1099, 3921, 3922, 5498, and W-2G*, Tax Year 2025
  revision, `https://www.irs.gov/pub/irs-pdf/p1220.pdf` (retrieved 2026-07-29,
  1,735,511 bytes, HTTP 200). Source of every field position, length,
  justification rule and indicator code in this bundle: Part C, Sec. 3 for
  positions 1-543; Part C, Sec. 3 (18) for the Form 1099-MISC tail at 544-750;
  Part C, Sec. 3 (19) for the Form 1099-NEC tail quoted in the skill for
  contrast; Part A, Sec. 12, Table 1 for the participating-state programme
  codes; Part B, Sec. 2 for the amount-code assignments per return type.
- Rights, verbatim from the publisher: *"Content on this website that was
  created or maintained by federal employees in the course of their duties is
  not subject to copyright and may be freely copied. Credit is requested."*
  (`https://www.irs.gov/privacy-disclosure/irs-web-site-privacy-and-security-notice`).
  No non-commercial restriction and no contractor operator. The Internal Revenue
  Service is credited in the skill and in `build/build_report.json`.
- Payee data: synthetic, authored for this bundle, recorded in
  `build/build_report.json#anonymisation`. No real taxpayer identification
  number, name or address is used.

## Scoring

One case per field group per record plus one answer-file case, 31 total, read
from the JUnit XML and filtered to the `test_graded_case` prefix. `test.sh`
**gates**: if any grader self-check fails or is skipped, the run scores 0 rather
than being graded by a verifier that has failed its own audit. Grading is by
decoded field value at every case, never by substring: a submission carrying a
literal that happens to look like a pass is scored on what its fields decode to.
