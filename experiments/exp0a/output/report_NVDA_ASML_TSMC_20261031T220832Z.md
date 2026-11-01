# Experiment 0a report

Generated at: 2026-10-31T22:08:32.201095+00:00
Overall: PASS

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
| price | 204.64 | USD | USD | 2026-10-30T00:00:00+00:00 | 942f66d2cc44 | 0db5e59e8ac9 | 204.63999938964844 | 6.1035156E-7 | valid |
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

## ASML: 11/12 valid

| Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status |
|---|---|---|---|---|---|---|---|---|---|
| revenue | 32667300000.0 | EUR | EUR | annual 2025-01-01 to 2025-12-31 | 764526c6d9fb | 02ef40cbb531 | 32667300000.0 | 0.0 | valid |
| operating_income | 12054000000.0 | EUR | EUR | annual 2025-01-01 to 2025-12-31 | 764526c6d9fb |  | None | None | valid |
| net_income | 10213000000.0 | EUR | EUR | annual 2025-01-01 to 2025-12-31 | 764526c6d9fb | 02ef40cbb531 | 9609400000.0 | 603600000.0 | valid |
| operating_cash_flow | 13826500000.0 | EUR | EUR | annual 2025-01-01 to 2025-12-31 | 764526c6d9fb | 02ef40cbb531 | 12658500000.0 | 1168000000.0 | valid |
| capex | 1573600000.0 | EUR | EUR | annual 2025-01-01 to 2025-12-31 | 764526c6d9fb | 02ef40cbb531 | 1573600000.0 | 0.0 | valid |
| total_debt | 4390900000.0 | EUR | EUR | as of 2025-12-31 | 764526c6d9fb | 02ef40cbb531 | 2709000000.0 | 1681900000.0 | valid |
| cash | 12916000000.0 | EUR | EUR | as of 2025-12-31 | 764526c6d9fb | 02ef40cbb531 | 12916000000.0 | 0.0 | valid |
| shares_outstanding | 385400000.0 | shares | None | as of 2025-12-31 | 764526c6d9fb |  | None | None | failed |
| price | 1412.800048828125 | EUR | EUR | 2026-10-30T08:00:00+00:00 | e278f4c77fb4 | be2ed22a93c2 | 1412.80 | 0.000048828125 | valid |
| reporting_currency | 1 | EUR | EUR | as of 2026-06-28 | 02ef40cbb531 |  | None | None | valid |
| fiscal_period | 739795 | date_ordinal | None | as of 2026-06-28 | 02ef40cbb531 |  | None | None | valid |
| listing | 1 | EURONEXT:ASML | EUR | as of 2026-06-28 | 02ef40cbb531 |  | None | None | valid |

### Valuation panel

- Listing: EURONEXT:ASML (EUR)
- Price: 1412.800048828125 as of 2026-10-30 08:00:00+00:00
- Shares: 385400000.0
- Market cap: 544493138818.3593750000000
- Total debt: 4390900000.0
- Cash: 12916000000.0
- EV: 535968038818.3593750000000
- TTM revenue: 32667300000.0 (end 2025-12-31)
- TTM net income: 10213000000.0
- TTM FCF: 12252900000.0
- Trailing P/E: 53.31373140295303779496719867
- EV/Sales: 16.40686676947159315278581334
- FCF yield: 0.02250331386469043459325120343
- Balance sheet as of: 2025-12-31
- Note: Descriptive evidence only. Trailing P/E is misleading for cyclical semiconductor companies.
- Note: No forward P/E, DCF, reverse valuation, or scenario weighting in Experiment 0a.
- Note: The home-market filing publishes a full year, and the quarterly statement uses different accounting rules. Valuation uses the home-market full year.
- Note: FCF = TTM operating cash flow − TTM capex. Provider FCF is not used.
- Note: Market cap mixes price as of 2026-10-30T08:00:00+00:00 with shares as of 2025-12-31.

### Discrepancies

- revenue: passed=True class=None primary=32667300000.0 cross=32667300000.0 pct=0 
- net_income: passed=True class=DiscrepancyClass.accounting_definition primary=10213000000.0 cross=9609400000.0 pct=0.05910114559874669538823068638 Same year, different accounting rules. The home-market figure 10213000000.0 is the one kept. The company report states 9609400000.0.
- operating_cash_flow: passed=True class=DiscrepancyClass.accounting_definition primary=13826500000.0 cross=12658500000.0 pct=0.08447546378331464940512783423 Same year, different accounting rules. The home-market figure 13826500000.0 is the one kept. The company report states 12658500000.0.
- capex: passed=True class=None primary=1573600000.0 cross=1573600000.0 pct=0 
- total_debt: passed=True class=DiscrepancyClass.accounting_definition primary=4390900000.0 cross=2709000000.0 pct=None Long-term borrowings of 2709000000.0 on 2025-12-31 match the company report. The portion due within a year, 1681900000.0, is only in the home-market report. The total kept is the home-market total.
- cash: passed=True class=None primary=12916000000.0 cross=12916000000.0 pct=0 
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
- net income for the year ended 2025-12-31 is 10213000000.0 under the home market's accounting rules. The company report states 9609400000.0 for that same year under its own rules. The home-market figure is the one kept.
- operating cash flow for the year ended 2025-12-31 is 13826500000.0 under the home market's accounting rules. The company report states 12658500000.0 for that same year under its own rules. The home-market figure is the one kept.
- A later statement shows cash of 6671900000.0 on 2026-06-28. No second document states that later figure. The confirmed cash is the 2025-12-31 figure both documents state.
- A later statement shows borrowings of 1984400000.0 on 2026-06-28. No second document states that later figure. The confirmed borrowings is the 2025-12-31 figure both documents state.

## TSMC: 11/12 valid

| Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status |
|---|---|---|---|---|---|---|---|---|---|
| revenue | 4440492429000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 170a13bdc7e9 | a55d6aca73ba | 4440492000000 | 429000.0 | valid |
| operating_income | 2491156024000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | f0e27feb8ef8 |  | None | None | valid |
| net_income | 2236752922000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 6efd7856c4ec | a55d6aca73ba | 2237088000000 | 335078000.0 | valid |
| operating_cash_flow | 2634679110000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 648090bab9ac | a55d6aca73ba | 2634679000000 | 110000.0 | valid |
| capex | 1491122744000 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 3be049c1fef7 | a55d6aca73ba | 1491123000000 | 256000 | valid |
| total_debt | 983513000000 | TWD | TWD | as of 2026-09-30 | 05cf01194e35 |  | None | None | failed |
| cash | 3134218213000 | TWD | TWD | as of 2026-06-30 | 8b2b82c41a1b | a55d6aca73ba | 3134218000000 | 213000 | valid |
| shares_outstanding | 25932370067 | shares | None | as of 2026-10-31 | beb7de039626 | 05cf01194e35 | 2.593240E+10 | 29933 | valid |
| price | 2370.0000 | TWD | TWD | 2026-10-31T22:08:32.049228+00:00 | ec6ba12e2765 | 49600e13f308 | 2370.0 | 0.0000 | valid |
| reporting_currency | 1 | TWD | TWD | as of 2026-10-31 | 170a13bdc7e9 |  | None | None | valid |
| fiscal_period | 739920 | date_ordinal | None | as of 2026-10-31 | 170a13bdc7e9 |  | None | None | valid |
| listing | 1 | TWSE:2330 | TWD | as of 2026-10-31 | 170a13bdc7e9 |  | None | None | valid |

### Valuation panel

- Listing: TWSE:2330 (TWD)
- Price: 2370.0000 as of 2026-10-31 22:08:32.049228+00:00
- Shares: 25932370067
- Market cap: 61459717058790.0000
- Total debt: 983513000000
- Cash: 3134218213000
- EV: 59309011845790.0000
- TTM revenue: 4440492429000.0 (end 2026-06-30)
- TTM net income: 2236752922000.0
- TTM FCF: 1143556366000.0
- Trailing P/E: 27.47720432341520821762002375
- EV/Sales: 13.35640422635432895588886950
- FCF yield: 0.01860659991171319567238458365
- Balance sheet as of: 2026-06-30
- Note: Descriptive evidence only. Trailing P/E is misleading for cyclical semiconductor companies.
- Note: No forward P/E, DCF, reverse valuation, or scenario weighting in Experiment 0a.
- Note: FCF = TTM operating cash flow − TTM capex. Provider FCF is not used.
- Note: EV mixes debt as of 2026-09-30 with cash as of 2026-06-30.

### Discrepancies

- revenue: passed=True class=None primary=4440492429000.0 cross=4440492000000 pct=9.661090675400856538652145960E-8 
- net_income: passed=True class=None primary=2236752922000.0 cross=2237088000000 pct=0.0001498055492425103893526957914 
- operating_cash_flow: passed=True class=None primary=2634679110000.0 cross=2634679000000 pct=4.175081495977701815838969475E-8 
- capex: passed=True class=None primary=1491122744000 cross=1491123000000 pct=1.716827142702344831244824739E-7 
- total_debt: passed=False class=DiscrepancyClass.unresolved primary=983513000000 cross=None pct=None No second document states this line. The first source was not compared with itself.
- cash: passed=True class=None primary=3134218213000 cross=3134218000000 pct=6.795953106153429145426256892E-8 
- shares_outstanding: passed=True class=None primary=25932370067 cross=2.593240E+10 pct=0.000001154271665978227149290974215 
- price: passed=True class=None primary=2370.0000 cross=2370.0 pct=0 

### Findings

- TSMC home market is Taiwan (TWSE:2330). Filings are read with the Taiwan adapter.
- Home-market source: Taiwan public disclosure site and the Taiwan exchange company profile. The United States filing cabinet was not used.
- Equipment purchases were read from Taiwan's cash-flow statements and split into quarters.
- Cash was read from Taiwan's balance sheet for 2026Q2.
- Company quarterly report was downloaded and read as the separate document.
- Debt was taken from the company report.
- The share count was checked against the company's capital stock dated 2026-09-30, divided by the face amount printed on the exchange profile dated 2026-10-31.
- A later statement shows cash of 3621894000000 on 2026-09-30. No second document states that later figure. The confirmed cash is the 2026-06-30 figure both documents state.

## Experiment findings

- Experiment 0a only. No agents, no LLM calls, no portfolio, no screening.
- Raw artifacts stored under C:\Users\ahmet\Documents\PythonProjects\Epilith\data\raw.
