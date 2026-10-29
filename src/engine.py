from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from src.publisher import publish_datasets
from src.database import DATABASE_PATH, save_run
from src.validators import evaluate_rule


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "rules.yaml"
INPUT_DIR = PROJECT_ROOT / "data" / "input"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def load_config() -> dict:
    """Load validation rules and dataset configuration."""

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("The YAML configuration must contain a mapping.")

    if "datasets" not in config or "rules" not in config:
        raise ValueError("Configuration must contain datasets and rules.")

    return config


def load_datasets(config: dict) -> dict[str, pd.DataFrame]:
    """Load configured CSV datasets."""

    datasets = {}

    for dataset_name, dataset_config in config["datasets"].items():
        file_path = INPUT_DIR / f"{dataset_name}.csv"

        if not file_path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {file_path}"
            )

        
        try:
            df = pd.read_csv(file_path)
        except pd.errors.EmptyDataError as exc:
            raise ValueError(
                f"Dataset '{dataset_name}' is empty or has no header."
            ) from exc
        except pd.errors.ParserError as exc:
            raise ValueError(
                f"Dataset '{dataset_name}' contains malformed CSV data: {exc}"
            ) from exc


        required_columns = dataset_config.get("required_columns", [])
        missing_columns = [
            column for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Dataset '{dataset_name}' is missing columns: "
                f"{missing_columns}"
            )

        datasets[dataset_name] = df

    return datasets


def run_engine() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Execute all configured rules and save validation reports."""

    config = load_config()
    datasets = load_datasets(config)

    run_time = datetime.now(timezone.utc).isoformat()
    rule_results = []
    row_issues = []

    for rule in config["rules"]:
        dataset_name = rule["dataset"]

        if dataset_name not in datasets:
            raise ValueError(
                f"Rule {rule['rule_id']} refers to unknown dataset "
                f"'{dataset_name}'."
            )

        df = datasets[dataset_name]

        failed_mask = evaluate_rule(
            rule=rule,
            df=df,
            datasets=datasets,
        )

        failed_mask = failed_mask.fillna(True).astype(bool)
        failed_positions = [
            position
            for position, failed in enumerate(failed_mask.tolist())
            if failed
        ]

        failed_count = len(failed_positions)
        total_count = len(df)
        passed_count = total_count - failed_count

        pass_rate = (
            round((passed_count / total_count) * 100, 2)
            if total_count > 0
            else 100.0
        )

        rule_results.append({
            "run_time": run_time,
            "dataset": dataset_name,
            "rule_id": rule["rule_id"],
            "rule_type": rule["type"],
            "severity": rule["severity"],
            "status": "FAIL" if failed_count else "PASS",
            "total_records": total_count,
            "passed_records": passed_count,
            "failed_records": failed_count,
            "pass_rate_percent": pass_rate,
        })

        dataset_config = config["datasets"][dataset_name]
        primary_key = dataset_config.get("primary_key")
        column = rule.get("column")

        for position in failed_positions:
            row = df.iloc[position]

            record_id = (
                row[primary_key]
                if primary_key and primary_key in df.columns
                else None
            )

            value = (
                row[column]
                if column and column in df.columns
                else str(row.to_dict())
            )

            row_issues.append({
                "run_time": run_time,
                "dataset": dataset_name,
                "rule_id": rule["rule_id"],
                "severity": rule["severity"],
                "row_number": position + 1,
                "record_id": record_id,
                "column": column or rule.get("name", "custom_rule"),
                "value": value,
                "message": (
                    f"Record failed {rule['type']} validation "
                    f"for rule {rule['rule_id']}."
                ),
            })

    results_df = pd.DataFrame(rule_results)
    
    issue_columns = [
        "run_time", "dataset", "rule_id", "severity",
        "row_number", "record_id", "column", "value", "message",
    ]

    issues_df = pd.DataFrame(row_issues,
    columns=issue_columns)
    
    reconciliation_df = publish_datasets(datasets, issues_df)

    if not reconciliation_df["reconciled"].all():
        raise RuntimeError("Record reconciliation failed.")
    
    # Save this execution and its results in SQLite.
    run_id = save_run(results_df, issues_df)

    # Include the run ID in the CSV reports as well.
    results_df.insert(0, "run_id", run_id)
    issues_df.insert(0, "run_id", run_id)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results_df.to_csv(OUTPUT_DIR / "rule_results.csv", index=False)
    issues_df.to_csv(OUTPUT_DIR / "row_issues.csv", index=False)

    print("\nDATA QUALITY ENGINE RESULTS")
    print("=" * 35)
    print(f"Run time: {run_time}")
    print(f"Run ID: {run_id}")
    print(f"SQLite database: {DATABASE_PATH}")
    print(f"Datasets loaded: {len(datasets)}")
    print(f"Rules executed: {len(results_df)}")
    print(f"Rules passed: {(results_df['status'] == 'PASS').sum()}")
    print(f"Rules failed: {(results_df['status'] == 'FAIL').sum()}")
    print(f"Failed record-rule issues: {len(issues_df)}")
    print(f"\nReports saved to: {OUTPUT_DIR}")

    print("\nRule summary:")
    print(
        results_df[
            ["dataset", "rule_id", "status", "failed_records"]
        ].to_string(index=False)
    )

    return results_df, issues_df


if __name__ == "__main__":
    run_engine()