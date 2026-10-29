from datetime import datetime, timezone

import pandas as pd


def check_completeness(df: pd.DataFrame, column: str) -> pd.Series:
    """Return True for rows where a column is missing or blank."""

    missing = df[column].isna()
    blank = df[column].astype("string").str.strip().eq("").fillna(False)

    return missing | blank


def check_uniqueness(df: pd.DataFrame, column: str) -> pd.Series:
    """Return True for all rows containing a duplicate non-null value."""

    return df[column].duplicated(keep=False) & df[column].notna()


def check_referential_integrity(
    df: pd.DataFrame,
    column: str,
    reference_df: pd.DataFrame,
    reference_column: str,
) -> pd.Series:
    """Return True when a value has no matching reference record."""

    values = df[column].astype("string").str.strip()
    reference_values = (
        reference_df[reference_column]
        .dropna()
        .astype("string")
        .str.strip()
    )

    missing = values.isna() | values.eq("").fillna(False)
    unmatched = ~values.isin(reference_values)

    return missing | unmatched


def check_range(
    df: pd.DataFrame,
    column: str,
    minimum: float,
    maximum: float,
) -> pd.Series:
    """Return True for non-numeric values or values outside the allowed range."""

    values = pd.to_numeric(df[column], errors="coerce")

    return values.isna() | (values < minimum) | (values > maximum)


def check_freshness(
    df: pd.DataFrame,
    column: str,
    max_age_hours: float,
    reference_time: datetime | None = None,
) -> pd.Series:
    """Return True for invalid timestamps or timestamps that are too old."""

    timestamps = pd.to_datetime(df[column], errors="coerce", utc=True)

    if reference_time is None:
        now = pd.Timestamp.now(tz="UTC")
    else:
        now = pd.Timestamp(reference_time)
        if now.tzinfo is None:
            now = now.tz_localize("UTC")
        else:
            now = now.tz_convert("UTC")

    cutoff = now - pd.Timedelta(hours=max_age_hours)

    return timestamps.isna() | (timestamps < cutoff)


def check_custom_rule(
    df: pd.DataFrame,
    rule_name: str,
) -> pd.Series:
    """Run a supported, named business rule."""

    if rule_name == "completed_order_positive_amount":
        status = df["order_status"].astype("string").str.strip().str.lower()
        amount = pd.to_numeric(df["order_amount"], errors="coerce")

        return status.eq("completed") & (
            amount.isna() | (amount <= 0)
        )

    raise ValueError(f"Unsupported custom rule: {rule_name}")


def evaluate_rule(
    rule: dict,
    df: pd.DataFrame,
    datasets: dict[str, pd.DataFrame],
    reference_time: datetime | None = None,
) -> pd.Series:
    """Select the correct validator for a rule from the YAML configuration."""

    rule_type = rule["type"]

    if rule_type == "custom":
        return check_custom_rule(df, rule["name"])
    
    column = rule["column"]

    if column not in df.columns:
        raise ValueError(
            f"Rule {rule['rule_id']}: column '{column}' does not exist"
        )

    if rule_type == "completeness":
        return check_completeness(df, column)

    if rule_type == "uniqueness":
        return check_uniqueness(df, column)

    if rule_type == "referential_integrity":
        reference_name = rule["reference_dataset"]

        if reference_name not in datasets:
            raise ValueError(
                f"Rule {rule['rule_id']}: reference dataset "
                f"'{reference_name}' was not loaded"
            )

        reference_df = datasets[reference_name]
        reference_column = rule["reference_column"]

        if reference_column not in reference_df.columns:
            raise ValueError(
                f"Rule {rule['rule_id']}: reference column "
                f"'{reference_column}' does not exist"
            )

        return check_referential_integrity(
            df,
            column,
            reference_df,
            reference_column,
        )

    if rule_type == "range":
        return check_range(
            df,
            column,
            rule["min"],
            rule["max"],
        )

    if rule_type == "freshness":
        return check_freshness(
            df,
            column,
            rule["max_age_hours"],
            reference_time,
        )

    if rule_type == "custom":
        return check_custom_rule(df, rule["name"])

    raise ValueError(
        f"Rule {rule['rule_id']}: unsupported type '{rule_type}'"
    )