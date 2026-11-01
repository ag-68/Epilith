# Experiment 0a report

Generated at: 2026-10-31T21:58:02.885196+00:00
Overall: FAIL

## NVDA: 11/12 valid

| Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status |
|---|---|---|---|---|---|---|---|---|---|
| revenue | 302969000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 302969000000 | 0 | valid |
| operating_income | 197579000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 |  | None | None | valid |
| net_income | 192879000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 192879000000 | 0 | valid |
| operating_cash_flow | 134360000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 134361000000 | 1000000 | valid |
| capex | 7354000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 7355000000 | 1000000 | valid |
| total_debt | 33366000000 | USD | USD | as of 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 33366000000 | 0 | valid |
| cash | 22443000000 | USD | USD | as of 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 22443000000 | 0 | valid |
| shares_outstanding | 24100000000 | shares | None | as of 2026-08-21 | 19ef503a5770 |  | None | None | failed |
| price | 204.64 | USD | USD | 2026-10-30T00:00:00+00:00 | 942f66d2cc44 | 1af47414b360 | 204.63999938964844 | 6.1035156E-7 | valid |
| reporting_currency | 1 | USD | USD | as of 2026-07-26 | 19ef503a5770 |  | None | None | valid |
| fiscal_period | 739823 | date_ordinal | None | as of 2026-07-26 | 19ef503a5770 |  | None | None | valid |
| listing | 1 | NASDAQ:NVDA | USD | as of 2026-07-26 | 19ef503a5770 |  | None | None | valid |

### Valuation panel

- Listing: NASDAQ:NVDA (USD)
- Price: 204.64 as of 2026-10-30 00:00:00+00:00
- Shares: 24100000000
- Market cap: 4931824000000.00
- Total debt: 33366000000
- Cash: 22443000000
- EV: 4942747000000.00
- TTM revenue: 302969000000 (end 2026-07-26)
- TTM net income: 192879000000
- TTM FCF: 127006000000
- Trailing P/E: 25.56952286148310598872868482
- EV/Sales: 16.31436549613986909551802330
- FCF yield: 0.02575233828295575835634037224
- Balance sheet as of: 2026-07-26
- Note: Descriptive evidence only. Trailing P/E is misleading for cyclical semiconductor companies.
- Note: No forward P/E, DCF, reverse valuation, or scenario weighting in Experiment 0a.
- Note: FCF = TTM operating cash flow − TTM capex. Provider FCF is not used.
- Note: Market cap mixes price as of 2026-10-30T00:00:00+00:00 with shares as of 2026-08-21.

### Discrepancies

- revenue: passed=True class=None primary=302969000000 cross=302969000000 pct=0 
- net_income: passed=True class=None primary=192879000000 cross=192879000000 pct=0 
- operating_cash_flow: passed=True class=None primary=134360000000 cross=134361000000 pct=0.000007442691277165823161655254540 
- capex: passed=True class=None primary=7354000000 cross=7355000000 pct=0.0001359804188196899646450911069 
- total_debt: passed=True class=None primary=33366000000 cross=33366000000 pct=0 
- cash: passed=True class=None primary=22443000000 cross=22443000000 pct=0 
- shares_outstanding: passed=False class=DiscrepancyClass.unresolved primary=24100000000 cross=None pct=None No second document states this line. The first source was not compared with itself.
- price: passed=True class=None primary=204.64 cross=204.63999938964844 pct=2.982562353401094605160281470E-9 

### Findings

- NVDA home market is United States (NASDAQ:NVDA). Filings are read with the United States adapter.
- revenue: using us-gaap:Revenues (121 unique periods)
- operating_income: using us-gaap:OperatingIncomeLoss (112 unique periods)
- net_income: using us-gaap:NetIncomeLoss (124 unique periods)
- operating_cash_flow: using us-gaap:NetCashProvidedByUsedInOperatingActivities (76 unique periods)
- capex: using us-gaap:PaymentsToAcquireProductiveAssets (24 unique periods)
- cash: using us-gaap:CashAndCashEquivalentsAtCarryingValue (77 unique periods)
- short_term_investments: using us-gaap:DebtSecuritiesCurrent (3 unique periods)
- long_term_debt_noncurrent: using us-gaap:LongTermDebtNoncurrent (25 unique periods)
- long_term_debt_current: using us-gaap:LongTermDebtCurrent (21 unique periods)
- long_term_debt_total: using us-gaap:LongTermDebt (50 unique periods)
- operating_lease_liability: using us-gaap:OperatingLeaseLiability (31 unique periods)
- shares_outstanding: using dei:EntityCommonStockSharesOutstanding (69 unique periods)
- shares_outstanding_cover: using dei:EntityCommonStockSharesOutstanding (69 unique periods)
- Reported LongTermDebt equals current + noncurrent; using the sum of components
- Operating lease liability 5494000000 excluded from total_debt
- Live United States filing download failed; using a previously stored snapshot. Error: Client error '403 Forbidden' for url 'https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
- Company quarterly report was downloaded and read as the separate document.

## ASML: 5/12 valid

| Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status |
|---|---|---|---|---|---|---|---|---|---|
| revenue | 35327500000.0 | EUR | EUR | TTM 2025-06-30 to 2026-06-28 | 02ef40cbb531 |  | None | None | failed |
| operating_income | 12513400000.0 | EUR | EUR | TTM 2025-06-30 to 2026-06-28 | 02ef40cbb531 |  | None | None | valid |
| net_income | 10638400000.0 | EUR | EUR | TTM 2025-06-30 to 2026-06-28 | 02ef40cbb531 |  | None | None | failed |
| operating_cash_flow | 11486800000.0 | EUR | EUR | TTM 2025-06-30 to 2026-06-28 | 02ef40cbb531 |  | None | None | failed |
| capex | 1445600000.0 | EUR | EUR | TTM 2025-06-30 to 2026-06-28 | 02ef40cbb531 |  | None | None | failed |
| total_debt | 4390900000.0 | EUR | EUR | as of 2025-12-31 | 764526c6d9fb |  | None | None | failed |
| cash | 6671900000.0 | EUR | EUR | as of 2026-06-28 | 02ef40cbb531 |  | None | None | failed |
| shares_outstanding | 385400000.0 | shares | None | as of 2025-12-31 | 764526c6d9fb |  | None | None | failed |
| price | 1412.800048828125 | EUR | EUR | 2026-10-30T08:00:00+00:00 | db70985d419e | 4b2b3747c2fe | 1412.80 | 0.000048828125 | valid |
| reporting_currency | 1 | EUR | EUR | as of 2026-06-28 | 02ef40cbb531 |  | None | None | valid |
| fiscal_period | 739795 | date_ordinal | None | as of 2026-06-28 | 02ef40cbb531 |  | None | None | valid |
| listing | 1 | EURONEXT:ASML | EUR | as of 2026-06-28 | 02ef40cbb531 |  | None | None | valid |

### Valuation panel

- Listing: EURONEXT:ASML (EUR)
- Price: 1412.800048828125 as of 2026-10-30 08:00:00+00:00
- Shares: 385400000.0
- Market cap: 544493138818.3593750000000
- Total debt: 4390900000.0
- Cash: 6671900000.0
- EV: 542212138818.3593750000000
- TTM revenue: 35327500000.0 (end 2026-06-28)
- TTM net income: 10638400000.0
- TTM FCF: 10041200000.0
- Trailing P/E: 51.18186370303423212137163483
- EV/Sales: 15.34816046474727549359564079
- FCF yield: 0.01844137103690796397895632739
- Balance sheet as of: 2026-06-28
- Note: Descriptive evidence only. Trailing P/E is misleading for cyclical semiconductor companies.
- Note: No forward P/E, DCF, reverse valuation, or scenario weighting in Experiment 0a.
- Note: FCF = TTM operating cash flow − TTM capex. Provider FCF is not used.
- Note: Market cap mixes price as of 2026-10-30T08:00:00+00:00 with shares as of 2025-12-31.
- Note: EV mixes debt as of 2025-12-31 with cash as of 2026-06-28.

### Discrepancies

- revenue: passed=False class=DiscrepancyClass.unresolved primary=35327500000.0 cross=None pct=None No other document states this same twelve-month total. The home-market yearly report is a separate indicator and was not used as confirmation.
- net_income: passed=False class=DiscrepancyClass.unresolved primary=10638400000.0 cross=None pct=None No other document states this same twelve-month total. The home-market yearly report is a separate indicator and was not used as confirmation.
- operating_cash_flow: passed=False class=DiscrepancyClass.unresolved primary=11486800000.0 cross=None pct=None No other document states this same twelve-month total. The home-market yearly report is a separate indicator and was not used as confirmation.
- capex: passed=False class=DiscrepancyClass.unresolved primary=1445600000.0 cross=None pct=None No other document states this same twelve-month total. The home-market yearly report is a separate indicator and was not used as confirmation.
- total_debt: passed=False class=DiscrepancyClass.unresolved primary=4390900000.0 cross=None pct=None No second document states this line. The first source was not compared with itself.
- cash: passed=False class=DiscrepancyClass.unresolved primary=6671900000.0 cross=None pct=None No second document states this line. The first source was not compared with itself.
- shares_outstanding: passed=False class=DiscrepancyClass.unresolved primary=385400000.0 cross=None pct=None No second document states this line. The first source was not compared with itself.
- price: passed=True class=None primary=1412.800048828125 cross=1412.80 pct=3.456124243519205423211917961E-8 

### Findings

- ASML home market is Europe (EURONEXT:ASML). Filings are read with the Europe adapter.
- Home-market source: the public European electronic-report library. The United States filing cabinet was not used for these yearly figures.
- European library search for 'ASML Holding N.V.' returned 5 yearly package(s). It does not publish the last four quarters.
- The latest European yearly report was read. Its full-year figures are a second document, not a substitute for the quarterly statement.
- The company site refused the live download. Using the stored quarterly statement from an earlier retrieval. Live error: Client error '403 Forbidden' for url 'https://investor.asml.com/news-releases/news-release-details/q2-2026-financial-results'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
- revenue was missing from the home-market feed, so the company's quarterly report supplied the last four quarters.
- operating income was missing from the home-market feed, so the company's quarterly report supplied the last four quarters.
- net income was missing from the home-market feed, so the company's quarterly report supplied the last four quarters.
- operating cash flow was missing from the home-market feed, so the company's quarterly report supplied the last four quarters.
- capex was missing from the home-market feed, so the company's quarterly report supplied the last four quarters.
- Cash on the later date comes from the company report. An older home-market figure does not stand in for it.
- The home-market yearly report states revenue of 32667300000.0 for the year ended 2025-12-31 under its own accounting rules. The twelve-month total uses a different set of rules, so this yearly figure is a separate indicator and is not a confirmation.
- The home-market yearly report states net income of 10213000000.0 for the year ended 2025-12-31 under its own accounting rules. The twelve-month total uses a different set of rules, so this yearly figure is a separate indicator and is not a confirmation.
- The home-market yearly report states operating cash flow of 13826500000.0 for the year ended 2025-12-31 under its own accounting rules. The twelve-month total uses a different set of rules, so this yearly figure is a separate indicator and is not a confirmation.
- The home-market yearly report states capex of 1573600000.0 for the year ended 2025-12-31 under its own accounting rules. The twelve-month total uses a different set of rules, so this yearly figure is a separate indicator and is not a confirmation.
- A later statement shows borrowings of 1984400000.0 on 2026-06-28. No second document states that later figure. The older figure on 2025-12-31 is not treated as the latest confirmed borrowings.
- On 2025-12-31, the company report and the home-market filing both state cash of 12916000000.0. The latest figure, on 2026-06-28, does not have a second document.
- ASML failed field validity (5/12)

## TSMC: 9/12 valid

| Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status |
|---|---|---|---|---|---|---|---|---|---|
| revenue | 4440492429000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 170a13bdc7e9 | a55d6aca73ba | 4440492000000 | 429000.0 | valid |
| operating_income | 2491156024000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | f0e27feb8ef8 |  | None | None | valid |
| net_income | 2236752922000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 6efd7856c4ec | a55d6aca73ba | 2237088000000 | 335078000.0 | valid |
| operating_cash_flow | 2634679110000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 648090bab9ac | a55d6aca73ba | 2634679000000 | 110000.0 | valid |
| capex | 1491122744000 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 3be049c1fef7 | a55d6aca73ba | 1491123000000 | 256000 | valid |
| total_debt | 983513000000 | TWD | TWD | as of 2026-09-30 | 05cf01194e35 |  | None | None | failed |
| cash | 3621894000000 | TWD | TWD | as of 2026-09-30 | 05cf01194e35 |  | None | None | failed |
| shares_outstanding | 25932370067 | shares | None | as of 2026-10-31 | beb7de039626 |  | None | None | failed |
| price | 2370.0000 | TWD | TWD | 2026-10-31T21:58:02.728246+00:00 | 54781027d535 | e1efdd946496 | 2370.0 | 0.0000 | valid |
| reporting_currency | 1 | TWD | TWD | as of 2026-10-31 | 170a13bdc7e9 |  | None | None | valid |
| fiscal_period | 739920 | date_ordinal | None | as of 2026-10-31 | 170a13bdc7e9 |  | None | None | valid |
| listing | 1 | TWSE:2330 | TWD | as of 2026-10-31 | 170a13bdc7e9 |  | None | None | valid |

### Valuation panel

- Listing: TWSE:2330 (TWD)
- Price: 2370.0000 as of 2026-10-31 21:58:02.728246+00:00
- Shares: 25932370067
- Market cap: 61459717058790.0000
- Total debt: 983513000000
- Cash: 3621894000000
- EV: 58821336058790.0000
- TTM revenue: 4440492429000.0 (end 2026-06-30)
- TTM net income: 2236752922000.0
- TTM FCF: 1143556366000.0
- Trailing P/E: 27.47720432341520821762002375
- EV/Sales: 13.24657951776681207353545969
- FCF yield: 0.01860659991171319567238458365
- Balance sheet as of: 2026-09-30
- Note: Descriptive evidence only. Trailing P/E is misleading for cyclical semiconductor companies.
- Note: No forward P/E, DCF, reverse valuation, or scenario weighting in Experiment 0a.
- Note: FCF = TTM operating cash flow − TTM capex. Provider FCF is not used.
- Note: The balance sheet is as of 2026-09-30 and the trailing figures run through 2026-06-30.

### Discrepancies

- revenue: passed=True class=None primary=4440492429000.0 cross=4440492000000 pct=9.661090675400856538652145960E-8 
- net_income: passed=True class=None primary=2236752922000.0 cross=2237088000000 pct=0.0001498055492425103893526957914 
- operating_cash_flow: passed=True class=None primary=2634679110000.0 cross=2634679000000 pct=4.175081495977701815838969475E-8 
- capex: passed=True class=None primary=1491122744000 cross=1491123000000 pct=1.716827142702344831244824739E-7 
- total_debt: passed=False class=DiscrepancyClass.unresolved primary=983513000000 cross=None pct=None No second document states this line. The first source was not compared with itself.
- cash: passed=False class=DiscrepancyClass.unresolved primary=3621894000000 cross=None pct=None No second document states this line. The first source was not compared with itself.
- shares_outstanding: passed=False class=DiscrepancyClass.unresolved primary=25932370067 cross=None pct=None No second document states this line. The first source was not compared with itself.
- price: passed=True class=None primary=2370.0000 cross=2370.0 pct=0 

### Findings

- TSMC home market is Taiwan (TWSE:2330). Filings are read with the Taiwan adapter.
- Home-market source: Taiwan public disclosure site and the Taiwan exchange company profile. The United States filing cabinet was not used.
- Equipment purchases were read from Taiwan's cash-flow statements and split into quarters.
- Cash was read from Taiwan's balance sheet for 2026Q2.
- Company quarterly report was downloaded and read as the separate document.
- Debt was taken from the company report.
- Cash on the later date comes from the company report. An older home-market figure does not stand in for it.
- On 2026-06-30, the company report and the home-market filing both state cash of 3134218000000. The latest figure, on 2026-09-30, does not have a second document.
- TSMC failed field validity (9/12)

## Experiment findings

- Experiment 0a only. No agents, no LLM calls, no portfolio, no screening.
- Raw artifacts stored under C:\Users\ahmet\Documents\PythonProjects\Epilith\data\raw.
