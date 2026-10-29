import sqlite3
import uuid
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "output" / "data_quality.db"


def initialize_database():
    """Create the database and its tables if they do not exist."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                run_time TEXT NOT NULL,
                total_rules INTEGER NOT NULL,
                passed_rules INTEGER NOT NULL,
                failed_rules INTEGER NOT NULL,
                total_issues INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rule_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                dataset TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                total_records INTEGER NOT NULL,
                passed_records INTEGER NOT NULL,
                failed_records INTEGER NOT NULL,
                pass_rate_percent REAL NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS row_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                dataset TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                row_number INTEGER NOT NULL,
                record_id TEXT,
                column_name TEXT NOT NULL,
                value TEXT,
                message TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );
        """)


def _safe_value(value):
    """Convert pandas values to values SQLite can store."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        value = value.item()

    return value


def save_run(
    results_df: pd.DataFrame,
    issues_df: pd.DataFrame,
) -> str:
    """Save one execution and its results in a single transaction."""

    initialize_database()

    run_id = str(uuid.uuid4())

    run_time = (
        results_df["run_time"].iloc[0]
        if not results_df.empty
        else pd.Timestamp.now(tz="UTC").isoformat()
    )

    passed_rules = int((results_df["status"] == "PASS").sum())
    failed_rules = int((results_df["status"] == "FAIL").sum())

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            connection.execute(
                """
                INSERT INTO runs (
                    run_id, run_time, total_rules,
                    passed_rules, failed_rules, total_issues
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    run_time,
                    len(results_df),
                    passed_rules,
                    failed_rules,
                    len(issues_df),
                ),
            )

            for row in results_df.to_dict(orient="records"):
                connection.execute(
                    """
                    INSERT INTO rule_results (
                        run_id, dataset, rule_id, rule_type, severity,
                        status, total_records, passed_records,
                        failed_records, pass_rate_percent
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        row["dataset"],
                        row["rule_id"],
                        row["rule_type"],
                        row["severity"],
                        row["status"],
                        int(row["total_records"]),
                        int(row["passed_records"]),
                        int(row["failed_records"]),
                        float(row["pass_rate_percent"]),
                    ),
                )

            for row in issues_df.to_dict(orient="records"):
                connection.execute(
                    """
                    INSERT INTO row_issues (
                        run_id, dataset, rule_id, severity, row_number,
                        record_id, column_name, value, message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        row["dataset"],
                        row["rule_id"],
                        row["severity"],
                        int(row["row_number"]),
                        _safe_value(row["record_id"]),
                        str(row["column"]),
                        _safe_value(row["value"]),
                        row["message"],
                    ),
                )

    return run_id