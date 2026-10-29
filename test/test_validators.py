import pandas as pd

from src.validators import check_completeness, check_uniqueness


def test_completeness_detects_missing_and_blank_values():
    df = pd.DataFrame({
        "customer_id": ["C001", None, "  ", "C004"]
    })

    result = check_completeness(df, "customer_id")

    assert result.tolist() == [False, True, True, False]


def test_uniqueness_detects_duplicate_values():
    df = pd.DataFrame({
        "order_id": ["O001", "O002", "O001", "O003"]
    })

    result = check_uniqueness(df, "order_id")

    assert result.tolist() == [True, False, True, False]

from datetime import datetime, timezone

from src.validators import (
    check_referential_integrity,
    check_range,
    check_freshness,
    check_custom_rule,
)


def test_referential_integrity_detects_unknown_customer():
    orders = pd.DataFrame({
        "customer_id": ["C001", "C999", None]
    })
    customers = pd.DataFrame({
        "customer_id": ["C001", "C002"]
    })

    result = check_referential_integrity(
        orders, "customer_id", customers, "customer_id"
    )

    assert result.tolist() == [False, True, True]


def test_range_detects_values_outside_limits():
    df = pd.DataFrame({
        "order_amount": [100, -5, 100001, "invalid"]
    })

    result = check_range(df, "order_amount", 0, 100000)

    assert result.tolist() == [False, True, True, True]


def test_freshness_detects_old_timestamps():
    df = pd.DataFrame({
        "order_timestamp": [
            "2026-10-28T11:30:00",
            "2026-10-26T11:30:00",
            "invalid",
        ]
    })
    reference_time = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)

    result = check_freshness(
        df, "order_timestamp", 24, reference_time
    )

    assert result.tolist() == [False, True, True]


def test_custom_rule_detects_completed_order_with_zero_amount():
    df = pd.DataFrame({
        "order_status": ["completed", "pending", "completed"],
        "order_amount": [100, 0, 0],
    })

    result = check_custom_rule(
        df, "completed_order_positive_amount"
    )

    assert result.tolist() == [False, False, True]

    
import pandas as pd
from src.validators import check_completeness, check_uniqueness


def test_completeness_with_empty_dataframe():
    df = pd.DataFrame({"customer_id": []})

    result = check_completeness(df, "customer_id")

    assert len(result) == 0


def test_uniqueness_with_empty_dataframe():
    df = pd.DataFrame({"customer_id": []})

    result = check_uniqueness(df, "customer_id")

    assert len(result) == 0
