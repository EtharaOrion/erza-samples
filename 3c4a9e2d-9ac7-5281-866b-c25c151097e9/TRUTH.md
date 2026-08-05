# TRUTH — golden trajectory for task `ghg-conversion-factor-vintage`

**What this is.** The sequence of moves a competent run makes, in order, from opening the
task to writing the answer file. Each step says *what to do and why*. It is a grader
artifact: it is the spec the process rubric is derived from and the context the judge
panel reads. It is never shown to the agent under evaluation.

**No step states what it evaluates to.** There is not one conversion factor, not one
emissions figure, not one reporting year and not one graded value anywhere in this
document. A reader still has to supply the whole withheld factor set — every category, at
every publication vintage the ledger reaches — and do every multiplication.

**Method versus step answers.** Relations, and the constants that live *inside* a
relation — the arithmetic form of the conversion, the output contract's decimal
precision, the taxonomy's own column structure — are *method*, and they are stated here,
because without them the document is not followable. What is withheld is everything a
step is supposed to *produce or resolve*: every published factor, which numeric value
governs any particular category in any particular publication year, the reporting years
the ledger actually carries, and the graded values.

**Where it comes from.** From the reference derivation `build/gen.py` (the
transformations and every convention it pins, in its order), the independent
re-derivation `build/independent_check.py` (which conventions survive a second
formulation and a second parse of the same workbooks), `task.md` (what is asked and the
output contract), the shipped `environment/data/**` (which fields are present and,
decisively, which are absent), and the measured control routes recorded in
`answer_key.json`'s `control_gaps` (the failure modes the task was *built* to
discriminate). This bundle ships no `oracle/` directory; `build/gen.py` is the oracle for
the purpose of Stage 1, and every convention below is traced to a line of it. It is
**not** derived from the mounted `SKILL.md`, which is a document one arm of the
experiment is given and the other is not.

**The bar this file must clear.** Following these steps, and only these steps, plus the
shipped inputs and the domain knowledge the task exists to test, must land on the
reference answer exactly. Where the reference derivation admits more than one route, the
routes are named in the step rather than left for the rubric to punish.

---

## Step 0 — Read the task statement and fix the output contract before touching the data

**Do:** Establish, before any calculation: that one graded number is the emissions of one
ledger line in one reporting period; that its unit is kilograms of CO2 equivalent; where
the answer file goes; that the answers live under a single named top-level key as an
object; that the object is keyed by `case_id` rather than by the ledger's own line
identifier; and what decimal precision the contract asks for. The shipped question file
restates all of this and names the key for you — read it rather than inferring it from
the example in the prose.

**Why:** A correct calculation serialised into the wrong shape scores zero on every case
at once. The two identifiers in play differ by a fixed prefix, so keying the answer
object by the wrong one is a silent, total loss that looks like a formatting quibble.

**Do not:** treat the worked JSON snippet in the task statement as data. It is a shape
illustration; its key names a case that is not in this input and its value is not any
line's emissions.

---

## Step 1 — Inventory what is on disk, and establish what is *not* there

**Do:** List and read every file under the data directory before planning. Read the
ledger's header and confirm what each column is: a line identifier, a reporting period, a
scope, the taxonomy levels, a sub-column, a unit, a metered quantity, a description. Note
explicitly that the ledger carries **no conversion factor, no emissions figure, no
emissions intensity, no prior-period total, and no factor table of any kind**, and that
the container has no network.

**Why:** This is the step that tells you what kind of problem you are holding. The
arithmetic is one multiplication per line; the whole difficulty is that the multiplier is
not in the box and cannot be reached. A run that assumes the number it needs must be
somewhere on disk spends its budget searching; a run that assumes it must be derivable
from the columns present invents an estimator (see Step 5's **Do not**).

**Do not:** treat the metered quantities as anything other than final. They are exact
metered values in the stated unit; no rounding, no normalisation and no unit conversion
of the input is intended or required.

---

## Step 2 — Read the taxonomy columns as the publisher's own row address

**Do:** Treat the scope column, the category levels and the sub-column together as an
address into the published conversion-factor table, not as free-text description. The
levels are the publisher's own nesting. The sub-column carries a disposal route for waste
lines and a material-sourcing basis for material-use lines, and is empty where the
taxonomy has no such column. The unit column is part of the address, not a label: the
same category is published at more than one unit, and each unit has its own factor.

**Why:** Every column in that address changes the factor. Two lines of the same material
differing only in the sub-column are two different published rows with materially
different factors; a fuel metered by volume and the same fuel metered by energy are two
different published rows. A run that keys its lookup on the leaf category name alone
collapses lines that the publisher separates.

**Also establish:** the published table carries at least one address level that the
shipped ledger does not reproduce as its own column — some rows disambiguate at a level
where the ledger's corresponding value is carried by the unit column instead. Match on
the full address the ledger gives you plus the unit; do not require a shipped column for
every level the publisher prints.

**Do not:** normalise, re-spell or "tidy" the category strings before matching. They are
already the publisher's spellings, including the parenthetical qualifiers that select
between competing rows in the same category.

---

## Step 3 — Name the whole chain before writing any code

**Do:** Write down the chain end to end before implementing any of it:

```
ledger line  ->  its reporting period          ->  the factor set published for that
                                                   reporting year
             ->  its taxonomy address + unit   ->  the row in that set
             ->  the row's headline CO2e factor
line         ->  metered quantity  x  that factor  ->  kilograms of CO2e
case         ->  one entry in the answer object
```

Decide which link is the hard one and budget for it. The arithmetic is one multiplication;
the lookup — and specifically the choice of *which annual set to look in* — is the task.

**Why:** Runs that treat this as one undifferentiated calculation collapse the first two
links into a single factor table applied everywhere, and produce a full, well-formatted,
uniformly wrong answer set. Naming the links first is what prevents that.

**Also establish:** the chain is closed-form throughout. If your design contains a solver
loop, a fit, an optimisation, an interpolation across years or a tolerance, you have
mis-modelled the problem.

---

## Step 4 — Compute the answers with executable code, never by hand

**Do:** Author the derivation as source — a script, or a heredoc into an interpreter —
that reads the shipped ledger, applies the chain, and writes the answer file. Then run it.
Keep the factor figures you supply in one named table in that source, indexed by
publication year and by the row address, so the thing you are *asserting* is separable
from the thing you are *computing*.

**Why:** The graded band is a tight relative one — tighter than the agreement a figure
carried at three significant figures can establish — and the quantities span several
orders of magnitude, so hand arithmetic is not reliable at the precision required. More
importantly, an answer file written by hand cannot be re-derived, re-checked or corrected
when one factor turns out to be wrong or one vintage turns out to be misassigned. Keeping
the recalled table separate from the arithmetic is what makes Step 9's verification
possible at all.

**Do not:** write the answer file directly with values you computed in your head or in
prose. That is the one failure mode this channel exists to catch, and it is invisible in
the answer file itself.

---

## Step 5 — Decide where the conversion factors come from, and say so

**Do:** State, before you use them, where your factor figures come from: recalled domain
knowledge, or a mounted reference if the environment provides one. If they are recalled,
say that, say which publication vintage each figure is a memory *of*, and say how
confident you are per figure — distinguishing figures you hold at the published precision
from figures you are approximating.

**Why:** The published factor set is the withheld object of this task. It is not in the
environment, it cannot be reached over the network, and it cannot be reconstructed from
the columns you were given. Every graded value is decided entirely by which figures you
put in that table and which vintage you file them under, so the table's provenance *is*
the run's evidence. A run that supplies figures and never says where they came from has
produced an answer with no argument attached to it.

**Do not:** manufacture a factor out of the ledger's own columns. There is no relation
among the shipped columns that contains a factor — the quantities are physical amounts
and nothing else — so any "derivation" from them is an invention wearing a derivation's
clothes. In particular: do not infer one line's factor as a ratio of another line's, do
not treat a transmission-and-distribution category as a fixed fraction of its generation
category, and do not treat an upstream well-to-tank category as a fixed uplift on the
corresponding direct-combustion category. Those relationships are not published as
identities and do not hold numerically.

**Do not:** attempt to reach a data source over the network, or install a package to
fetch one. The container is offline by construction and an attempt is a wasted step, not
a route.

---

## Step 6 — Select the conversion factor that governs the line

**Everything before this is bookkeeping. This step is the task.** Steps 0–5 are reading,
addressing and plumbing; Steps 7–8 are one multiplication and a serialisation. The entire
difficulty of this task, and every measured control route that misses it, lives in
choosing *which published number* stands as a given line's factor.

The choice has three parts. They are independent, and getting any one of them wrong moves
the graded value far outside tolerance while leaving an answer that is well-formed,
correctly signed and plausibly sized. They are taken separately in Steps 6a, 6b and 6c.

**Why the three are independent:** the same line has a different factor under a different
annual vintage of the same table, a different factor at a different row address in the
same vintage, and a different factor if the single-gas component is taken in place of the
headline figure. A run can be right about two and wrong about the third and produce
something that looks exactly like a correct answer.

---

## Step 6a — Bind the factor set to the line's own reporting year

**This is the sub-step the task exists to measure.** The conversion factors are not
physical constants. The publisher re-derives the whole set every year from fuel-quality
survey returns, the realised grid generation mix, water-industry returns and waste-stream
studies, and publishes a new set annually. The rule is: **the set published for the
reporting year is the set that governs that reporting year's activity.** Apply it per
line, from the line's own reporting period — never once for the whole ledger.

**Do:** Read each line's reporting period, resolve it to the reporting year, and take that
line's factor from the annual set carrying that year. When the ledger spans more than one
reporting period, the same category must be converted with a *different* number in each
period, because the published sets differ at that category between adjacent years.

**Why:** The vintage decision alone decides every graded case. Measured on this bundle's
own controls, with the row address, the unit and the arithmetic all correct:

| Route (everything else correct) | Gap from the reference value | Cases it passes |
|---|---|---|
| newest published set applied to every reporting period | 14 to 1495 tolerances | none |
| the set published one year earlier than the reporting year | 16 to 1841 tolerances | none |
| the set published one year later than the reporting year | 14 to 1495 tolerances | none |
| the average of the published sets across the vintages in play | 3 to 4879 tolerances | none |

The first of those is the nearest real competitor: it is what a run does when it recalls
"the current published factors" and applies them to both periods. It is well-formed,
internally consistent, defensible-sounding, and wrong on every graded line.

**Do not:** apply one factor set to the whole ledger; take "the most recently published
set" unconditionally; interpolate or extrapolate between annual sets; average the sets;
or assume the year-on-year change is small enough to ignore. The year-on-year moves at
the graded categories run from a fraction of a percent to tens of percent, in directions
that differ by category — so no single escalator applied across categories reproduces the
set for another year either.

**Do not:** assume the vintage you recall best is the governing one. If you cannot produce
*different* figures for two adjacent publication years at the same category, then you do
not hold vintage-resolved figures at all, and Step 5's provenance statement should say so
rather than presenting one remembered set as though it were year-specific.

---

## Step 6b — Address the row at the line's exact unit and sub-column

**Do:** Within the governing annual set, take the row whose address matches the line's
full taxonomy path, whose sub-column matches the line's sub-column, and whose unit of
measure matches the line's metered unit exactly. Where a line is metered in energy, the
calorific-value basis stated in the unit is part of the address: the same fuel is
published at a gross basis and at a net basis and they are different numbers. Where a
line is metered by volume, the volume is metered volume and is converted by the
volume-basis row, not by converting the volume to energy first.

**Why:** Each of these is a published row of its own with its own factor, and substituting
a neighbouring row gives a figure that is real, published, correctly vintaged and wrong.
The sub-column is the sharpest case: for one material, two disposal routes are two rows
whose factors differ by more than an order of magnitude in some categories.

**Do not:** convert a metered volume into energy using a calorific value and then apply an
energy-basis factor; substitute a net-basis row for a gross-basis one or the reverse;
apply one material's factor across all of that material's disposal routes; or drop the
qualifier in parentheses on a fuel name, which selects between competing rows in the same
category.

---

## Step 6c — Take the headline CO2e figure, not a single-gas component of it

**Do:** Each published row is emitted at more than one greenhouse-gas basis: a headline
carbon-dioxide-equivalent figure and, separately, the single-gas components it is built
from. Take the headline CO2 equivalent.

**Why:** The components are published beside the headline in the same table, at the same
address, and are the same order of magnitude for some categories — so taking one produces
a real published number that fails the graded band. The reference derivation filters on
the greenhouse-gas basis column and keeps only the equivalent figure; this is a
convention it pins silently and a reader who does not pin it will diverge.

**Do not:** sum the single-gas components to reconstruct the equivalent figure. They are
rounded independently of the headline and independently of each other, and the
reconstruction does not reproduce the published equivalent to the precision this task
grades at. The headline figure is the published quantity; use it directly.

---

## Step 7 — Convert the metered quantity with one multiplication, in the line's own unit

**Do:** For each reported line, with `q` the metered quantity as shipped and `f` the
governing factor selected in Step 6:

```
kg CO2e = q * f
```

The factor is published per unit of the line's own metered unit, so no unit conversion,
no scaling and no intermediate normalisation enters. Carry the arithmetic at full
floating-point (or exact decimal) precision; do not round `q`, do not round `f`, and do
not round any intermediate.

**Why:** The published factors carry several significant figures and the graded band is a
tight relative one. Rounding the factor to a remembered headline precision is not a small
error here — it is the strongest recall-only route available and it was priced: carrying
the *correct vintage's correct row* at three significant figures still misses every
graded line, by 2 to 17 tolerances. Precision is not decoration on this task; it is part
of the answer.

**Do not:** convert units "to be safe" (tonnes to kilograms, cubic metres to litres, kWh
to MJ) before multiplying. The factor is already expressed per the shipped unit, and a
conversion applied on one side only is a clean order-of-magnitude error that survives
every plausibility check.

---

## Step 8 — Serialise one number per requested case, at the contract's precision

**Do:** Write the answer file at the contract's path, with the answers nested under the
contract's top-level key, as an object with exactly one entry per case listed in the
question file's case list, keyed by `case_id`, each value a JSON number carried to at
least the number of decimal places the contract asks for. Ledger lines that are not
listed as cases are context and are not reported.

**Why:** The graded set is per case; a missing key is a lost case, and the wrong
top-level key or the wrong identifier spelling loses all of them at once. Precision
matters in the ordinary way: the tolerance is a small relative band, and the graded
values span orders of magnitude, so an emitted value rounded to whole units is inside the
band for the largest cases and far outside it for the smallest.

**Do not:** emit the values as strings, as tonnes, as percentages, or formatted to fewer
decimals than the contract asks for; do not invent keys for unreported ledger lines; and
do not round anywhere upstream of the final write — round once, at the end, if at all.

---

## Step 9 — Verify with a check that could have disagreed

**Do:** Before reporting, run at least one check whose outcome was not already determined
by the factor table you chose. The distinction is the whole point of this step:

| Check | Can it disagree with you? |
|---|---|
| Re-running your multiplication over your own factor table | **No.** It reproduces your arithmetic, wrong table and all |
| Recovering a factor as emitted value over metered quantity | **No.** An algebraic identity — it cannot fail |
| The emitted values are positive and plausibly sized | **No.** Any factor of the right order of magnitude produces those |
| The two reporting periods give different totals | **No.** The metered quantities differ between periods anyway |
| The answer object has an entry per requested case | **No** about the numbers — it is a contract check, and it belongs at Step 8 |
| Your factor agrees at three significant figures with a headline figure you also recall | **No.** Measured: agreement at that precision leaves every graded line outside the band |
| Confirming your table returns a *different* number for the same category in the two reporting periods, and that the differences are not one uniform escalator across categories | **Yes** |
| Confirming your table returns different numbers for two disposal routes of one material, and for the two calorific-value bases of one fuel | **Yes** |
| Cross-checking two rows of the same fuel within one annual set through a published physical property — the volume-basis factor over the gross-energy-basis factor must equal that fuel's volumetric gross calorific value; the gross-basis factor over the net-basis factor must equal that fuel's gross-to-net calorific ratio | **Yes** |
| Confirming the row you addressed carries the line's own metered unit rather than a neighbouring unit in the same category | **Yes** |
| Re-deriving one line in exact decimal instead of binary floating point | **Weakly.** It catches parse and arithmetic slips only — never a wrong factor and never a wrong vintage |

**Why:** This task's characteristic failure is a run that is internally consistent and
externally wrong. Every cheap check passes for such a run — the shape is right, the units
are right, the magnitudes are right, its own arithmetic reproduces exactly. Confidence is
not evidence here, and the measured control routes are all confident.

**Do not:** present your answers as "verified", "cross-checked" or "validated" on the
strength of a check from the upper half of that table. If the only real evidence is that
you recalled the figures and believe them, say exactly that instead.

---

## Step 10 — Working conditions to respect throughout

**Do:** Work only from what the container provides — the shipped data directory, the
interpreter that is installed, and a mounted reference directory if one is present. Leave
the shipped inputs exactly as you found them; copy them out if you want to work on them.
Stay inside the time budget: the lookup is the expensive part, not the arithmetic.

**Do not:** modify, move, truncate or overwrite anything in the input data directory;
attempt network access; install packages. The container is offline by construction, and
the grading of both channels reads the shipped ledger as it was shipped.

---

## The failure modes this task discriminates

Each of these was implemented and priced against every graded line during construction,
and each misses every one of them by more than the tolerance. They are listed so that a
reader recognises them as failures rather than as reasonable approximations:

- the newest published factor set applied to every reporting period — the nearest real
  competitor, and what "use the current published factors" produces;
- the set published one year earlier than the reporting year, everything else correct;
- the set published one year later than the reporting year, everything else correct;
- the average of the published sets across the vintages in play — the route that denies
  the reporting year matters;
- the correct vintage's correct row carried at three significant figures — the strongest
  route available to a run that recalls the shape of the table but not its precision;
- reporting nothing, i.e. zero emissions;
- a single constant reported for every case — swept exhaustively in closed form over the
  whole range of graded values, and separated by construction so that no constant can
  reproduce more than the one case it sits on.

---

## What a finished run must have produced

Stated as properties, not values:

- an answer file at the contract's path, with the answers nested under the contract's
  top-level key;
- exactly one entry per case listed in the question file's case list, keyed by `case_id`
  and not by the ledger's line identifier, with no invented keys;
- every value a JSON number in kilograms of CO2 equivalent, positive, carried to at least
  the contract's decimal precision;
- a factor that varied with the line's reporting year, with the line's row address
  including its unit and sub-column, and that was the headline equivalent figure rather
  than a single-gas component — three separate dependencies, all present;
- for a category appearing in more than one reporting period, two *different* factors
  actually applied, whose ratio is not shared with the other categories' year-on-year
  ratios;
- factors carried at published precision, not at the precision of a rounded recollection;
- a re-runnable artifact: source that reproduces the emitted numbers from the shipped
  ledger plus the run's own factor table, and evidence that it was run;
- a stated provenance for that factor table, per vintage, and at least one verification
  whose result was not predetermined by it;
- the input data directory byte-identical to how it was shipped.

The numeric ground truth for this task lives grader-side in the bundle's
`answer_key.json` under `graded_outputs`, with the per-case tolerance and the measured
control-route gaps beside it. It is deliberately not reproduced here, and no criterion
derived from this document may be graded by comparing against it.
