Task:
A payables team has finished assembling this year's information returns and now
has to hand them to the US tax authority's electronic transmission channel. The
payee details are settled and reviewed. What is left is to render each payee as
the line that channel accepts.

Input (`/root/data/`):

1. `payees.json` - the return type, the payment year, and one entry per payee.
   Each entry carries the payee's reference label, the name control, the kind of
   taxpayer identification number and the number itself, the account number and
   office code the issuer assigned, whether the return is an original or a
   correction, the payment amounts by amount code in US dollars, the payee's
   name lines, mailing address, city, state and postal code, the ordinal
   position that payee's record occupies in the transmission file, the notice
   and sales indicators that apply, the state and local tax withheld, and the
   state programme code where one applies.

2. `question.json` - the specification the transmission must conform to, given
   by publisher, document, title and revision, together with the record name,
   the exact character length of one record, the return type, the payee
   references to emit, and the output contract. It also carries a
   `decoy_reference` block holding the same payee details as the payables system
   exports them, comma-delimited; that block is supplied for orientation.

The specification named in `question.json` governs, and the revision named there
is the one in force for this payment year: the layout that revision publishes is
the layout the channel reads.

Each payee entry becomes one line of exactly the character length
`question.json` states, in which every field occupies its own range of character
positions and no separator characters appear anywhere. Placement, padding and
character case are all part of what the channel checks, because it slices each
line apart at positions it holds internally rather than parsing it.

Output:
Write `/root/results.json` with exactly:

```json
{"records": {"XX0000": "ZZZZ ... ZZZZ"}}
```

- `records` - an object with one entry per payee reference listed in
  `question.json`, mapping that reference to that payee's line.

(`XX0000` is not a payee reference in the data, and the value shown stands for a
line made up entirely of the letter Z. Both are placeholders showing the JSON
shape; they are not the answer.)

Scoring: each submitted line is sliced back apart at the positions the
specification fixes, and every field is decoded and compared against the payee
entry it was built from. There is one case per field group per record, plus one
case for the shape of the answer file as a whole; `question.json` states the
total. Score = cases passed / total.

The container has Python 3. No network access.
