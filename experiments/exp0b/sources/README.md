# Source excerpts for Experiment 0b

The analyst may only quote from stored text. There are two ways that text gets here.

## Automatic (default)

For a United States filer nothing needs to be done. The runner downloads the company's newest annual report
(10-K), the quarterly report filed after it (10-Q), and the newest earnings release (8-K exhibit), stores the
raw files under `data/raw/sec_edgar/<TICKER>/`, and cuts fixed sections by their printed headings:

| Document | Sections kept | Cut at |
|---|---|---|
| 10-K | Item 1 Business, Item 1A Risk Factors, Item 7 MD&A | 12k / 15k / 15k characters |
| 10-Q | Item 2 MD&A, Item 1A Risk Factors | 15k / 6k characters |
| 8-K earnings release | whole exhibit | 12k characters |

The cut text and a `sources.yaml` manifest are written to `data/sources/<TICKER>/<folder_id>/`. The folder
name is derived from the filings' hashes and the cutting rules, so the same filings always produce the same
folder and nothing is rewritten. A newer filing produces a new folder.

This is selection by heading, not retrieval: no index, no search, no ranking. A retrieval step can replace
`src/research/filing_sections.py` later without changing anything downstream. Companies outside the United
States are not cut automatically yet and need the manual folder below.

## Manual (override)

One folder per ticker here. If `sources.yaml` lists at least one entry, it is used instead of the automatic
cut. Plain-text excerpts plus the manifest:

```text
sources/
└── NVDA/
    ├── sources.yaml
    ├── 10q_q2fy27_mdna.txt
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

Rules for both:

- Text is stored verbatim. The quote checker compares the model's quotes against these bytes.
- Keep a file once a run has used it. Each run records the file's hash, so the file is evidence.
- A new version of a document is a new file; old ones are not edited.
- Nothing about your portfolio, position, or preference goes in here. The analyst must not see it.
