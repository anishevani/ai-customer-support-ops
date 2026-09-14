"""Run the CSV, pandas, and profiling reports from one command."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import default_tickets_csv
from src.fundamentals import format_metrics, load_tickets
from src.pandas_analysis import load_tickets_frame, run_ticket_analysis
from src.profile_data import profile_tickets


def main() -> None:
    csv_path = default_tickets_csv()
    print(f"Source: {csv_path}")
    print("\n--- CSV metrics (no pandas) ---\n")
    print(format_metrics(load_tickets(csv_path)))
    print("\n--- Data profile ---\n")
    frame = load_tickets_frame(csv_path)
    print(profile_tickets(frame))
    print("\n--- Pandas analysis ---\n")
    run_ticket_analysis(frame)


if __name__ == "__main__":
    main()
