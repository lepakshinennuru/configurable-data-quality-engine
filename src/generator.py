
import argparse
from pathlib import Path

import pandas as pd
from faker import Faker
from datetime import datetime, timedelta


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "data" / "input"


def generate_data(rows: int = 50, seed: int = 42) -> None:
    """Generate reproducible customer and order CSV files."""

    fake = Faker()
    fake.seed_instance(seed)

    reference_time = datetime.now()

    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate customers
    customer_count = max(10, rows // 3)
    customers = []

    for i in range(1, customer_count + 1):
        customers.append({
            "customer_id": f"C{i:04d}",
            "customer_name": fake.name(),
            "email": fake.email(),
            "created_at": fake.date_time_between(
                start_date=reference_time - timedelta(days=180),
                end_date=reference_time
            ).isoformat()
        })

    customers_df = pd.DataFrame(customers)

    # Generate orders
    orders = []

    for i in range(1, rows + 1):
        customer = customers[(i - 1) % customer_count]

        orders.append({
            "order_id": f"O{i:06d}",
            "customer_id": customer["customer_id"],
            "order_amount": round(
                fake.pyfloat(
                    min_value=10,
                    max_value=5000,
                    right_digits=2
                ),
                2
            ),
            "order_status": [
                "pending", "completed", "cancelled"
            ][i % 3],
            "order_timestamp": (
                reference_time - timedelta(
                    hours=fake.random_int(min=1, max=168)
                )
            ).isoformat(),
            "source_file": "orders.csv"
        })

    orders_df = pd.DataFrame(orders)

    customers_df.to_csv(INPUT_DIR / "customers.csv", index=False)
    orders_df.to_csv(INPUT_DIR / "orders.csv", index=False)

    print("Sample data generated successfully!")
    print(f"Customers: {len(customers_df)}")
    print(f"Orders: {len(orders_df)}")
    print(f"Saved to: {INPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.rows < 1:
        parser.error("--rows must be greater than zero")

    generate_data(rows=args.rows, seed=args.seed)