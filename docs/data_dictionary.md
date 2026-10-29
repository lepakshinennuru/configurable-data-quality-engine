# Data Dictionary

## 1. Customers Dataset

**Grain:** One record per customer.

| Column | Description | Expected rule |
|---|---|---|
| customer_id | Unique customer identifier | Required and unique |
| name | Customer name | Required |
| email | Customer email address | Required |
| signup_date | Date the customer registered | Valid date |

**Primary key:** `customer_id`

## 2. Orders Dataset

**Grain:** One record per order.

| Column | Description | Expected rule |
|---|---|---|
| order_id | Unique order identifier | Required and unique |
| customer_id | Customer who placed the order | Must reference an existing customer |
| amount | Order amount | Must satisfy configured range and business rules |
| status | Current order status | Must satisfy configured business rules |
| order_timestamp | Time the order was recorded | Must satisfy the configured freshness rule |

**Primary key:** `order_id`

**Foreign key:** `customer_id` references `customers.customer_id`.

## 3. Relationships

One customer may have multiple orders. Each order should reference a valid customer.

## 4. Data Quality Rules

The engine supports completeness, uniqueness, referential integrity, range, freshness, and custom business-rule validation. Rule definitions are maintained in `config/rules.yaml`.

Failed records are written to quarantine outputs, and rule-level results and row-level issues are reported separately.

## 5. Processing and Traceability

The engine records run identifiers and validation results in SQLite. Reconciliation compares input record counts with clean and quarantined record counts.

## 6. Assumptions and Limitations

The exact column names, required fields, accepted ranges, and business conditions are defined by the project configuration and implementation. This dictionary should be checked against the current CSV headers and `config/rules.yaml` before submission.

The current implementation publishes output files separately; publication across all files is not a single atomic transaction.
