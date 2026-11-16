# Sector likelihood register: what does a 1-10 "probability" mean?

**Status: working draft, version 0.2 (16 November 2026).**

This is an independent study by Nikhil Sehgal. It is not a product of Catena-X, BMW Group or Ulm
University, and it uses public data only.

## The problem

The Catena-X Due Diligence Check plans a shared country and sector risk register for the abstract
risk analysis of suppliers ([DDC KIT][kit]). A sector register is useful if a user can compare
sectors, for example land transport, rubber and consulting, on one protected right. A natural format
is a likelihood from 1 to 10.

Weber (2026) coded 1,305 documented risks into 87 NACE divisions and concluded that the frequency of
risk mentions "reflects visibility rather than probability". That leaves a measurement question
open: before a register can estimate a likelihood, it must say what the likelihood is a likelihood
of, and how a point from 1 to 10 follows from it.

## The four questions

This study assumes that a sector register which continues the published work must answer four
questions. The assumption is the reading of the author from public documents (the [DDC KIT][kit]
and Weber 2026). Nobody at Catena-X, BMW Group or Ulm University confirmed it.

1. **Method.** Which rule gives each NACE division a likelihood for one protected right, so that
   another person can get the same result?
2. **Data gaps.** How does the register score a sector with few or no documented cases, without
   reading silence as low risk?
3. **AI.** Where can AI collect and code the evidence without loss of traceability?
4. **Integration.** How does the sector score combine with the country register and the company
   size?

The code tests questions 1, 2 and 4 on the one protected right for which public rates per NACE
division exist: occupational health and safety (Eurostat accidents at work). Question 3 has no code
yet.

## Results

All numbers are in [`results/RESULTS.md`](results/RESULTS.md). The scripts write that file.

| Question | Experiment | Result on Eurostat data |
|---|---|---|
| 1 Method | E1 mapping rule | The same 2024 fatal accident rates give land transport, rubber and consulting 3/2/1 on a fixed logarithmic scale, 10/6/2 as deciles and 1/1/1 on a linear scale. The order of the sectors stays the same. |
| 1 Method | E3 stability | A score from the 2020-2022 mean ranks the 2023-2024 rates with a Spearman correlation of 0.872 (0.819 from 2022 alone). 11% of divisions change their point on the fixed log scale. 47% change their decile. |
| 1 Method | E4 sensitivity | With three time windows and three positions of the scale limits, 74 of 88 divisions change their point by 1 or 2. |
| 2 Data gaps | E2 visibility | In 2022 the recorded non-fatal accidents per fatal accident run from 25 (Bulgaria) to 3,410 (Netherlands). The rank correlation between the non-fatal and the fatal rate across 30 countries is -0.04. |
| 2 Data gaps | E5 sparse divisions | In one year, 24 of 87 divisions have fewer than 5 fatal accidents and 4 have none. All 4 have accidents in the next two years. A pull toward the rate of the NACE section lowers the number of wrong points from 17 to 11 with one year of data, and from 10 to 8 with three years. With three years the rank correlation does not improve (0.867 raw, 0.848 with the pull). |
| 4 Integration | E6 country and sector | Across 455 country-sector cells, sector alone explains 67% of the deviance, country alone 24%, and country factor times sector factor 90%. Real differences remain: 27% of the large cells get a different point from the factor model than from their own rate. |
| 4 Integration | E1 company size | For land transport, the probability of at least one fatal accident per year is 0.37% for 50 workers and 31% for 5,000 workers. Company size must enter one time only. |

Reading of the results (analysis of the author, not a proven finding):

1. A point from 1 to 10 has a meaning only if the register publishes the event, the unit, the
   period and the mapping rule. A relative scale (deciles) changes when other sectors change. A
   fixed scale does not.
2. A count of recorded cases is not a likelihood. It needs a correction for the recording system,
   and no recorded case in a small sector does not mean no risk.
3. For sectors with few cases, information from similar sectors helps most when the data are thin.
4. Country factor times sector factor is a useful first model. It is not sufficient for all
   country-sector pairs, so a register needs a rule for exceptions.

## The scale used here

`register/scales.py` holds a fixed logarithmic scale. Each point is about 3 times the point below:
point 2 starts at 1 in 100,000 workers per year and point 10 starts at 1 in 10. This table is a
proposal of this study. It is not a standard, and E4 shows how the points move if the limits move.

## Limits

- **One right only.** Public rates per NACE division exist for accidents at work. For child labour
  and forced labour no such rates were found, so this code says nothing about them.
- **EU data only.** The rates describe work in the EU-27, not global supply chains.
- **Fatal accidents are rare.** They use only points 1 to 4 of the scale.
- **Small numbers.** Rates of small countries and small divisions change much from year to year.
  Four divisions show a rate of 0 in 2024.
- **Stability is not validity.** E3 shows that the score is stable over time. It does not show that
  the score is correct.
- **No AI component yet.** The study plan includes a text pipeline that extracts and codes evidence
  for rights without statistics. This repository has no such code and makes no claim about it.
- **Likelihood only.** Severity is a separate dimension and is not scored here.

## Run it

Python 3.10 or later. No packages are necessary.

```
py -m unittest          # unit tests
py run_all.py           # use the stored Eurostat data
py run_all.py --refresh # download the data again
```

`data/raw/` holds the Eurostat responses that produced the committed results, with the retrieval
date and the request URL inside each file.

## Data and sources

- Eurostat, accidents at work by NACE Rev. 2 activity: `hsw_n2_01` (non-fatal) and `hsw_n2_02`
  (fatal), incidence per 100,000 persons employed. Source: Eurostat, reuse with attribution.
- Catena-X Due Diligence Check KIT, Eclipse Tractus-X. [Source on GitHub][kit].
- Cox, L.A. (2008). What's wrong with risk matrices? *Risk Analysis* 28(2), 497-512.
  doi:10.1111/j.1539-6924.2008.01030.x
- Hubbard, D.W. and Evans, D. (2010). Problems with scoring methods and ordinal scales in risk
  assessment. *IBM Journal of Research and Development* 54(3), 2:1-2:10. doi:10.1147/JRD.2010.2042914
- Saisana, M., Saltelli, A. and Tarantola, S. (2005). Uncertainty and sensitivity analysis techniques
  as tools for the quality assessment of composite indicators. *Journal of the Royal Statistical
  Society A* 168(2), 307-323. doi:10.1111/j.1467-985x.2005.00350.x
- Weber, K. (2026). *Assessment of sector-specific human rights and environmental risks: Study
  Summary.* Digitale Schriftenreihe Ulm NUF, 05/2026. [PDF][weber].

## Licence

Code: MIT. Eurostat data: copyright European Union, reuse allowed with attribution.

[kit]: https://github.com/eclipse-tractusx/eclipse-tractusx.github.io/tree/main/docs-kits/kits/due-diligence-check-kit
[weber]: https://www.uni-ulm.de/fileadmin/website_uni_ulm/mawi.nachaltman/Schriftenreihe/Schriftenreihe_StudySummary-KWeber.pdf
