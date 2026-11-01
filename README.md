# Epilith

Recommendation-only investment research for AI infrastructure. It never trades.

Experiment 0a (data feasibility for NVDA, ASML, and TSMC) has passed. The repository is now in **Experiment 0b**: one research memo for one company, built from validated facts and fixed sections of the company's own filings, with quote checks in Python and an independent red team. See `docs/exp0a.md`, `docs/exp0b.md`, and `docs/roadmap.md`.

Research aid, not financial advice.

## Phases

| Phase | Status | What |
|---|---|---|
| **0a. Data feasibility** | Passed | 12 facts × NVDA, ASML, TSMC. Provenance, TTM from four quarters, independent cross-checks, discrepancy classification, descriptive valuation panel. |
| **0b. First research memo** | In progress | Evidence extraction, analyst, red team, immutable decision log. First live NVIDIA memo written. Local page to look a company up. |
| **1. Multi-agent ablation** | Later | Keep extra agents only if they improve evaluation. |
| **2. AI-infra dependency map** | Later | Hand-curated YAML/JSON. LLMs may propose edits, never own the map. |
| **3. Portfolio context** | Later | IBKR read-only + Nordnet CSV. No auto-sizing. |
| **4. Idea generation** | Later | Universe → screen → research. Trailing screens favor past winners; say so. |
| **5. Event-driven monitoring** | Later | Scheduled re-eval, not continuous polling. |

Locked rules: Python owns numbers; LLMs do not; every extra component must earn its place.

## Current status

A stock is routed by home market before any filing is downloaded. The United States filing cabinet is the home source only for United States stocks. Each market keeps its own accounting rules. The regulator's filing is the figure kept and is valid on its own. The company's own release can confirm it, explain a difference, or dispute it; it never decides validity. Each field carries a provenance (authority, company, market) and a confirmation mark, and the report counts confirmed fields separately.

Experiment 0a passes: each company has at least 11 of 12 fields valid. The table below is from the run of 31 Oct 2026, under the earlier rule that required a second document; under the current rule NVIDIA scores 12/12 with 7 confirmed.

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

Set `SEC_USER_AGENT` in `.env` to a string that includes a real contact mailbox. SEC EDGAR rejects anonymous clients, and it also blocks no-reply addresses (such as `@users.noreply.github.com`) as "undeclared automated tool", from any machine.
Set `GROQ_API_KEY` for Experiment 0b. In cloud agents it is a Runtime Secret with the same name.

## Run Experiment 0a

```powershell
$env:PYTHONPATH = "src"
python experiments\exp0a\run.py
```

Reports land in `experiments/exp0a/output/`. Raw fetches are hashed and stored under `data/raw/`; they are never overwritten.
The latest passing report is committed, so 0b can run without refetching.

## Run Experiment 0b (current step)

Type the company. For a United States filer the data check, the address-book entry and the reading material
(newest 10-K, 10-Q and earnings release, cut by section heading) are all produced automatically:

```powershell
$env:PYTHONPATH = "src"
python experiments\exp0b\run.py NVIDIA
```

The memo and every intermediate artifact land under `data/research/NVDA/<run_id>/`. The decision log entry is written
under `data/decision_log/`. Record what you did afterwards with `--action <ENTRY_ID> watched "reason"`. Details in `docs/exp0b.md`.

## Open the local page

```powershell
$env:PYTHONPATH = "src"
pip install -r requirements.txt
python experiments\ui\run.py
```

Then open http://127.0.0.1:8765. Type a company name. Existing memos are listed; you can record watched / skipped / bought there. The page talks to the same runner as the command line and stays on this machine.

```powershell
pytest
```
