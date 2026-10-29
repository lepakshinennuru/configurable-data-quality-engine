import os
import tempfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
CLEAN_DIR = OUTPUT_DIR / "clean"
QUARANTINE_DIR = OUTPUT_DIR / "quarantine"


def _write_csv_safely(df: pd.DataFrame, destination: Path) -> None:
    """Write a CSV to a temporary file before replacing its destination."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            suffix=".tmp",
            prefix=f"{destination.stem}_",
            dir=destination.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            df.to_csv(temp_file, index=False)

        os.replace(temp_path, destination)

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def publish_datasets(
    datasets: dict[str, pd.DataFrame],
    issues_df: pd.DataFrame,
) -> pd.DataFrame:
    """Separate accepted records from records that failed any rule."""

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    reconciliation = []

    for dataset_name, df in datasets.items():
        dataset_issues = issues_df[
            issues_df["dataset"] == dataset_name
        ]

        # Row numbers in the issue report start at 1.
        failed_positions = set(
            pd.to_numeric(
                dataset_issues["row_number"], errors="coerce"
            ).dropna().astype(int) - 1
        )

        # Ignore invalid positions defensively.
        failed_positions = {
            position for position in failed_positions
            if 0 <= position < len(df)
        }

        clean_positions = [
            position for position in range(len(df))
            if position not in failed_positions
        ]
        quarantine_positions = sorted(failed_positions)

        clean_df = df.iloc[clean_positions].copy()
        quarantine_df = df.iloc[quarantine_positions].copy()

        # Preserve the original record fields and add failure details.
        failed_rules_by_position = {}

        for _, issue in dataset_issues.iterrows():
            try:
                position = int(issue["row_number"]) - 1
            except (TypeError, ValueError):
                continue

            if position in failed_positions:
                failed_rules_by_position.setdefault(
                    position, []
                ).append(str(issue["rule_id"]))

        quarantine_df["_dq_failed_rules"] = [
            ";".join(sorted(set(
                failed_rules_by_position.get(position, [])
            )))
            for position in quarantine_positions
        ]

        clean_path = CLEAN_DIR / f"{dataset_name}_clean.csv"
        quarantine_path = (
            QUARANTINE_DIR / f"{dataset_name}_quarantine.csv"
        )

        _write_csv_safely(clean_df, clean_path)
        _write_csv_safely(quarantine_df, quarantine_path)

        input_count = len(df)
        clean_count = len(clean_df)
        quarantine_count = len(quarantine_df)

        reconciliation.append({
            "dataset": dataset_name,
            "input_records": input_count,
            "clean_records": clean_count,
            "quarantined_records": quarantine_count,
            "reconciled": (
                input_count == clean_count + quarantine_count
            ),
        })

    reconciliation_df = pd.DataFrame(reconciliation)
    _write_csv_safely(
        reconciliation_df,
        OUTPUT_DIR / "reconciliation.csv",
    )

    print("\nPUBLISHING SUMMARY")
    print("=" * 35)

    for row in reconciliation:
        print(
            f"{row['dataset']}: "
            f"input={row['input_records']}, "
            f"clean={row['clean_records']}, "
            f"quarantined={row['quarantined_records']}, "
            f"reconciled={row['reconciled']}"
        )

    return reconciliation_df
