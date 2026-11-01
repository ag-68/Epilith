from __future__ import annotations

from research.formatting import METRIC_LABELS, VALUATION_LABELS, confirmation_text, fact_value_text, valuation_value_text
from research.models import EvidenceSet, FactSheet, ModelRun, NumberFinding, RedTeamOutput, SourceBundle, Thesis


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- (none)"]


def render_memo(
    *,
    run_id: str,
    prompt_version: str,
    sheet: FactSheet,
    bundle: SourceBundle,
    evidence: EvidenceSet,
    thesis: Thesis,
    red_team: RedTeamOutput,
    number_findings: list[NumberFinding],
    model_runs: list[ModelRun],
) -> str:
    """Markdown memo. Numbers in the facts section come from the fact sheet, never from model text."""
    lines: list[str] = [
        f"# {sheet.company_name} ({sheet.ticker}) research memo",
        "",
        f"Run `{run_id}`, prompt version `{prompt_version}`. Research aid, not financial advice. Not a trade instruction.",
        "",
        "## Business",
        "",
        thesis.business,
        "",
        "## AI-infrastructure exposure",
        "",
        thesis.ai_infrastructure_exposure,
        "",
        "## Key financial facts",
        "",
        f"Validated in Experiment 0a ({sheet.report_path}, snapshot `{sheet.data_snapshot_id}`). Figures in {sheet.currency}.",
        "",
        "| Metric | Value | Period / as-of | Source | Second document |",
        "|---|---|---|---|---|",
    ]
    for line in sheet.facts:
        lines.append(
            f"| {METRIC_LABELS.get(line.metric, line.metric)} | {fact_value_text(line)} | {line.period_label or ''} "
            f"| {line.source_id or ''} | {confirmation_text(line)} |"
        )
    if sheet.excluded:
        lines += ["", "Not validated, shown for completeness:", ""]
        for line in sheet.excluded:
            lines.append(f"- {METRIC_LABELS.get(line.metric, line.metric)}: {fact_value_text(line)} ({line.status})")
    if sheet.valuation:
        lines += ["", "Descriptive valuation panel (computed in Python):", ""]
        for key, raw in sheet.valuation.items():
            lines.append(f"- {VALUATION_LABELS.get(key, key)}: {valuation_value_text(key, raw)}")
        for note in sheet.valuation_notes:
            lines.append(f"- Note: {note}")

    lines += ["", "## Key evidence", ""]
    if evidence.verified:
        for claim in evidence.verified:
            source = bundle.by_id(claim.source_id)
            title = source.title if source else claim.source_id
            lines.append(f"- **{claim.evidence_id}** {claim.claim}")
            lines.append(f"  > \"{claim.exact_quote}\" — {title} (`{claim.source_id}`)")
    else:
        lines.append("- No claim passed quote verification.")

    lines += ["", "## Financial interpretation", "", thesis.financial_interpretation]
    lines += ["", "## Bull thesis", ""] + _bullets(thesis.bull_thesis)
    lines += ["", "## Bear thesis", ""] + _bullets(thesis.bear_thesis)
    lines += ["", "## Key risks", ""]
    for risk in thesis.key_risks:
        refs = f" [{', '.join(risk.evidence_ids)}]" if risk.evidence_ids else ""
        lines.append(f"- **{risk.category}**: {risk.description}{refs}")
    lines += ["", "## Valuation interpretation", "", thesis.valuation_interpretation]

    lines += ["", "## Three assumptions most likely to be wrong", ""]
    by_id = {a.id: a for a in thesis.assumptions}
    for item in thesis.most_likely_wrong:
        assumption = by_id.get(item.assumption_id)
        value = f" ({assumption.value})" if assumption else ""
        lines.append(f"- `{item.assumption_id}`{value}: {item.why}")

    lines += ["", "## How to verify the top claims", ""]
    for step in thesis.how_to_verify:
        lines.append(f"- {step.claim} — {step.method}")

    lines += [
        "",
        "## Conclusion",
        "",
        f"**{thesis.conclusion.label}.** {thesis.conclusion.reasoning}",
        "",
        "Conditions that would change this:",
        "",
    ] + _bullets(thesis.conclusion.conditions)

    lines += ["", "## Appendix A: Assumptions (structured)", ""]
    for a in thesis.assumptions:
        refs = ", ".join(a.evidence_ids) or "none"
        lines.append(f"- `{a.id}` = {a.value}. {a.rationale} Evidence: {refs}. Invalidated if: {a.invalidated_if}")

    lines += ["", "## Appendix B: Red team", "", red_team.overall_assessment, "", "Attacks:", ""]
    for attack in red_team.attacks:
        refs = f" [{', '.join(attack.evidence_ids)}]" if attack.evidence_ids else ""
        lines.append(f"- **{attack.target}**: {attack.argument}{refs}")
    lines += ["", "Contradictory evidence:", ""]
    lines += _bullets([f"{c.evidence_id}: {c.contradicts}" for c in red_team.contradictory_evidence])
    lines += ["", "Missing risks:", ""] + _bullets(red_team.missing_risks)
    lines += ["", "Alternative explanations:", ""] + _bullets(red_team.alternative_explanations)
    lines += ["", "Invalidation conditions:", ""] + _bullets(red_team.invalidation_conditions)

    lines += ["", "## Appendix C: Claims that failed quote verification", ""]
    if evidence.unverified:
        for claim in evidence.unverified:
            lines.append(f"- {claim.claim} (`{claim.source_id}`): {claim.note}")
    else:
        lines.append("- None.")

    lines += ["", "## Appendix D: Figures in model text not traceable to the fact sheet", ""]
    if number_findings:
        lines.append("Best-effort scan. Each item needs a human check before it is repeated anywhere.")
        lines.append("")
        for finding in number_findings:
            lines.append(f"- `{finding.token}` in {finding.section}: …{finding.context}…")
    else:
        lines.append("- None found.")

    lines += ["", "## Appendix E: Provenance", ""]
    lines.append(f"- Source bundle `{bundle.bundle_id}` with {len(bundle.excerpts)} excerpt(s):")
    for excerpt in bundle.excerpts:
        when = f", {excerpt.published.isoformat()}" if excerpt.published else ""
        lines.append(f"  - `{excerpt.source_id}` {excerpt.kind}: {excerpt.title}{when}, sha256 `{excerpt.content_hash[:16]}`")
    for run in model_runs:
        tokens = ""
        if run.prompt_tokens is not None or run.completion_tokens is not None:
            tokens = f", tokens in/out {run.prompt_tokens}/{run.completion_tokens}"
        lines.append(f"- {run.purpose}: {run.provider} `{run.model}` ({run.model_version or 'n/a'}){tokens}")
    return "\n".join(lines) + "\n"
