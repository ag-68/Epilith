from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from research.runner import record_action, run_memo  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 0b: first research memo")
    parser.add_argument("company", nargs="?", default=None, help="Company name or ticker, e.g. NVIDIA or NVDA")
    parser.add_argument("--company", dest="company_flag", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--action",
        nargs=3,
        metavar=("ENTRY_ID", "ACTION", "REASON"),
        help="Record bought | skipped | watched for a decision log entry instead of writing a memo",
    )
    parser.add_argument("--notes", default=None, help="Override notes to store with --action")
    args = parser.parse_args()
    if args.action:
        entry_id, action, reason = args.action
        record = record_action(entry_id, action, reason, args.notes)  # type: ignore[arg-type]
        print(f"Recorded {record.user_action} for {entry_id} at {record.recorded_at.isoformat()}")
        sys.exit(0)
    query = args.company or args.company_flag
    if not query:
        parser.error("give a company name or ticker, e.g. python experiments/exp0b/run.py NVIDIA")
    result, entry_id = run_memo(query)
    print(result.memo_markdown)
    print(f"Memo: {Path(result.artifact_dir) / 'memo.md'}")
    print(f"Decision log entry: {entry_id}")
    print(
        "Record what you did with it:\n"
        f"  python experiments/exp0b/run.py --action {entry_id} watched \"reason\""
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
