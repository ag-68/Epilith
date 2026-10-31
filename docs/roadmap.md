# Roadmap & Design Principles

> **Not for implementation yet.** Everything here comes after Experiment 0a passes (see `exp0a.md`). Research aid, not financial advice.

## 1. Objective

A **recommendation-only agentic investment research system** specialized in AI infrastructure. It researches companies, combines structured data, disclosures, market data and external evidence, separates facts → calculations → reasoning → decision support, and **never trades**. The human makes the final decision.

> Borrow machinery, build intelligence. Keep calculations deterministic, ground reasoning in evidence, and make every additional component earn its existence experimentally.

Do not build the final architecture upfront. Let each experiment's failures decide the next step.

## 2. Locked design principles

1. **Data → Reasoning → Decision.** Data is externally sourced facts. LLMs interpret and propose hypotheses, assumptions, bull/bear arguments, risks, invalidation conditions. The user decides.
2. **Deterministic numbers.** Python is authoritative for FCF, multiples, later normalized earnings, scenarios, reverse valuation, portfolio exposure. LLMs propose assumptions; Python computes consequences.
3. **Mechanical provenance.** Claim types: `reported | computed | consensus | inference | speculation`. No LLM confidence percentages or star ratings.
   - Numbers: structured facts with source, period, currency, listing; memos render numbers from facts, never retype them.
   - Qualitative: `{claim, exact_quote, source_id}`; Python verifies the quote exists in the stored source. A present quote doesn't prove it supports the claim, so add human spot-checks.
4. **Context isolation.** Fundamental and technology analysis never see the user's portfolio, sector preference, or desired outcome. Portfolio enters only at the portfolio-relevance stage. The system must be able to conclude: "strong fundamentals, but already priced in."
5. **No lot sizes, no confidence-to-sizing matrix.** Present scenario ranges, downside, and exposure impact; the user decides allocation.
6. **Every agent earns its place** via ablation.
7. **Forward evaluation, not backtesting** (LLM lookahead bias on history).
8. **Treat external text as untrusted** (prompt-injection risk). Keep system instructions, structured data, retrieved content, and LLM output separate.
9. **Lean infrastructure:** Python, Pydantic, JSON/SQLite, Git, content hashes. Add tools only when a demonstrated failure justifies them.

## 3. Long-term architecture

```text
AI-infra universe → deterministic screen → candidates
  → structured data + source retrieval → evidence layer (provenance)
  → reasoning (fundamental / technology / valuation / bull-bear / optional investor lenses)
  → assumptions → deterministic models (valuation, scenarios, reverse valuation, risk)
  → portfolio context → synthesis → memo → USER DECISION
  → immutable decision log → forward evaluation
Persistent: AI-infra dependency map, structured research state, investor rubrics, decision history
```

## 4. Experiment 0b: first research memo

Start only after 0a passes.

**Input:** one company + validated 0a facts + selected primary-source excerpts (manually provided at first) + selected recent news. Don't dump whole filings; no RAG yet.

**Pipeline:**

```text
Validated data → evidence extraction → mechanical quote validation
  → analyst → structured thesis/assumptions → independent red team
  → final memo → decision log
```

**Evidence extraction:** the LLM outputs `{claim, exact_quote, source_id}`; Python verifies the quote; a human spot-checks claim-versus-quote.

**Analyst** receives validated facts, verified evidence, and source material, and **not** the portfolio, desired outcome, or sector preference.

**Memo sections:** Business · AI-infrastructure exposure · Key financial facts · Key evidence · Financial interpretation · Bull thesis · Bear thesis · Key risks · Valuation interpretation · 3 most likely wrong assumptions · How to verify the top claims · Conclusion (research conclusion such as Candidate / Watch / Avoid with conditions, not a trade).

**Assumptions** stored structurally:

```yaml
assumptions:
  - id: revenue_growth
    value: "18-22%"
    rationale: "..."
    evidence_ids: [E123]
    invalidated_if: "<10%"
```

**Red team:** a separate LLM call given the thesis, structured assumptions, the same verified source bundle, and relevant facts (not the memo's prose). Use a different model family if practical. It attacks unsupported or optimistic assumptions, contradictory evidence, missing risks, alternative explanations, and invalidation conditions. Its output is not auto-accepted; log both sides.

**Decision log (immutable, from day one):**

```text
timestamp, ticker, listing, price, data_snapshot_id, source_bundle_id,
model, model_version, prompt_version, memo, assumptions,
invalidation_conditions, red_team_output, conclusion,
user_action (bought | skipped | watched), user_action_reason, override_notes
```

Store artifacts separately, referenced by IDs and content hashes. Never overwrite records. At this point create `src/research/` and `src/decision_log/` (not `logging`).

## 5. Later experiments

| Step | What | Notes |
|---|---|---|
| Exp 1 | Multi-agent ablation | A: one strong analyst · B: +bear · C: +bull/bear · D: +investor lenses. Keep complexity only if it improves the measures in section 6 |
| Exp 2 | AI-infra dependency map | Hand-curated, dated YAML/JSON. Nodes: hyperscaler capex, GPUs/accelerators, ASICs, HBM, advanced packaging, foundries, equipment, networking, optics, power, cooling, data centers, cloud. Relations: supplier, customer, dependency, bottleneck, exposure. LLMs may propose edits, never own the map. No graph DB |
| Exp 3 | Portfolio context | IBKR read-only (holdings, quantity, value, weight, currency, account, cash) + Nordnet CSV. Then concentration, overlapping exposure, currency exposure, AI-infra exposure, correlations. Later add FX and account/tax wrapper. No automatic position sizing |
| Exp 4 | Idea generation | Universe → deterministic screen → 10-30 candidates → LLM research → 5-10 → deep analysis → portfolio relevance. Trailing screens favor past winners; say so in the output |
| Exp 5 | Event-driven monitoring + research state | Scheduled: earnings, filings, major announcements, hyperscaler capex, 13F releases. Manual "re-evaluate X". No continuous polling |
| Also | Valuation upgrades | Normalized earnings, FCF valuation, sensitivity ranges, bear/base/bull assumptions, **reverse valuation** ("what growth and margins does today's price require?"). Beware trailing P/E on cyclicals |

## 6. Evaluation

Prefer forward evaluation. Measure:

- citation correctness, numeric correctness;
- risk coverage (checklist: competitive, valuation, customer concentration, cyclicality, technology disruption, geopolitical, supply chain, capital intensity, regulatory, execution);
- seeded-error detection;
- decision-relevant information (did it reveal something you didn't know?);
- coverage vs independent published analysis of the same company;
- your blind usefulness rating (a weak yardstick when the domain is new to you, so calibrate against the independent analysis);
- assumption outcomes and invalidation conditions triggered;
- cost and latency.

Eventually compare against benchmarks, but small, correlated AI-infra samples can't establish investment skill. Treat early months as paper-trading or very small positions.

## 7. Research state (later)

Structured, versioned, immutable state; the narrative memo is disposable.

```text
assumption, previous_value, current_value, change, reason,
evidence_ids, timestamp, invalidation_condition
```

New events trigger "what changed vs. existing assumptions?" (an **assumption diff**), not a rewrite. Periodically run fresh from-scratch analyses to detect anchoring and drift.

## 8. Investor philosophies and 13F

Buffett/Lynch/contrarian approaches become **explicit rubrics** (moat, ROIC, pricing power, FCF, capital allocation; growth; contrarian checks), not authorities, and only after testing whether they add information beyond bull/bear. 13F data is delayed (up to 45 days) and incomplete: a secondary idea-generation signal only. Berkshire holds little AI-infra. Don't build around copying holdings.

## 9. Reference projects (study, don't clone)

- `virattt/ai-hedge-fund`: investor-persona and multi-agent reference
- `TradingAgents`: bull/bear debate pattern
- `FinRobot` / `FinGPT`: financial-report analysis
- `OpenBB`: optional data abstraction
- `LangGraph`: orchestration only if multi-agent complexity demands it
- IBKR API (e.g. `ib_async`): read-only portfolio data
- Nordnet: CSV/export initially (verify what API access currently exists)

Don't introduce a framework because it exists.

## 10. Reliability (add when needed)

Retries, caching, token budgets, source validation, immutable snapshots, content hashes. Note non-US coverage gaps: SK Hynix, Samsung, Tokyo Electron and similar names don't file with the SEC, so expect local disclosures, IFRS vs US GAAP differences, and weaker free data. Log 0a findings on this before extending the universe.
