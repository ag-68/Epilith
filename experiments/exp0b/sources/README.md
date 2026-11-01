# Source excerpts for Experiment 0b

One folder per ticker. Each folder holds plain-text excerpts and a `sources.yaml` that describes them.
The excerpts are chosen by hand. No retrieval index, no whole filings. Pick the passages that matter:
the business description, the segment and demand commentary, guidance, risk factors, and a few recent
news items.

```text
sources/
└── NVDA/
    ├── sources.yaml
    ├── 10q_q2fy27_mdna.txt
    ├── q2fy27_release.txt
    └── news_2026-10-15_reuters.txt
```

`sources.yaml`:

```yaml
sources:
  - source_id: nvda-10q-q2fy27-mdna
    kind: filing            # filing | ir_release | annual_report | transcript | news
    title: "NVIDIA Form 10-Q, quarter ended 26 July 2026, MD&A excerpt"
    url: https://www.sec.gov/...
    published: 2026-08-27
    file: 10q_q2fy27_mdna.txt
```

Rules:

- Paste text verbatim. The quote checker compares the model's quotes against these bytes.
- Keep the file in the folder when a run has used it. Each run records the file's hash, so the file is evidence.
- Add a new file for a new version of a document; do not edit the old one.
- Nothing about your portfolio, position, or preference goes in here. The analyst must not see it.
