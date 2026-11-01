# Experiment 0b: First Research Memo

> Spec: `roadmap.md` section 4. This page is the runbook. Research aid, not financial advice.

## 1. Question

Given validated 0a facts and a handful of hand-picked source excerpts, can a model-written memo be produced where every
quote is verifiable, every number traces to a stored fact, the analyst never sees the user's portfolio, and a separate
model attacks the thesis before a person reads it?

## 2. Pipeline

```text
0a report + normalized snapshot  ──►  FactSheet (Python)
sources/<TICKER>/*.txt + sources.yaml ──►  SourceBundle (hashed)
        │
        ▼
evidence extraction (LLM)  ──►  quote verification (Python)  ──►  EvidenceSet
        │
        ▼
analyst (LLM, model A)  ──►  Thesis + structured assumptions
        │
        ▼
red team (LLM, model B; gets structure, facts, evidence, sources; not the memo prose)
        │
        ▼
numbers audit (Python)  ──►  memo.md  ──►  decision log entry (append-only)
```

Code: `src/llm/` (provider interface, Groq, scripted stand-in, call recorder), `src/research/`, `src/decision_log/`,
`experiments/exp0b/run.py`.

## 3. Guardrails and where they live

| Rule | Enforcement |
|---|---|
| Python owns numbers | `FactSheet` is built from the 0a report. The memo's facts table and valuation panel are rendered from it. Model prose is scanned and any figure that does not match a fact is listed in Appendix D for a human check. |
| Quotes must exist | `research/evidence.py` checks each `exact_quote` against the stored source bytes after whitespace and quote-mark normalization. Failures are kept, flagged, and excluded from the analyst's input. |
| Context isolation | `ResearchPipeline.run(sheet, bundle)` has no portfolio parameter. Tests assert the analyst prompt never contains the word. |
| Red team independence | Different model family by config (`config/llm.yaml`). It receives the structured thesis, not the memo prose. Output is logged, not merged. |
| Untrusted text | Sources are wrapped in `<<<SOURCE>>>` delimiters and the system prompt says to treat them as data. |
| Provenance | Each run writes `fact_sheet.json`, `source_bundle.json`, `evidence.json`, `thesis.json`, `red_team.json`, `memo.md`, `run.json`, and one file per LLM call with request and response hashes, under `data/research/<TICKER>/<run_id>/`. Nothing is overwritten. |
| Decision log | `data/decision_log/entries/<id>.json` written once. User actions go to `data/decision_log/actions/`, never into the entry. |

## 4. Run

1. Put the key in place. Locally: `GROQ_API_KEY=...` in `.env`. Cloud agents: a Runtime Secret with the same name.
2. Add excerpts under `experiments/exp0b/sources/NVDA/` and list them in `sources.yaml` (format in `sources/README.md`).
3. Run:

```powershell
$env:PYTHONPATH = "src"
python experiments\exp0b\run.py --company NVDA
```

4. Read the memo, then record what you did:

```powershell
python experiments\exp0b\run.py --action <ENTRY_ID> watched "reason"
```

Actions: `bought | skipped | watched`. Each call appends a new record.

## 5. What to look at after the first run

- Appendix C: claims that failed the quote check. Many failures mean the extraction prompt or the source formatting needs work.
- Appendix D: figures the model introduced. Decide whether each is a derived number it labeled, or an invention.
- Spot-check three verified claims by hand: does the quote actually support the claim?
- Compare the red team's attacks with the three "most likely wrong" assumptions. Overlap is a good sign; none is a warning.
- Note what the schema had to change. That drives Experiment 1.

## 6. Out of scope

No RAG, no retrieval index, no whole filings, no portfolio data, no position sizing, no trading. One company at a time.
