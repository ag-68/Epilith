# Experiment 0a: Data Feasibility Spec

> Scope: **only this experiment**. Do not build agents, LLM calls, portfolio, screening, or anything in `roadmap.md`. Research aid, not financial advice.

## 1. Question

For NVDA, ASML and TSMC, can we programmatically obtain a small set of financial and market facts, understand exactly what each number means, identify its source and period, reproduce derived metrics, and **detect discrepancies rather than silently hiding them**?

- Yes → begin 0b (see `roadmap.md`).
- No → fix the data layer first. Do not build 0b just because an API returned data.

## 2. Test companies

| Ticker | Region | Accounting | Reporting currency | Valuation listing (basis) |
|---|---|---|---|---|
| NVDA | US | US GAAP | USD | NASDAQ:NVDA (USD) |
| ASML | Europe | IFRS | EUR | Euronext Amsterdam (EUR) |
| TSMC | Asia | IFRS (TWD reporting) | TWD | Taiwan primary listing (TWD) |

Geographic diversity is deliberate: it tests GAAP vs IFRS, currencies, fiscal calendars, listings, ADRs, and reporting units.

Use the **local primary listing** as the valuation basis. Never mix it with the ADR or the other listing. If ADR data is ever collected, store the ADR ratio, ADR currency, FX rate, and FX date as separate facts.

## 3. Data contract: 12 required fields per company

| # | Field | Kind | Period rule |
|---|---|---|---|
| 1 | Revenue | flow | TTM (sum of last 4 reported quarters) |
| 2 | Operating income | flow | TTM |
| 3 | Net income (attributable to shareholders) | flow | TTM |
| 4 | Operating cash flow | flow | TTM |
| 5 | Capex | flow | TTM |
| 6 | Total debt | balance sheet | latest reported quarter-end |
| 7 | Cash and equivalents | balance sheet | latest reported quarter-end |
| 8 | Shares outstanding | balance sheet | latest reported period-end |
| 9 | Current price | market | with as-of timestamp |
| 10 | Reporting currency | metadata | n/a |
| 11 | Fiscal period (latest quarter and latest fiscal year labels and end dates) | metadata | n/a |
| 12 | Listing/exchange | metadata | n/a |

Notes:
- Fields 10-12 will almost always pass, so "11 of 12" effectively means **at most one failure among the 9 real facts**. Don't read the threshold as looser than it is.
- Flow facts require the **four individual quarters** to be collected and stored, plus the latest fiscal-year figure as a secondary cross-check. Quarterly facts are therefore required, not optional.
- Each quarterly fact keeps its own provenance (type `reported`). Each **TTM value is itself a derived fact**, marked `computed`, with its formula and inputs recorded:

```text
type: computed
formula: sum(latest_4_reported_quarters)
source_ids: [Q1_fact_id, Q2_fact_id, Q3_fact_id, Q4_fact_id]
```

- FCF is **computed**: `FCF = Operating cash flow − Capex` (TTM). Never accept a provider's FCF. Its inputs are the TTM fact IDs.
- Shares outstanding is point-in-time: the latest reported period-end figure with `as_of_date`.
- The latest annual figures are kept as a secondary reference/cross-check dataset, not as the primary valuation input.

### Metadata required on every numeric fact

```text
fact_id, metric, value, unit, currency,
period_type (annual | quarterly | TTM | point_in_time),
period_start_date (flows only), period_end_date (flows) or as_of_date (balance sheet),
listing, definition, source_id, source_date, retrieved_at, content_hash
```

### Price fact (additionally)

```text
price, currency, listing, as_of_timestamp, market_status
```

Never call a price "current" without knowing what moment it represents.

## 4. Definitions (store the definition text with each fact)

Do not assume identical metric names mean identical accounting definitions.

- **Debt:** state exactly what is included: current debt, long-term debt, and whether lease liabilities are included. Use one consistent policy across companies and document any forced deviation. Record the alternative (with/without leases) as a second fact if it differs materially.
- **Capex:** state exactly which cash-flow lines are included (e.g. purchases of property, plant and equipment; capitalized development costs; intangibles). IFRS and US GAAP treat some items differently.
- **Shares:** state basic vs diluted, and period-end vs weighted-average. For market cap use **period-end shares outstanding**, and document it.
- **Net income:** attributable to shareholders of the parent.
- **Cash:** state whether short-term investments/marketable securities are included. Default: cash and cash equivalents only; record short-term investments as a separate fact if reported.

## 5. Valuation panel (Python only)

Compute in one consistent listing, currency, share representation, and set of periods:

```text
Market cap      = price × shares outstanding
Enterprise value = market cap + total debt − cash
Trailing P/E    = market cap / TTM net income
EV/Sales        = EV / TTM revenue
FCF yield       = TTM FCF / market cap
```

Rules:
- Every input is dated. The panel reports its inputs' dates (price timestamp, TTM end date, balance-sheet as-of date).
- Do not mix current price with stale annual figures, or TTM with annual, without documenting it.
- No forward P/E, no DCF, no reverse valuation, no probability-weighted scenarios in 0a.
- The panel is **descriptive evidence, not a verdict**. Trailing P/E is especially misleading for cyclical semiconductor companies at peaks and troughs.

## 6. Sources

Prefer primary or structured sources:
- SEC EDGAR / XBRL (US filers; check what ASML and TSMC file there).
- Company investor-relations releases and official annual/quarterly reports.
- A reliable market-price provider.
- OpenBB only as an optional abstraction layer. It is not the architecture and doesn't guarantee data availability.

Keep provider-specific code isolated behind a small interface so providers are swappable.

**Cross-check independence:** a cross-check must come from a **different origin** than the primary value. Two values from the same XBRL feed, or the same aggregator, do not count. Acceptable examples: primary from XBRL vs cross-check from the company's IR release/annual report; price from provider A vs provider B.

## 7. Raw data and snapshots

Every external fetch stores:

```text
raw artifact, metadata, retrieved_at, source, content_hash
```

- Hash the **actual stored raw bytes**, not a later re-fetch.
- Never overwrite historical raw snapshots.
- Web pages change between fetches, so always keep the raw copy.

## 8. Pass/fail criteria (fixed before looking at results)

### Field validity, per company: at least 11 of 12 valid

A field is valid only if: (1) the value was obtained; (2) unit, currency, period/as-of, and listing are known; (3) the source is recorded; (4) it passes validation.

### The home-market filing is the figure kept

The regulator's filing (SEC EDGAR for US stocks, the European filing library, the Taiwan disclosure site) is the
source of truth. A figure stated there, with unit, currency, period, and provenance, is **valid** on its own.
A company's own release can **confirm** it, **explain** a difference, or **dispute** it. It never decides validity.
When the company's release is newer than the filing, the filing is still the figure kept; the newer figure is noted.

Every field records a `provenance` (authority, company, market) and a `confirmation`:

```text
confirmed    second document states the same figure within tolerance
explained    second document differs for a documented reason (period, rules, unit, listing, timing)
disputed     second document differs and nobody has explained why   -> listed in findings, figure still kept
unconfirmed  no second document states this line
```

### Cross-check on 8 fields (strengthens, does not qualify)

```text
Revenue (TTM), Net income (TTM), Operating cash flow (TTM), Capex (TTM),
Total debt, Cash, Shares outstanding, Price
```

- Tolerance: **≤1% difference**, unless a documented currency, unit, period, listing, definition, or timing difference explains it.
- Cross-check method for TTM values: compare against an independent computation (e.g. IR-release quarterly figures summed, or annual figure + current YTD − prior-year YTD) from a different origin.
- A second reading of the same period and the same calculation, within 1%, confirms a line.
- Each market keeps its own accounting rules. When the company report uses different rules for the same year, the home-market figure is the one kept and the company figure is recorded beside it. That difference does not fail the line.
- When the home market publishes a year and not four quarters, that year is the figure kept. A twelve-month total built by canceling the newest half is not used as confirmation.
- Balance-sheet fields use the newest date that two publishers state. A later date that only one document states is noted and does not replace the confirmed date.
- The United States filing cabinet is not a second reading for a company whose home market is elsewhere.
- If no second document exists, the field is **valid but unconfirmed**. The report counts confirmed fields separately
  so a reader can see how much of the sheet rests on one document.
- A figure that only the company's release states (the filing did not) is valid, marked `company`, and named in findings.
- Operating income has no cross-check but still requires primary-source provenance.

### Discrepancies

Never silently reconcile. Classify every discrepancy as one of:

```text
currency | unit | period | listing/ADR | accounting-definition | timing | source error | unresolved
```

`unresolved` = `disputed` on the field and a line in findings. The home-market figure is still the one kept.

### Overall

0a passes only if **all three companies** meet the threshold. A successful API call is not validation.

## 9. Outputs

1. **Validation table:**

```text
Company | Metric | Value | Unit | Currency | Period/As-of | Source | Cross-check source | Cross-check value | Difference | Status
```

2. **Per-company summary:** `NVDA: X/12 valid`, `ASML: X/12 valid`, `TSMC: X/12 valid`.
3. **Discrepancy report** with classification and explanation.
4. **Valuation panel** per company with input dates.
5. **Findings note:** what broke, what was hard, what the schema had to change. This drives the next architecture decision.

## 10. Known data traps

- **TSMC:** TWD reporting; Taiwan listing vs US ADR; ADR ratio; different price/share representations.
- **ASML:** EUR/IFRS; Euronext vs Nasdaq listing; capitalized development costs.
- **All:** millions vs billions; quarterly vs annual; fiscal vs calendar year; restatements; basic vs diluted; weighted-average vs period-end shares; debt/lease definitions; capex definitions; currency conversions; stale prices and timestamps.

## 11. Repository layout (0a only)

```text
ai-investment-research/
├── README.md
├── requirements.txt
├── .env.example
├── .cursorrules            # copy the block in section 13
├── docs/
│   ├── exp0a.md            # this file
│   └── roadmap.md
├── config/
│   └── companies.yaml
├── data/
│   ├── raw/
│   ├── normalized/
│   └── snapshots/
├── src/
│   ├── data/               # ingestion, market_data, financial_data, normalization
│   ├── validation/         # data_quality.py
│   └── valuation/          # multiples.py
├── experiments/exp0a/
└── tests/
```

Do **not** create `agents/`, `research/`, `knowledge/`, `decision_log/`, `graph/` yet. Avoid naming any package `logging` (shadows the standard library).

Stack: Python, Pydantic, Pandas, JSON/SQLite, Git, simple API clients. No LangGraph, graph DB, or vector/RAG.

## 12. Implementation sequence

1. Create repo and Python environment.
2. Add this spec and `companies.yaml`.
3. Implement Pydantic models: `Company`, `FinancialFact`, `MarketFact`, `Source`, `FinancialSnapshot`.
4. Implement **NVDA** ingestion only (four quarters + latest fiscal year + balance sheet + price).
5. Validate NVDA against primary company-reported information; produce its report.
6. Add **ASML**. Fix the generic model for EUR/IFRS/listing differences.
7. Add **TSMC**. Fix the generic model for TWD/ADR/listing differences.
8. Unit tests for unit, currency, period, and listing handling, and for the valuation formulas.
9. Run the full 0a validation and produce the outputs in section 9.
10. **Stop.** Review results before starting 0b.

## 13. Cursor rules (copy into `.cursorrules`)

```text
1. Implement Experiment 0a first; follow docs/exp0a.md.
2. Do not implement agents or LLM calls before 0a passes.
3. Do not introduce LangGraph, a graph database, or vector/RAG infrastructure.
4. Do not implement trading or request trading permissions.
5. Keep provider-specific code isolated behind an interface.
6. Use Pydantic and type hints.
7. Store raw artifacts with metadata and content hashes; never overwrite snapshots.
8. Never let LLM-generated numbers become authoritative facts.
9. Fix generic data-model problems rather than adding company-specific hacks.
10. Do not expand scope without a demonstrated failure.
```
