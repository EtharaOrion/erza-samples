---
name: fixed-width-filing-record-emission
description: >-
  Turn structured payee or account data into a byte-exact, fixed-length
  transmission record for a regulator that publishes its own positional layout -
  US information returns transmitted through the IRS FIRE channel under
  Publication 1220, and formats built the same way. Covers the general
  discipline (position ranges are absolute and one-based, every field is padded
  to its declared length, justification and fill differ by field class), the
  layout of the 750-position payee detail record, and the return-specific tail
  tables for Forms 1099-MISC and 1099-NEC. Do NOT use when the receiving system
  takes a delimited or tagged format such as CSV, XML or JSON - the IRIS and
  AIR channels take XML and none of this applies to them - when the regulator
  supplies a library, schema or validator that assembles the record for you,
  when the task is to READ an existing transmission file rather than produce
  one, or when the record you need belongs to a specification this file does not
  tabulate: guessing a position range is worse than declining, because the
  receiving system rejects the whole transmission rather than the field.
---

# Emitting a byte-exact fixed-length regulatory record

Source for every position, length and indicator code below: Internal Revenue
Service, **Publication 1220**, *Specifications for Electronic Filing of Forms
1097, 1098, 1099, 3921, 3922, 5498, and W-2G*, Tax Year 2025 revision,
`https://www.irs.gov/pub/irs-pdf/p1220.pdf` - Part C, Sec. 3 for the block
common to every return type and Part C, Sec. 3 (18) and (19) for the
return-specific tails reproduced here. Publication 1220 is a US Government work
prepared by federal employees in the course of their duties, is not subject to
copyright, and may be freely copied; credit is requested, and is given here.

## Why this is not ordinary string formatting

A delimited file survives a wrong field order: the reader keys on the separator
or the header. A fixed-length file has neither. The receiving system slices the
record at absolute offsets it holds internally, so a field placed one position
early does not arrive mangled - it arrives as a *different field*, and every
field after it does too. There is no partial acceptance: a record whose payee
name begins at the wrong position is a transmission the regulator rejects.

That is why the layout table, not the data, is the hard part, and why it must be
transcribed rather than inferred. The opening fields of a specification like this
are widely reproduced and easy to remember; the interior of the record - the
reserved runs, the second name line, the block that begins after the payment
amounts - is where working implementations diverge and where an emitter that was
written from memory silently drifts.

## The discipline

1. **Positions are absolute, inclusive and one-based.** A field printed as
   `288-327` occupies positions 288 through 327 and is 40 positions long. Never
   derive one field's start by adding a guessed gap to the previous field's end;
   the tables carry reserved runs precisely so that the ends do not touch.

2. **Check the table against itself before using it.** Every row carries both a
   position range and a length. Assert `last - first + 1 == length` for every
   row, assert the rows are contiguous and non-overlapping, and assert the total
   equals the record length the specification declares. A mistyped digit fails
   one of the three; a mistyped digit that passes all three is not possible
   without a second, compensating error.

3. **Every field is padded to its full length.** Emit the record as a sequence
   of exactly-sized fields concatenated in order, or as a buffer of the declared
   length written into by absolute offset. Both work; assembling by
   concatenation and trusting the total is the failure mode, so assert the total
   afterwards either way.

4. **Justification and fill differ by field class, and the classes are not
   interchangeable.**

   | class | justification | fill | notes |
   |---|---|---|---|
   | alphanumeric | left | blanks | names, addresses, city, state, name control, office code |
   | payment amount | right | zeros | no sign, no comma, no decimal point |
   | count or sequence | right | zeros | record sequence numbers |
   | postal code | left | blanks | a five-digit code occupies the first five positions of a nine-position field |
   | reserved | n/a | blanks | "enter blanks" and "enter zeros" are different instructions; read which one the row gives |
   | indicator | n/a | n/a | a single position carrying a code from that field's own table, or a blank |

5. **Money carries no punctuation and no decimal point.** A payment amount field
   holds the amount in whole cents, right-justified and zero-filled to the
   field's length: the rightmost two positions are the cents. Unused amount
   fields are filled with zeros, not blanks - the specification requires every
   amount field to be present on every record.

6. **Alphabetic characters are upper case throughout the record.** The name
   lines admit a hyphen and an ampersand as their only special characters;
   titles, periods and apostrophes are removed before the name is placed.

7. **Emit the return-specific tail for the form you are actually filing.** The
   block common to every return type ends partway through the record and a
   per-form table governs the remainder. Neighbouring forms' tails are similar
   enough to look interchangeable and are not.

## The payee detail record

Record type `B`, 750 positions, one per payee per form. Positions 1 through 543
are the same for every return type in the publication; 544 through 750 are
return-specific.

### Positions 1-543, common to every return type

| positions | length | field | class and content |
|---|---|---|---|
| 1 | 1 | Record Type | the letter `B` |
| 2-5 | 4 | Payment Year | four digits, the year being reported |
| 6 | 1 | Corrected Return Indicator | `G` for a one-transaction correction or the first of a two-transaction correction, `C` for the second transaction of a two-transaction correction, blank for an original return |
| 7-10 | 4 | Name Control | first four characters of the surname of the person whose taxpayer identification number is reported, left justified, blank filled |
| 11 | 1 | Type of TIN | `1` for an employer identification number, `2` for a social security, individual taxpayer or adoption taxpayer identification number, blank if not determinable |
| 12-20 | 9 | Payee's TIN | nine digits, no hyphens, no alphabetic characters |
| 21-40 | 20 | Issuer's Account Number for Payee | may be left or right justified, blank filled |
| 41-44 | 4 | Issuer's Office Code | blanks if none |
| 45-54 | 10 | Blank | |
| 55-66 | 12 | Payment Amount 1 | |
| 67-78 | 12 | Payment Amount 2 | |
| 79-90 | 12 | Payment Amount 3 | |
| 91-102 | 12 | Payment Amount 4 | |
| 103-114 | 12 | Payment Amount 5 | |
| 115-126 | 12 | Payment Amount 6 | |
| 127-138 | 12 | Payment Amount 7 | |
| 139-150 | 12 | Payment Amount 8 | |
| 151-162 | 12 | Payment Amount 9 | |
| 163-174 | 12 | Payment Amount A | |
| 175-186 | 12 | Payment Amount B | |
| 187-198 | 12 | Payment Amount C | |
| 199-210 | 12 | Payment Amount D | |
| 211-222 | 12 | Payment Amount E | |
| 223-234 | 12 | Payment Amount F | |
| 235-246 | 12 | Payment Amount G | |
| 247-258 | 12 | Payment Amount H | |
| 259-270 | 12 | Payment Amount J | |
| 271-286 | 16 | Blank | |
| 287 | 1 | Foreign Country Indicator | `1` when the payee's address is in a foreign country, otherwise blank |
| 288-327 | 40 | First Payee Name Line | left justified, blank filled |
| 328-367 | 40 | Second Payee Name Line | additional payees, or the continuation of a name too long for the first line; no address information; left justified, blank filled |
| 368-407 | 40 | Payee Mailing Address | left justified, blank filled; nothing but the mailing address |
| 408-447 | 40 | Blank | |
| 448-487 | 40 | Payee City | city, town or post office only; no state, no postal code |
| 488-489 | 2 | Payee State | the two-letter postal abbreviation |
| 490-498 | 9 | Payee ZIP Code | nine or five digits; a five-digit code is left justified and the rest blank filled |
| 499 | 1 | Blank | |
| 500-507 | 8 | Record Sequence Number | the record's ordinal position in the transmission file, right justified with leading zeros |
| 508-543 | 36 | Blank | |

The eighteen payment amount fields are addressed by the amount **codes** `1`
through `9` and then `A` through `H` and `J` - there is no code `I`. Each form
declares which codes it uses; the codes it does not use still occupy their
positions, zero-filled.

### Positions 544-750 for Form 1099-MISC

| positions | length | field | class and content |
|---|---|---|---|
| 544 | 1 | Second TIN Notice | `2` when the IRS has given notice twice within three calendar years of an incorrect name and TIN combination, otherwise blank |
| 545-546 | 2 | Blank | |
| 547 | 1 | Direct Sales Indicator | `1` for consumer-product sales of five thousand dollars or more on a buy-sell, deposit-commission or other commission basis for resale away from a permanent retail establishment, otherwise blank |
| 548 | 1 | FATCA Filing Requirement Indicator | `1` when there is a filing requirement under chapter 4, otherwise blank |
| 549-662 | 114 | Blank | |
| 663-722 | 60 | Special Data Entries | the filer's own use, or state and local reporting; blanks when unused |
| 723-734 | 12 | State Income Tax Withheld | payment-amount class |
| 735-746 | 12 | Local Income Tax Withheld | payment-amount class |
| 747-748 | 2 | Combined Federal/State Code | the participating state's two-digit programme code, blanks for issuers or states not in the programme; this is a programme code, not the postal abbreviation |
| 749-750 | 2 | Blank | blanks, or a carriage return and line feed |

Note the code at 544: it is `2`, not `1`. It is the only indicator in this tail
that is not signalled with a `1`.

### Positions 544-750 for Form 1099-NEC

Identical to the Form 1099-MISC tail with one difference, and the difference is
easy to miss because everything around it agrees: Form 1099-NEC has **no** FATCA
filing requirement indicator, so its blank run begins at 548 and covers 548
through 662, a length of 115. Positions 544, 545-546, 547 and everything from
663 onward are the same as the Form 1099-MISC table above.

## Checks before transmitting

- Every record is exactly the declared length. Count it; do not assume it.
- The field table's own lengths sum to the declared record length, and its
  position ranges are contiguous with no gap and no overlap.
- Slice the finished record back apart at the same offsets and read each field:
  the name control, the identification number, the name lines, the city and the
  postal code must come back out as what went in. This is the check that catches
  an off-by-one that a forward emitter cannot see, because a forward emitter
  produces a well-formed record either way.
- Every payment amount field is twelve digits with no sign and no punctuation,
  including the ones the form does not use.
- No lower-case characters anywhere in the record.
- The tail belongs to the form actually being filed.

## Sources

- Internal Revenue Service, Publication 1220, *Specifications for Electronic
  Filing of Forms 1097, 1098, 1099, 3921, 3922, 5498, and W-2G*, Tax Year 2025
  revision, `https://www.irs.gov/pub/irs-pdf/p1220.pdf`. Part A, Sec. 12,
  Table 1 lists the participating states and their programme codes; Part A,
  Sec. 13, Table 2 lists the postal abbreviations; Part C, Sec. 3 carries the
  payee detail record layout reproduced above; Part E, Exhibit 1 gives the name
  control rules.
- Rights: `https://www.irs.gov/privacy-disclosure/irs-web-site-privacy-and-security-notice`
  - content created or maintained by federal employees in the course of their
  duties is not subject to copyright and may be freely copied; credit is
  requested. Credit: Internal Revenue Service.
