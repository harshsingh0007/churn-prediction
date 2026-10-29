"""Pure I/O loaders — one function per source, no feature logic here."""

import sqlite3

import pandas as pd


def load_customers(path: str = "data/customers.csv") -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["signup_date"])


def load_transactions(path: str = "data/transactions.db") -> pd.DataFrame:
    con = sqlite3.connect(path)
    df = pd.read_sql("SELECT * FROM transactions", con)
    con.close()
    df["txn_timestamp"] = pd.to_datetime(df["txn_timestamp"])
    return df


def load_monthly_agg(path: str = "data/transactions_monthly_agg.parquet") -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["txn_month"] = pd.to_datetime(df["txn_month"])
    return df
