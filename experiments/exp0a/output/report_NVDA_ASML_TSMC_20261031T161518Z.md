# Experiment 0a report

Generated at: 2026-10-31T16:15:18.984485+00:00
Overall: FAIL

## NVDA: 11/12 valid

| Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status |
|---|---|---|---|---|---|---|---|---|---|
| revenue | 302969000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 302948000000.0 | 21000000.0 | valid |
| operating_income | 197579000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 |  | None | None | valid |
| net_income | 192879000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 192879000000 | 0 | valid |
| operating_cash_flow | 134360000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 134360000000 | 0 | valid |
| capex | 7354000000 | USD | USD | TTM 2025-07-28 to 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 7354000000 | 0 | valid |
| total_debt | 33366000000 | USD | USD | as of 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 33366000000 | 0 | valid |
| cash | 22443000000 | USD | USD | as of 2026-07-26 | 19ef503a5770 | a8247969d0f0 | 22443000000 | 0 | valid |
| shares_outstanding | 24100000000 | shares | None | as of 2026-08-21 | 19ef503a5770 |  | None | None | failed |
| price | 204.64 | USD | USD | 2026-10-30T00:00:00+00:00 | 942f66d2cc44 | 8a5e6bab68fe | 204.63999938964844 | 6.1035156E-7 | valid |
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

- revenue: passed=True class=None primary=302969000000 cross=302948000000.0 pct=0.00006931402222669646069399839588 
- net_income: passed=True class=None primary=192879000000 cross=192879000000 pct=0 
- operating_cash_flow: passed=True class=None primary=134360000000 cross=134360000000 pct=0 
- capex: passed=True class=None primary=7354000000 cross=7354000000 pct=0 
- total_debt: passed=True class=None primary=33366000000 cross=33366000000 pct=0 
- cash: passed=True class=None primary=22443000000 cross=22443000000 pct=0 
- shares_outstanding: passed=False class=DiscrepancyClass.unresolved primary=24100000000 cross=None pct=None No independent IR/press-release figure for this balance-sheet item.
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

## ASML: 0/12 valid

| Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status |
|---|---|---|---|---|---|---|---|---|---|
| revenue | None | None | None | None |  |  | None | None | missing |
| operating_income | None | None | None | None |  |  | None | None | missing |
| net_income | None | None | None | None |  |  | None | None | missing |
| operating_cash_flow | None | None | None | None |  |  | None | None | missing |
| capex | None | None | None | None |  |  | None | None | missing |
| total_debt | None | None | None | None |  |  | None | None | missing |
| cash | None | None | None | None |  |  | None | None | missing |
| shares_outstanding | None | None | None | None |  |  | None | None | missing |
| price | 1412.800048828125 | EUR | EUR | 2026-10-30T08:00:00+00:00 | e1ef86994204 |  | None | None | failed |
| reporting_currency | None | None | None | None |  |  | None | None | missing |
| fiscal_period | None | None | None | None |  |  | None | None | missing |
| listing | None | None | None | None |  |  | None | None | missing |

### Valuation panel

- Listing: EURONEXT:ASML (EUR)
- Price: 1412.800048828125 as of 2026-10-30 08:00:00+00:00
- Shares: None
- Market cap: None
- Total debt: None
- Cash: None
- EV: None
- TTM revenue: None (end None)
- TTM net income: None
- TTM FCF: None
- Trailing P/E: None
- EV/Sales: None
- FCF yield: None
- Balance sheet as of: None
- Note: Descriptive evidence only. Trailing P/E is misleading for cyclical semiconductor companies.
- Note: No forward P/E, DCF, reverse valuation, or scenario weighting in Experiment 0a.

### Discrepancies

- revenue: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None Earnings release did not yield an independent figure for this metric.
- net_income: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None Earnings release did not yield an independent figure for this metric.
- operating_cash_flow: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None Earnings release did not yield an independent figure for this metric.
- capex: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None Earnings release did not yield an independent figure for this metric.
- total_debt: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None No independent IR/press-release figure for this balance-sheet item.
- cash: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None No independent IR/press-release figure for this balance-sheet item.
- shares_outstanding: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None No independent IR/press-release figure for this balance-sheet item.
- price: passed=False class=DiscrepancyClass.unresolved primary=1412.800048828125 cross=None pct=None No second, independent price source for this listing yet. A second copy of the same website does not count.

### Findings

- ASML home market is Europe (EURONEXT:ASML). Filings are read with the Europe adapter.
- Home-market source: the public European electronic-report library. The United States filing cabinet was not used.
- European library search for 'ASML Holding N.V.' returned 5 package(s). That library holds electronic yearly reports. It did not return the last four quarters, so sales, profit, cash, debt, and the share count stay empty rather than being copied from the United States filing.
- IR release fetch failed for https://www.asml.com/en/news/press-releases/2026/q2-2026-financial-results: Client error '403 Forbidden' for url 'https://investor.asml.com/news-releases/news-release-details/q2-2026-financial-results'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403
- ASML failed field validity (0/12)

## TSMC: 5/12 valid

| Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status |
|---|---|---|---|---|---|---|---|---|---|
| revenue | 4440492429000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 170a13bdc7e9 | 39a56bb13756 | 2026 | 1270380247974.0 | failed |
| operating_income | 2491156024000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | f0e27feb8ef8 |  | None | None | valid |
| net_income | 2236752922000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 6efd7856c4ec |  | None | None | failed |
| operating_cash_flow | 2634679110000.0 | TWD | TWD | TTM 2025-07-01 to 2026-06-30 | 648090bab9ac |  | None | None | failed |
| capex | None | None | None | None |  |  | None | None | missing |
| total_debt | None | None | None | None |  |  | None | None | missing |
| cash | None | None | None | None |  |  | None | None | missing |
| shares_outstanding | 25932370067 | shares | None | as of 2026-10-30 | e54820b99038 |  | None | None | failed |
| price | 2370.0000 | TWD | TWD | 2026-10-31T16:15:14.763244+00:00 | 1e21675c6fd8 | b66733f1ea38 | 2370.0 | 0.0000 | valid |
| reporting_currency | 1 | TWD | TWD | as of 2026-10-30 | 170a13bdc7e9 |  | None | None | valid |
| fiscal_period | 739919 | date_ordinal | None | as of 2026-10-30 | 170a13bdc7e9 |  | None | None | valid |
| listing | 1 | TWSE:2330 | TWD | as of 2026-10-30 | 170a13bdc7e9 |  | None | None | valid |

### Valuation panel

- Listing: TWSE:2330 (TWD)
- Price: 2370.0000 as of 2026-10-31 16:15:14.763244+00:00
- Shares: 25932370067
- Market cap: 61459717058790.0000
- Total debt: None
- Cash: None
- EV: None
- TTM revenue: 4440492429000.0 (end 2026-06-30)
- TTM net income: 2236752922000.0
- TTM FCF: None
- Trailing P/E: 27.47720432341520821762002375
- EV/Sales: None
- FCF yield: None
- Balance sheet as of: None
- Note: Descriptive evidence only. Trailing P/E is misleading for cyclical semiconductor companies.
- Note: No forward P/E, DCF, reverse valuation, or scenario weighting in Experiment 0a.
- Note: Market cap mixes price as of 2026-10-31T16:15:14.763244+00:00 with shares as of 2026-10-30.

### Discrepancies

- revenue: passed=False class=DiscrepancyClass.unresolved primary=1270380250000.0 cross=2026 pct=0.9999999984052019070668014557 Latest-quarter XBRL value differs from the earnings release by more than 1%. Quote: Revenue 2026
- net_income: passed=False class=DiscrepancyClass.unresolved primary=2236752922000.0 cross=None pct=None Earnings release did not yield an independent figure for this metric.
- operating_cash_flow: passed=False class=DiscrepancyClass.unresolved primary=2634679110000.0 cross=None pct=None Earnings release did not yield an independent figure for this metric.
- capex: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None Earnings release did not yield an independent figure for this metric.
- total_debt: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None No independent IR/press-release figure for this balance-sheet item.
- cash: passed=False class=DiscrepancyClass.unresolved primary=None cross=None pct=None No independent IR/press-release figure for this balance-sheet item.
- shares_outstanding: passed=False class=DiscrepancyClass.unresolved primary=25932370067 cross=None pct=None No independent IR/press-release figure for this balance-sheet item.
- price: passed=True class=None primary=2370.0000 cross=2370.0 pct=0 

### Findings

- TSMC home market is Taiwan (TWSE:2330). Filings are read with the Taiwan adapter.
- Home-market source: Taiwan public disclosure site and the Taiwan exchange company profile. The United States filing cabinet was not used.
- Taiwan's machine-readable quarterly feed does not split out cash, borrowings, or equipment purchases. Those items stay empty rather than being guessed from a wider cash-flow total.
- TSMC failed field validity (5/12)

## Experiment findings

- Experiment 0a only. No agents, no LLM calls, no portfolio, no screening.
- Raw artifacts stored under C:\Users\ahmet\Documents\PythonProjects\Epilith\data\raw.
