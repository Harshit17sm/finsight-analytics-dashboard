# FinSight — FinTech Analytics Dashboard

FinSight turns transaction-level data into an executive-friendly analytics workspace. It includes:

- A browser dashboard with KPI cards, product mix, revenue trend, churn risk, and customer segments.
- CSV upload support for columns such as `customer_id`, `transaction_date`, `amount`, `product_type`, and `status`.
- A Python pipeline that cleans data, derives RFM + churn attributes, and exports Power BI-ready tables.
- A ready-to-use DAX measure reference in `powerbi/measures.dax`.

## Run the dashboard

Open `index.html` directly in a browser, or serve the folder with any static web server. The dashboard loads its built-in demo dataset automatically. Use **Import CSV** to analyze your own export.

The uploader accepts comma-separated files with these fields:

```text
customer_id,transaction_date,amount,product_type,status
```

## Run the pipeline

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py --input data/transactions.csv --output exports
```

The pipeline writes `customers.csv`, `transactions_clean.csv`, `product_summary.csv`, and `monthly_summary.csv` to the output folder. `--as-of 2025-06-30` can be supplied for reproducible churn calculations; otherwise the latest transaction date is used.

## Churn and RFM assumptions

- Churn means no successful transaction in the last 90 days.
- Failed, declined, and reversed transactions are excluded from monetary and activity metrics.
- Recency is measured in days since each customer’s last successful transaction.
- Frequency is successful transaction count; monetary value is successful transaction revenue.

These defaults are intentionally visible in the interface and can be changed in `pipeline.py`.
