# Who governs, who blocks: the separation of powers in 188 constitutions

We read the texts of all 188 constitutions in force (English editions from the Constitute Project) and wrote each of 11 key decisions as a simple game: which bodies must agree and by what majority. From that we compute each body's share of decision power (the Shapley-Shubik index), the veto players, and the minority of seats that can block. The interactive version (in Polish) covers every country and decision: https://maxqmaxx.github.io/konstytucja/wladza/index.html, with a reform simulator for Poland: https://maxqmaxx.github.io/konstytucja/wladza/symulator.html.

## Key findings

- **Poland's President holds 16.3% of decision power** across 11 decisions: rank 129 of 178 (between 118 and 144 under alternative assumptions). World median for heads of state: 27.5%; EU average 14.7%.
- **Presidential veto.** The Sejm overrides the President's veto with 3/5 of votes (Art. 122(5)), so 40% of deputies can sustain it, worth 10% of power over ordinary law. Only 3 constitutions use 3/5; 53 use 2/3, and in 64 a simple majority overrides the veto.
- **Regime type matters most.** Heads of state hold on average 41.6% of power in presidential systems, 18.2% in premier-presidential systems such as Poland or France, and 13.8% in parliamentary republics. The strongest: Brunei 64.3%, Saudi Arabia 62.5%, Zambia 60.6%, Equatorial Guinea 59.1%, Qatar 57.6%, Tunisia 57.4%, Malawi 55.6%, United Arab Emirates 55.0%.
- **Capture.** In Poland a bare Sejm majority can fill the Constitutional Tribunal (Art. 194: no qualified majority) and the judges' seats on the National Council of the Judiciary (Art. 187: the Constitution leaves the choice to statute). Four of five key institutions are within reach of a simple majority, with or without the President.
- **Judicial independence on paper.** Poland's constitution contains 8 of 10 guarantees (score 80; world median 30, EU average 54). Missing: selection of constitutional judges by more than one body or a supermajority, and a rule that judges elect the judges on the judicial council.

## Poland, the EU and the world

- **Poland**: First chamber 62.2%, Second chamber 4.5%, Government 13.9%, Head of state 16.3%, Judiciary 3.0%
- **EU average (26)**: First chamber 61.5%, Second chamber 4.0%, Government 16.3%, Head of state 14.7%, The people 1.2%, Constitutional court 1.0%, Judiciary 1.2%
- **World average (178)**: First chamber 57.1%, Second chamber 4.7%, Government 9.0%, Head of state 26.8%, The people 1.0%, Constitutional court 0.3%, Judiciary 1.2%

| Decision | Power shares in Poland | Veto players | Blocking minority in the Sejm |
|---|---|---|---|
| Ordinary law | First chamber 90.0%, Head of state 10.0% | First chamber | more than 50.0% |
| Budget | Government 50.0%, First chamber 50.0% | Government, First chamber | more than 50.0% |
| Constitutional amendment | First chamber 50.0%, Second chamber 50.0% | First chamber, Second chamber | more than 33.3% |
| Appointing the head of government | First chamber 100.0% | First chamber | more than 50.0% |
| Removing the government | First chamber 100.0% | First chamber | more than 50.0% |
| Dissolving parliament | Head of state 66.7%, First chamber 33.3% | – | cannot block |
| Constitutional judges | First chamber 100.0% | First chamber | more than 50.0% |
| State of emergency | Government 37.5%, Head of state 37.5%, First chamber 25.0% | Government, Head of state, First chamber | more than 50.0% |
| War and troops | Government 37.5%, Head of state 37.5%, First chamber 25.0% | Government, Head of state, First chamber | more than 50.0% |
| Treaty ratification | First chamber 44.4%, Government 27.8%, Head of state 27.8% | Government, Head of state, First chamber | more than 33.3% |
| Removing the head of state | First chamber 66.7%, Judiciary 33.3% | Judiciary, First chamber | more than 33.3% |

## Regime types

| Type (from the text and CCP coding) | Countries | Head of state | Government | Parliament |
|---|---|---|---|---|
| Presidential | 52 | 41.6% | 0.0% | 56.1% |
| Parliamentary republic | 37 | 13.8% | 12.6% | 71.8% |
| Semi-presidential, premier-presidential | 26 | 18.2% | 9.8% | 68.2% |
| Parliamentary monarchy | 18 | 17.5% | 19.0% | 61.7% |
| Semi-presidential, president-parliamentary | 16 | 30.5% | 14.0% | 51.8% |
| Government answers to parliament and an indirectly chosen head of state | 12 | 25.5% | 12.5% | 61.2% |
| Government answers only to the head of state | 10 | 36.6% | 5.6% | 55.7% |
| Not determinable from the text | 5 | 15.6% | 22.2% | 57.1% |
| President elected by parliament heads government | 2 | 31.2% | 0.0% | 66.7% |

## Who can capture institutions

For each institution named in a constitution: the weakest political camp that fills it on its own. Share of ranked countries that have the institution in their constitution.

| Institution | Countries | Simple majority or ordinary law | Supermajority or judges needed | Poland |
|---|---|---|---|---|
| Constitutional court | 88 | 53.4% | 46.6% | simple majority in the chamber |
| Judicial council | 130 | 72.3% | 27.7% | left to ordinary law |
| Ombudsman | 89 | 100.0% | 0.0% | simple majority in the chamber |
| Central bank | 95 | 100.0% | 0.0% | majority + head of state |
| Prosecutor general | 149 | 83.9% | 16.1% | left to ordinary law |
| Electoral body | 113 | 85.0% | 15.0% | not in the constitution |
| Amending the constitution | 178 | 4.5% | 95.5% | 2/3 of seats |

## How far to trust these numbers

- **Readings vs experts.** Our language-model readings (with verbatim quotes checked in code) agree with the hand coding of the Comparative Constitutions Project (v5, 2023) in 88.1% of 1641 comparisons; structural fields reach 97–99% (chambers, veto override threshold, dissolution). Each of the 188 disagreements was then adjudicated against the text (question in our definition, blind to who answered what, verbatim quote required): 42 readings were corrected, giving 90.5%.
- **Regime types** agree with Cheibub, Elkins and Ginsburg (2014) in 84.0% of 106 constitutions (kappa 0.76). Our head-of-state share falls in their order: presidential 39.2%, semi-presidential 21.4%, parliamentary 15.8%.
- **Judicial index** correlates moderately with the Melton-Ginsburg de jure index (Spearman ρ = 0.323, 95% CI 0.166–0.465).
- **CCP executive power index** (7 powers) correlates weakly with our executive share (ρ = 0.186): it counts powers of the whole executive, including prime ministers, and barely separates regime types, so it measures something else.
- **Robustness.** Under alternative assumptions the ranking correlates 0.87–0.994 with the baseline, but a single country typically moves 26 places, so we report ranges.

## Limits

- Text only: no statutes, standing orders, case law or practice. Bodies are treated as unitary; the model knows nothing about parties, coalitions or cohabitation.
- Chambers are modelled as large bodies of equal members; agenda-setting (who proposes first) carries no power, only whose consent is needed.
- Where the text is silent, the assumption is listed next to the decision; a missing provision is not proof of absence.
- Data and code: github.com/maxqmaxx/konstytucja (dane/wladza_*.csv, kod/analysis/wladza/). CCP data: Elkins and Ginsburg, Characteristics of National Constitutions v5 (2025).
