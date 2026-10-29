import pandas as pd
import pytest
from unittest.mock import patch

from src.engine import run_engine, load_datasets
from src.database import DATABASE_PATH

@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    test_db = tmp_path / "test_data_quality.db"
    monkeypatch.setattr(
        "src.database.DATABASE_PATH",
        test_db,
    )
    monkeypatch.setattr(
        "src.engine.DATABASE_PATH",
        test_db,
    )
    return test_db

def test_engine_runs_all_configured_rules():
    results_df, issues_df = run_engine()

    # The YAML currently defines eight rules.
    assert len(results_df) == 8

    # Every rule must have a valid status.
    assert set(results_df["status"]).issubset({"PASS", "FAIL"})

    # Issue records must identify the rule that failed.
    if not issues_df.empty:
        assert issues_df["rule_id"].notna().all()

    # The database should have been created.
    assert DATABASE_PATH.exists()



def test_reconciliation_balances_input_records(
    tmp_path,
    monkeypatch,
    isolated_database,
):
    from src import engine, publisher

    test_output = tmp_path / "output"
    test_output.mkdir()

    # Isolate generated files from your real project outputs.
    monkeypatch.setattr(engine, "OUTPUT_DIR", test_output)
    monkeypatch.setattr(publisher, "OUTPUT_DIR", test_output)
    monkeypatch.setattr(
        publisher,
        "CLEAN_DIR",
        test_output / "clean",
    )
    monkeypatch.setattr(
        publisher,
        "QUARANTINE_DIR",
        test_output / "quarantine",
    )

    run_engine()

    reconciliation_path = test_output / "reconciliation.csv"

    assert reconciliation_path.exists()

    reconciliation = pd.read_csv(reconciliation_path)

    assert not reconciliation.empty
    assert reconciliation["reconciled"].all()

    assert (
        reconciliation["input_records"]
        == reconciliation["clean_records"]
        + reconciliation["quarantined_records"]
    ).all()


def test_load_datasets_rejects_missing_required_column():
    config = {
        "datasets": {
            "customers": {
                "required_columns": [
                    "customer_id",
                    "customer_name",
                    "email",
                    "created_at",
                ]
            }
        }
    }

    incomplete_csv = "customer_id,email\nC0001,test@example.com\n"

    with patch("src.engine.INPUT_DIR") as mock_input_dir:
        mock_file = mock_input_dir.__truediv__.return_value
        mock_file.exists.return_value = True
        mock_file.open.return_value.__enter__.return_value = None

        with patch("src.engine.pd.read_csv") as mock_read_csv:
            import io
            mock_read_csv.return_value = pd.read_csv(
                io.StringIO(incomplete_csv)
            )

            with pytest.raises(
                ValueError,
                match="missing columns",
            ):
                load_datasets(config)

def test_load_datasets_rejects_malformed_csv(tmp_path):
    config = {
        "datasets": {
            "customers": {
                "required_columns": [
                    "customer_id",
                    "customer_name",
                    "email",
                    "created_at",
                ]
            }
        }
    }

    malformed_csv = (
        "customer_id,customer_name,email,created_at\n"
        'C0001,"Alice,alice@example.com,2024-01-01\n'
    )

    (tmp_path / "customers.csv").write_text(
        malformed_csv,
        encoding="utf-8",
    )

    with patch("src.engine.INPUT_DIR", tmp_path):
        with pytest.raises(
            ValueError,
            match="malformed CSV data",
        ):
            load_datasets(config)


def test_load_datasets_rejects_empty_csv(tmp_path):
    config = {
        "datasets": {
            "customers": {
                "required_columns": [
                    "customer_id",
                    "customer_name",
                    "email",
                    "created_at",
                ]
            }
        }
    }

    (tmp_path / "customers.csv").write_text(
        "",
        encoding="utf-8",
    )

    with patch("src.engine.INPUT_DIR", tmp_path):
        with pytest.raises(
            ValueError,
            match="empty or has no header",
        ):
            load_datasets(config)


def test_load_datasets_accepts_csv_with_headers_only(tmp_path):
    config = {
        "datasets": {
            "customers": {
                "required_columns": [
                    "customer_id",
                    "customer_name",
                    "email",
                    "created_at",
                ]
            }
        }
    }

    (tmp_path / "customers.csv").write_text(
        "customer_id,customer_name,email,created_at\n",
        encoding="utf-8",
    )

    with patch("src.engine.INPUT_DIR", tmp_path):
        datasets = load_datasets(config)

    assert "customers" in datasets
    assert datasets["customers"].empty
    assert list(datasets["customers"].columns) == [
        "customer_id",
        "customer_name",
        "email",
        "created_at",
    ]


def test_engine_rerun_creates_separate_run_records(isolated_database):
    import sqlite3

    run_engine()
    run_engine()

    with sqlite3.connect(DATABASE_PATH) as connection:
        run_count = connection.execute(
            "SELECT COUNT(*) FROM runs"
        ).fetchone()[0]

        distinct_run_count = connection.execute(
            "SELECT COUNT(DISTINCT run_id) FROM runs"
        ).fetchone()[0]

    assert run_count == distinct_run_count


def test_each_run_has_linked_rule_results(isolated_database):
    import sqlite3

    run_engine()
    run_engine()

    with sqlite3.connect(DATABASE_PATH) as connection:
        runs = connection.execute(
            "SELECT run_id, total_rules FROM runs"
        ).fetchall()

        for run_id, total_rules in runs:
            result_count = connection.execute(
                "SELECT COUNT(*) FROM rule_results WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]

            assert result_count == total_rules



def test_publishing_failure_does_not_report_success(tmp_path):
    from unittest.mock import patch
    from src.publisher import publish_datasets

    datasets = {
        "customers": pd.DataFrame({
            "customer_id": ["C001"],
            "customer_name": ["Alice"],
        })
    }

    issues = pd.DataFrame(
        columns=["dataset", "row_number", "rule_id"]
    )

    with patch("src.publisher.CLEAN_DIR", tmp_path / "clean"), \
         patch("src.publisher.QUARANTINE_DIR", tmp_path / "quarantine"), \
         patch("src.publisher.OUTPUT_DIR", tmp_path), \
         patch(
             "src.publisher.os.replace",
             side_effect=OSError("Simulated disk write failure"),
         ):
        with pytest.raises(
            OSError,
            match="Simulated disk write failure",
        ):
            publish_datasets(datasets, issues)



def test_safe_csv_write_preserves_existing_file_on_failure(tmp_path):
    from unittest.mock import patch
    from src.publisher import _write_csv_safely

    destination = tmp_path / "existing.csv"
    destination.write_text(
        "customer_id\nC001\n",
        encoding="utf-8",
    )

    new_data = pd.DataFrame({
        "customer_id": ["C002"],
    })

    with patch(
        "src.publisher.os.replace",
        side_effect=OSError("Simulated replacement failure"),
    ):
        with pytest.raises(
            OSError,
            match="Simulated replacement failure",
        ):
            _write_csv_safely(new_data, destination)

    assert destination.read_text(encoding="utf-8") == (
        "customer_id\nC001\n"
    )
