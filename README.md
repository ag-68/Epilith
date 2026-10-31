# Epilith

Recommendation-only investment research for AI infrastructure. It never trades.

This repository is in **Experiment 0a**: prove that a small set of financial and market facts can be fetched, defined, sourced, reproduced, and cross-checked for NVDA, ASML, and TSMC. Agents, memos, and portfolio logic wait until 0a passes. See `docs/exp0a.md` and `docs/roadmap.md`.

Research aid, not financial advice.

## Phases

| Phase | Status | What |
|---|---|---|
| **0a. Data feasibility** | In progress | 12 facts × NVDA, ASML, TSMC. Provenance, TTM from four quarters, independent cross-checks, discrepancy classification, descriptive valuation panel. |
| **0b. First research memo** | Blocked on 0a | Evidence extraction, analyst, red team, immutable decision log. No RAG. |
| **1. Multi-agent ablation** | Later | Keep extra agents only if they improve evaluation. |
| **2. AI-infra dependency map** | Later | Hand-curated YAML/JSON. LLMs may propose edits, never own the map. |
| **3. Portfolio context** | Later | IBKR read-only + Nordnet CSV. No auto-sizing. |
| **4. Idea generation** | Later | Universe → screen → research. Trailing screens favor past winners; say so. |
| **5. Event-driven monitoring** | Later | Scheduled re-eval, not continuous polling. |

Locked rules: Python owns numbers; LLMs do not; every extra component must earn its place.

## Current status

A stock is routed by home market before any filing is downloaded. The United States filing cabinet is the home source only for United States stocks. Each market keeps its own accounting rules. The home-market figure is the one kept. The company report confirms it when the same period and the same calculation agree within 1%. A different set of rules is recorded beside it and does not fail the line.

Experiment 0a passes: each company has at least 11 of 12 fields valid.

| Company | Valid fields | What is still open |
|---|---|---|
| NVIDIA | 11/12 | The last twelve months match the company's own quarterly releases. The release does not state how many shares were outstanding, so that line is the one miss. |
| ASML | 11/12 | The figure kept is the European full year 2025. Sales and equipment purchases match the company report exactly. Profit and cash from the business are the European figures; the company report, written under US rules, prints different amounts for that same year. Cash on 31 Dec 2025 matches; June cash has no second document. Long-term borrowings match; the portion due within a year is only in the European report. The share count is the one miss. |
| TSMC | 11/12 | Sales, profit, cash from the business, and equipment purchases match. Cash is the 30 Jun 2026 figure both documents state; September cash has no second document. The share count matches the company's capital stock divided by the exchange's printed face amount. Borrowings are the one miss. |

## 0a sequence

1. Scaffold (this repo)
2. Pydantic models + `config/companies.yaml`
3. **NVDA** ingestion and report
4. ASML (EUR / IFRS / listing)
5. TSMC (TWD / ADR / listing)
6. Unit tests for unit, currency, period, listing, valuation
7. Full three-company validation
8. Stop and review before 0b

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `SEC_USER_AGENT` in `.env` to a string that includes a contact email. SEC EDGAR rejects anonymous clients.

## Run NVDA (current step)

```powershell
$env:PYTHONPATH = "src"
python experiments\exp0a\run.py --company NVDA
```

Reports land in `experiments/exp0a/output/`. Raw fetches are hashed and stored under `data/raw/`; they are never overwritten.

```powershell
pytest
```
