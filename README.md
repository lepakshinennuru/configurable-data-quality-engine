# Configurable Data Quality Engine

## Overview

The Configurable Data Quality Engine is a Python-based data validation pipeline that validates datasets against configurable rules defined in YAML. It identifies data quality issues, separates invalid records into quarantine files, publishes clean datasets, generates reports, and stores execution history in SQLite.

The project demonstrates a modular data quality workflow with validation, reconciliation, error handling, testing, and performance benchmarking.

## Features

- **Configurable validation:** Define datasets and validation rules using YAML.
- **Completeness:** Detect missing and blank values.
- **Uniqueness:** Identify duplicate values in key columns.
- **Referential integrity:** Detect references to nonexistent records.
- **Range validation:** Validate values against configured minimum and maximum limits.
- **Freshness validation:** Identify outdated or invalid timestamps.
- **Custom business rules:** Apply named business-specific validation logic.
- **Data quarantine:** Separate records that fail one or more configured rules.
- **Clean data publishing:** Export records that pass all applicable rules.
- **Reconciliation:** Verify that input records equal clean records plus quarantined records.
- **Execution history:** Store run metadata, rule results, and row-level issues in SQLite.
- **Safe CSV writing:** Write individual CSV outputs through temporary files before replacing their destinations.
- **Automated testing:** Include unit and integration tests using pytest.
- **Performance benchmarking:** Measure pipeline execution time over multiple runs.

## Technology Stack

- Python
- Pandas
- PyYAML
- SQLite
- Faker
- pytest

## Project Structure

```text
data-quality-engine/
├── config/
│   └── rules.yaml
├── data/
│   ├── input/
│   │   ├── customers.csv
│   │   └── orders.csv
│   └── output/
│       ├── clean/
│       ├── quarantine/
│       ├── data_quality.db
│       ├── rule_results.csv
│       ├── row_issues.csv
│       └── reconciliation.csv
├── src/
│   ├── __init__.py
│   ├── benchmark.py
│   ├── check_config.py
│   ├── database.py
│   ├── engine.py
│   ├── generator.py
│   ├── publisher.py
│   └── validators.py
├── test/
│   ├── test_validators.py
│   └── test_engine.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd data-quality-engine
```

Replace `<your-repository-url>` with your actual repository URL.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

## Generate Sample Data

Generate a sample dataset:

```bash
python -m src.generator --rows 50 --seed 42
```

Generate a larger dataset for performance testing:

```bash
python -m src.generator --rows 10000 --seed 42
```

The generator creates customer and order CSV files in `data/input/`.

## Run the Engine

Execute the complete data quality pipeline:

```bash
python -m src.engine
```

The engine loads the configuration and datasets, executes the configured validation rules, publishes clean and quarantined records, verifies reconciliation, and saves execution results.

## Run Automated Tests

Run the complete test suite:

```bash
python -m pytest -v
```

The current test suite contains 18 passing tests covering validation behavior, data loading, reconciliation, execution history, and safe CSV writing.

## Run the Performance Benchmark

Execute the pipeline three times and calculate its average, minimum, and maximum runtime:

```bash
python -m src.benchmark
```

In a recent local benchmark using 3,333 customers and 10,000 orders, the average pipeline runtime was approximately 0.954 seconds. Actual performance depends on the machine, dataset, and execution environment.

## Output Files

| Output | Description |
|---|---|
| `rule_results.csv` | Rule-level validation results and failure counts |
| `row_issues.csv` | Details of records that failed validation rules |
| `reconciliation.csv` | Input, clean, and quarantined record counts |
| `data_quality.db` | SQLite database containing execution history and validation results |
| `clean/` | Published datasets containing records that pass the configured rules |
| `quarantine/` | Datasets containing records that fail one or more configured rules |

CSV reports and published datasets represent the latest execution, while SQLite retains historical run records.

## Configuration

Validation rules are maintained in `config/rules.yaml`. Each rule defines its identifier, target dataset, validation type, and severity, together with any required parameters.

Supported rule types include:

- `completeness`
- `uniqueness`
- `referential_integrity`
- `range`
- `freshness`
- `custom`

For example:

```yaml
- rule_id: ORD004
  dataset: orders
  type: range
  column: order_amount
  min: 0
  max: 100000
  severity: HIGH
```

This rule validates that order amounts fall within the configured range.

## Design and Reliability

The application separates configuration loading, validation, execution, database persistence, and publishing into individual modules.

- **Modularity:** Each component has a defined responsibility.
- **Error handling:** Dataset loading detects empty files, malformed CSV data, and missing required columns.
- **Reconciliation:** The pipeline checks that input record counts match clean plus quarantined record counts.
- **Execution history:** SQLite stores separate execution records and their associated rule results and issues.
- **Safe CSV writes:** Each output CSV is written to a temporary file before replacement, helping preserve the previous file if a write or replacement fails.

CSV files are replaced individually; publishing all output files and database updates is not a single atomic transaction.

## Future Improvements

- Atomic publication across all output files and database changes.
- More comprehensive failure-recovery and retry testing.
- Configurable freshness reference times and fully reproducible benchmark datasets.
- Additional validation types and schema-evolution support.
- Performance testing on larger datasets and under concurrent workloads.
- Structured logging and additional operational metrics.

## Conclusion

The Configurable Data Quality Engine demonstrates a configurable, testable, and modular approach to data validation. It combines rule-based checks, record quarantine, reconciliation, SQLite persistence, CSV publishing, and performance measurement in a single Python pipeline.

## Supporting Documentation and Sample Results

- [Data Dictionary](docs/data_dictionary.md): Documents dataset fields, keys, relationships, and assumptions.
- [AI Prompt History](docs/prompt_history.md): Describes AI assistance used during development. This record should be completed with the original prompts available from the development history.
- [Rule Results Sample](docs/sample_outputs/rule_results.csv): Example validation outcomes.
- [Row Issues Sample](docs/sample_outputs/row_issues.csv): Example row-level validation failures.
- [Reconciliation Sample](docs/sample_outputs/reconciliation.csv): Example input, clean, and quarantined record counts.

## Important Limitations

- Publishing multiple output files and updating SQLite are not one atomic transaction.
- The current freshness rule can quarantine older records; the threshold and timestamp behavior are configuration-dependent.
- Sample output files represent a particular execution and may not match a later run.
- Performance results are local measurements, not production-scale guarantees.

