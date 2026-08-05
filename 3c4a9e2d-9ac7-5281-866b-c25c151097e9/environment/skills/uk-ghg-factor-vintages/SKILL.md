---
name: uk-ghg-factor-vintages
description: >-
  Compute a UK organisation's greenhouse-gas inventory lines in kg CO2e from
  metered activity data using the UK Government's annual conversion-factor
  publication, including which annual factor vintage governs a given reporting
  period and the vintage-specific factor values for stationary fuels, grid
  electricity and its transmission and distribution losses, water, purchased
  materials, biomass and biogas combustion, well-to-tank emissions and waste
  disposal routes. Do not use this for non-UK inventories, for reporting periods
  before 2023 or after 2026, for product life-cycle assessments, for the
  CH4-only or N2O-only subcomponents of a factor, or when the emissions figures
  themselves are already supplied and only need aggregating.
---

# UK GHG conversion factors: the vintage rule and the factor tables

The UK Government publishes a conversion-factor set every year (the series
historically known as the Defra factors, now published by the Department for
Energy Security and Net Zero). Each set is re-derived annually from fuel-quality
surveys, the actual generation mix of the grid, water-industry data and
waste-stream studies — so the factor for the same activity, in the same unit,
is a different number in different years. The sets are not interchangeable and
there is no formula linking one year's value to the next: the annual movement
is an empirical result, not a trend you can extrapolate.

## 1. The vintage rule

**Each reporting period uses the conversion-factor set published for that
reporting year.** Activity metered in calendar year 2024 is converted with the
2024 set; activity metered in calendar year 2025 with the 2025 set. Applying
the newest set to every year, or the previous year's set to this year, is the
standard error this procedure exists to prevent: the factors move year to year
by anything from a fraction of a percent (gaseous fuels) to tens of percent
(grid electricity, water, recycling routes), and the direction of movement
differs by category, so no uniform correction recovers a mis-vintaged result.

## 2. Selecting the factor

A factor is identified by the full category path AND the unit. Match every
level exactly:

- **Category path** — Scope / Level 1 / Level 2 / Level 3 (and, where the
  table has one, the column label such as a waste-disposal route or a
  material-sourcing basis).
- **Unit** — the factor is per unit stated. A kWh factor and a cubic-metre
  factor for the same fuel are different numbers, and kWh factors state their
  calorific-value basis: a quantity billed in kWh (Gross CV) must use the Gross
  CV factor, not the Net CV one (they differ by roughly ten percent for
  natural gas).

Then: **kg CO2e = quantity × factor.** No other adjustment applies to the
headline kg CO2e figure. Report the product at full precision; do not round
the factor before multiplying.

## 3. Factor tables, by vintage

Headline **kg CO2e per unit** values from the four annual sets, at the
categories and units this procedure covers. Values are transcribed from the
published flat-format tables exactly as stored; the 2023 edition stores some
factors at full computational precision and later editions store them at five
to six significant figures — use each figure as printed, do not re-round.

### Scope 1 — fuels and on-site combustion

| category / unit | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| Fuels / Gaseous fuels / Natural gas / cubic metres | 2.038390310067114 | 2.04542 | 2.06672 | 2.02633 |
| Fuels / Gaseous fuels / Natural gas / kWh (Gross CV) | 0.18292892617449666 | 0.1829 | 0.18296 | 0.18231 |
| Fuels / Liquid fuels / Petrol (average biofuel blend) / litres | 2.097473127516779 | 2.0844 | 2.06916 | 2.075 |
| Fuels / Liquid fuels / Diesel (average biofuel blend) / litres | 2.5120638845637586 | 2.51279 | 2.57082 | 2.58354 |
| Bioenergy / Biomass / Wood pellets / tonnes | 51.56192 | 54.33654 | 55.19389 | 57.25249 |
| Bioenergy / Biomass / Grass/straw / tonnes | 57.63342 | 54.08777 | 47.35709 | 46.89059 |
| Bioenergy / Biogas / Biogas / tonnes | 1.23595 | 1.26431 | 1.24314 | 1.22851 |

(Bioenergy factors above are the combustion-emissions basis the published
tables carry for these rows; biogenic CO2 is reported outside scopes and is
not part of these figures.)

### Scope 2 — purchased electricity

| category / unit | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| UK electricity / Electricity generated / Electricity: UK / kWh | 0.20707428859060403 | 0.20705 | 0.177 | 0.13096 |

### Scope 3 — upstream, water, materials and waste

| category / unit | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| Transmission and distribution / T&D- UK electricity / Electricity: UK / kWh | 0.017915111409395973 | 0.0183 | 0.01853 | 0.01299 |
| Water supply / cubic metres | 0.1766845465790137 | 0.15311 | 0.1913 | 0.1913 |
| Water treatment / cubic metres | 0.20131829171065632 | 0.18574 | 0.17088 | 0.17088 |
| Material use / Paper / Paper and board: board / Primary material production / tonnes | 801.5217654981054 | 1193.96586 | 1199.72542 | 1198.23866 |
| Waste disposal / Plastic / Plastics: average plastics / Closed-loop / tonnes | 21.28080723687633 | 6.41061 | 4.68568 | 4.65358 |
| Waste disposal / Plastic / Plastics: average plastics / Landfill / tonnes | 8.884130131626865 | 8.88386 | 8.98311 | 9.00687 |
| Waste disposal / Construction / Insulation / Landfill / tonnes | 1.2340139100536913 | 1.23393 | 1.26338 | 1.27043 |
| Waste disposal / Refuse / Organic: food and drink waste / Composting / tonnes | 8.912421710629 | 8.88386 | 8.98311 | 9.00687 |
| WTT- fuels / Gaseous fuels / Natural gas / cubic metres | 0.3366 | 0.3366 | 0.3366 | 0.3366 |

## 4. Worked example (2023 reporting period, illustrative)

Factors in this example are the natural-gas volume rows of the 2023 and 2025
editions in the tables above, as published on
https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting.

A site burned 1,000 cubic metres of natural gas in calendar year 2023. The
2023 vintage governs, its natural-gas volume factor is 2.038390310067114 kg
CO2e per cubic metre, so the line is 1,000 × 2.038390310067114 =
2,038.390310067114 kg CO2e. The same volume in a 2025 reporting period would
use 2.06672 and give 2,066.72 kg CO2e — the difference is entirely the
vintage.

## 5. Checks before reporting

1. Every line's factor came from the vintage matching that line's reporting
   period — never from the newest table by default.
2. Every kWh line's calorific-value basis matches the factor used.
3. Waste lines matched the disposal route column (landfill, closed-loop,
   composting…), and material-use lines matched the sourcing basis.
4. No factor was rounded before multiplying.

## Source

UK Government greenhouse gas reporting: conversion factors, annual editions
2023–2026, Department for Energy Security and Net Zero (with Defra),
gov.uk collection "Government conversion factors for company reporting".
Contains public sector information licensed under the Open Government Licence
v3.0.
