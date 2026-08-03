# TRUTH.md — payee detail record emission (golden trajectory)

The ordered moves a competent run makes, from opening the task to writing the
answer. Each step says **what to do and why**; **no step states what it
evaluates to**. Derived from `oracle/solve.py` with every produced value
stripped out: no record, no field position and no golden appears anywhere in
this file.

**Method is kept; the map is stripped.** What is below is complete as method —
the discipline a positional transmission format imposes, the field classes and
their justification and fill rules, the self-consistency check a published
position table must survive before it is used, the order the operations run in,
and the read-back that catches the error a forward emitter cannot see. What is
deliberately **not** printed is the position range of any field of the record
this instance grades. That table is the withheld lever the task exists to
measure, and this file is handed to an LLM judge; printing it would make it a
second answer key, which `PROMPT-AUTHOR-TO-30.md` §6.11 forbids. The one
structural figure that does appear here — the record's total length — is stated
in the agent's own inputs, so it leaks nothing.

**No worked example record appears here either**, for the same reason it appears
nowhere in the agent's surface: one correct record lets a reader count the name
block's start position straight off it.

---

## What is being asked

Three payees, one payee detail record each, for a single information return type
and payment year. Each record is one line of exactly the length the inputs
declare, carrying that payee's name control, taxpayer identification number and
its kind, issuer account number and office code, correction status, payment
amounts by amount code, name lines, mailing address, city, state, postal code,
sequence number, notice and sales indicators, withholding and programme code,
each at the character positions the governing specification fixes. One answer
file, keyed by payee reference.

The specification's identity and revision, the record's length, the return type,
the payee references and the output contract all come from
`/root/data/question.json`; the payee details come from `/root/data/payees.json`.
Both are supplied.

## Delta-lever

Each payee's details must be written at the absolute character positions the
governing specification fixes for this return type — including the reserved runs
that sit between fields which look adjacent, and the return-specific block that
governs the end of the record — rather than packed on in field order; the
default route places the opening correctly and slides everything after the
payment amount block.

Everything else in this task — reading JSON, padding a string, converting
dollars to whole cents — is work a competent run does correctly without help.
The lever is entirely in *where each field goes*.

## The crux

**The crux is Step 5: every field is written at its own published position
range, and the reserved runs between fields are reserved rather than skipped.**

It has three failure surfaces, and all three are separately fatal:

1. **Packing.** The fields are concatenated in the order the table lists them,
   with the reserved runs omitted. This produces a line of the right length once
   it is padded, with the opening correct, and it misplaces every field after
   the first omitted run.
2. **Delimiting.** The fields are joined with separators. The orientation block
   in `question.json` shows the payee details in exactly that shape, so this is
   the route a run under time pressure copies.
3. **Stopping early.** The part of the table that is widely reproduced is
   emitted and the remainder of the line is filled to length. This is the most
   honest of the three failures and the easiest to mistake for success, because
   what it produces is well-formed.

The distance from "placed at the published positions" to each of these is
measured, per route, in `../expected_values.json` under `control_gaps`.

## Step 0 — Read the inputs

Open `/root/data/question.json` and `/root/data/payees.json`. The first names
the specification, its revision, the record name, the record's exact character
length, the return type, the payee references to emit and the output contract;
it also carries an orientation block holding the same payee details
comma-delimited, which is labelled as such. The second carries one entry per
payee.

Read the orientation block for what it is. It is the payables system's own
export, not a transmission record, and its shape is one of the measured wrong
routes.

## Step 1 — Fix which specification, revision and return type govern

The inputs name a publisher, a document, a title and a revision, and separately
a return type. All four matter. A positional specification is revised, and a
revision's layout is not interchangeable with another's; the return type
selects which of the specification's per-form tables governs the end of the
record.

A frequent claim about this family of specifications is that the fixed-length
transmission format has been retired in favour of a tagged one. Whatever is true
of neighbouring channels, the inputs name a revision and state that it is the
one in force for this payment year, so the question is settled by the inputs and
not by any belief about the format's status. A run that declines on those
grounds has answered a different question than the one asked.

## Step 2 — Retrieve the field table for this record and this return type

The specification publishes the record as a table, one row per field, each row
carrying a field name, a position range, a length and a description of what the
field holds. Part of the table is common to every return type in the
specification and part is selected by the return type being reported. Retrieve
both parts. There is no deriving one from the other, and no deriving either from
the payee data: the data says what to write, never where.

## Step 3 — Check the table against itself before using it

A position table carries redundant information — a range and a length — and that
redundancy is the only defence against a transcription error, so use it:

    for every row:   last - first + 1 == length
    across rows:     each row begins one position after the previous row ends
    over the whole:  the lengths sum to the declared record length

A mistyped start fails the first; a mistyped start with a compensating mistyped
length fails the second. A table that passes all three is internally consistent,
which is not the same as correct but is the strongest statement available
without a second source.

## Step 4 — Render each field to its full length, by field class

Every field occupies its whole range whether or not the payee has a value for
it. Justification and fill are set by the field's class, and the classes are not
interchangeable:

    alphanumeric     left justified, blank filled
    payment amount   right justified, zero filled, whole cents, no sign,
                     no comma, no decimal point
    count or sequence  right justified, zero filled
    postal code      left justified, blank filled; a short code occupies the
                     leading positions of its field and the rest is blank
    reserved         blanks, unless the row says zeros - the two instructions
                     are different and appear in different rows
    indicator        one position carrying a code from that field's own table,
                     or a blank

Two consequences that are easy to get wrong and cheap to get right. Unused
payment amount fields are zero-filled, not blank — the specification requires
every amount field to be present on every record. And alphabetic characters are
upper case throughout the record.

Indicator codes come from each field's own table and are not uniform: at least
one indicator in the return-specific block is signalled by a character other
than the one every neighbouring indicator uses. Read each row's own table
rather than generalising from the row above it.

## Step 5 — Place every field at its own published range  *(crux)*

Write the fields into the record at the ranges the table gives, not in the order
they happen to be listed with the gaps closed. The reserved runs are part of the
layout; they exist so that the fields around them do not touch, and closing one
moves every field after it.

Two spellings both work and neither is safer than the other by itself: build a
buffer of the declared length and write each field in at its own offset, or
concatenate the fields in order *including* the reserved runs. What matters is
that the reserved runs are emitted and that the total is asserted afterwards.

The receiving system does not parse the line. It slices it at offsets it holds
internally, so a field one position from where the specification puts it is not
received as a damaged field — it is received as a different field, and so is
everything after it.

## Step 6 — Emit the tail belonging to the return type being reported

The end of the record is governed by a per-form table. Neighbouring return types
have tails that agree at most positions and differ at a few, so a tail borrowed
from the wrong form produces a record that is right almost everywhere and wrong
where it counts. Select the table by the return type the inputs name.

## Step 7 — Read the record back, then write the contract

Before writing the answer, slice each finished line apart at the same positions
and read the fields back out. The name control, the identification number, the
name lines, the city, the postal code and the amounts must come back out as what
went in.

This is not ceremony. A forward emitter produces a well-formed line whether or
not its offsets are right, so nothing about the output looks wrong; a read-back
is the only check that can disagree. Assert the length as well, and assert that
no alphabetic character is lower case.

Then write `/root/results.json` with the single contracted top-level object
mapping each payee reference from `question.json` to that payee's line. The
reference label and the value shown in the prompt are a shape illustration;
copying either through is not an answer.

## Where runs break

Each route below is recomputed live in `../expected_values.json:control_gaps`
and recorded there with its distance from the reference in tolerance units.

- **The payee block packed on with the reserved runs closed** — the opening and
  the amounts land, everything after slides. This is the producible route for a
  run that does not hold the field table, and it is the nearest real competitor.
- **A delimited rendering** — the orientation block copied through, or the
  fields joined with separators and padded to length.
- **Amounts written as dollars-and-cents text, left justified** — the fixed-width
  default applied to the one class that inverts it.
- **The return-specific tail left blank** — the common part of the table emitted
  and the per-form part never placed.
- **Reserved runs zero-filled** — the usual fixed-width habit, against a
  specification that distinguishes blanks from zeros row by row.
- **The neighbouring return type's tail** — right almost everywhere. Measured
  non-discriminating on the payees that do not carry the indicator the two tails
  disagree about; see the caution recorded with that control.
- **A record of the wrong length** — every field case fails at once, and so does
  the answer-file case.

## What cannot be done

The field table is not recoverable from the payee data. The data is a handful of
semantic values per payee and the table is a positional map of some fifty rows;
no quantity of payment detail identifies a character offset, and there is no
example record anywhere in the inputs from which one could be counted off. A run
that claims to have derived the positions from the supplied files has not.

Equally, a plausible-looking line is not evidence. Every wrong route on this
task returns a well-formed line of the right length made of the right
characters, so nothing about the output's appearance separates a correctly
placed record from a confidently misplaced one. Judge on the read-back, not on
the shape.

## Sources

- **The record layout, the field classes, the indicator codes and the per-form
  tails** — Internal Revenue Service, Publication 1220, *Specifications for
  Electronic Filing of Forms 1097, 1098, 1099, 3921, 3922, 5498, and W-2G*, Tax
  Year 2025 revision, `https://www.irs.gov/pub/irs-pdf/p1220.pdf`, Part C,
  Sec. 3 and its per-form subsections, with the participating-state programme
  codes in Part A, Sec. 12, Table 1 and the amount-code assignments in Part B,
  Sec. 2. Rights are recorded in `../../build/build_report.json:licence`: content
  created by federal employees in the course of their duties is not subject to
  copyright and may be freely copied, with credit requested.
- **The specification's identity and revision, the record length, the return
  type, the payee references and the output contract** —
  `../../environment/data/question.json`, mirrored in
  `../expected_values.json`.
- **The self-consistency check of Step 3 and the read-back of Step 7** —
  `../brecord_layout.py` (`check_spans`, `field_faults`), the verifier's second
  formulation, which never renders a record.
- **The per-route separations quoted under "Where runs break"** —
  `../expected_values.json:control_gaps`, each recomputed on every graded run.
