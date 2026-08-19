"""Clean transaction data and produce RFM/churn tables for FinSight and Power BI."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"customer_id", "transaction_date", "amount", "product_type", "status"}
SUCCESS_STATUSES = {"completed", "success", "successful", "settled", "paid"}
CHURN_DAYS = 90


def clean_transactions(input_path: Path, as_of: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(input_path)
    missing = REQUIRED_COLUMNS - set(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    transactions = raw.copy()
    transactions["customer_id"] = transactions["customer_id"].astype(str).str.strip()
    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["amount"] = pd.to_numeric(transactions["amount"], errors="coerce")
    transactions["product_type"] = transactions["product_type"].fillna("Unknown").astype(str).str.strip()
    transactions["status"] = transactions["status"].fillna("unknown").astype(str).str.lower().str.strip()
    transactions = transactions.dropna(subset=["customer_id", "transaction_date", "amount"])
    transactions = transactions.drop_duplicates()
    transactions["is_successful"] = transactions["status"].isin(SUCCESS_STATUSES)
    successful = transactions[transactions["is_successful"]].copy()
    if successful.empty:
        raise ValueError("No successful transactions found after cleaning")

    snapshot = pd.Timestamp(as_of) if as_of else successful["transaction_date"].max()
    customer = successful.groupby("customer_id").agg(
        last_transaction_date=("transaction_date", "max"),
        frequency=("customer_id", "size"),
        monetary_value=("amount", "sum"),
        average_transaction=("amount", "mean"),
        products_used=("product_type", "nunique"),
    ).reset_index()
    customer["recency_days"] = (snapshot - customer["last_transaction_date"]).dt.days.clip(lower=0)
    customer["is_churned"] = (customer["recency_days"] > CHURN_DAYS).astype(int)
    customer["churn_status"] = customer["is_churned"].map({1: "At risk", 0: "Active"})
    customer["rfm_segment"] = pd.qcut(
        customer["monetary_value"].rank(method="first"), 4, labels=["Starter", "Growing", "Core", "VIP"]
    ) if len(customer) >= 4 else "Core"

    transactions["transaction_date"] = transactions["transaction_date"].dt.strftime("%Y-%m-%d")
    customer["last_transaction_date"] = customer["last_transaction_date"].dt.strftime("%Y-%m-%d")
    return transactions, customer


def export_tables(transactions: pd.DataFrame, customer: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    transactions.to_csv(output_dir / "transactions_clean.csv", index=False)
    customer.to_csv(output_dir / "customers.csv", index=False)
    successful = transactions[transactions["is_successful"]]
    successful = successful.assign(
        month=pd.to_datetime(successful["transaction_date"]).dt.to_period("M").astype(str)
    )
    successful.groupby("product_type", as_index=False).agg(
        revenue=("amount", "sum"), transactions=("customer_id", "size"), customers=("customer_id", "nunique")
    ).to_csv(output_dir / "product_summary.csv", index=False)
    successful.groupby("month", as_index=False).agg(
        revenue=("amount", "sum"), transactions=("customer_id", "size"), customers=("customer_id", "nunique")
    ).to_csv(output_dir / "monthly_summary.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("exports"))
    parser.add_argument("--as-of")
    args = parser.parse_args()
    transactions, customer = clean_transactions(args.input, args.as_of)
    export_tables(transactions, customer, args.output)
    print(f"Exported {len(transactions):,} transactions and {len(customer):,} customers to {args.output}")


if __name__ == "__main__":
    main()
