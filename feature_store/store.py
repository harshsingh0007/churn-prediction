"""Local feature store: SQLite registry + parquet value snapshots."""

import json
import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd

REGISTRY_PATH = "feature_store/registry.db"
VALUES_DIR = "feature_store/values"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS feature_registry (
    feature_name     TEXT NOT NULL,
    version          INTEGER NOT NULL,
    created_at       TEXT NOT NULL,
    description      TEXT NOT NULL,
    source_columns   TEXT NOT NULL,
    transform_summary TEXT NOT NULL,
    business_rationale TEXT NOT NULL,
    parameters       TEXT NOT NULL,
    parquet_path     TEXT NOT NULL,
    is_latest        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (feature_name, version)
)
"""


def _connect() -> sqlite3.Connection:
    os.makedirs("feature_store", exist_ok=True)
    con = sqlite3.connect(REGISTRY_PATH)
    con.execute(_SCHEMA)
    con.commit()
    return con


def version_exists_with_parameters(feature_name: str, parameters: dict) -> bool:
    """Return True if any registered version of this feature has exactly these parameters."""
    con = _connect()
    rows = con.execute(
        "SELECT parameters FROM feature_registry WHERE feature_name = ?", (feature_name,)
    ).fetchall()
    con.close()
    params_json = json.dumps(parameters, sort_keys=True)
    return any(json.dumps(json.loads(r[0]), sort_keys=True) == params_json for r in rows)


def register_version(
    feature_name: str,
    values_df: pd.DataFrame,
    description: str,
    source_columns: str,
    transform_summary: str,
    business_rationale: str,
    parameters: dict,
) -> int:
    """Write parquet snapshot, insert registry row, flip is_latest. Returns new version."""
    os.makedirs(VALUES_DIR, exist_ok=True)
    con = _connect()
    cur = con.cursor()

    cur.execute(
        "SELECT COALESCE(MAX(version), 0) FROM feature_registry WHERE feature_name = ?",
        (feature_name,),
    )
    next_version = cur.fetchone()[0] + 1

    parquet_path = f"{VALUES_DIR}/{feature_name}__v{next_version}.parquet"
    if os.path.exists(parquet_path):
        raise FileExistsError(f"Refusing to overwrite existing version: {parquet_path}")
    values_df.to_parquet(parquet_path, index=False)

    created_at = datetime.now(timezone.utc).isoformat()

    # flip previous latest to 0 and insert new row atomically
    cur.execute(
        "UPDATE feature_registry SET is_latest = 0 WHERE feature_name = ?",
        (feature_name,),
    )
    cur.execute(
        """INSERT INTO feature_registry
           (feature_name, version, created_at, description, source_columns,
            transform_summary, business_rationale, parameters, parquet_path, is_latest)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (
            feature_name,
            next_version,
            created_at,
            description,
            source_columns,
            transform_summary,
            business_rationale,
            json.dumps(parameters),
            parquet_path,
        ),
    )
    con.commit()
    con.close()
    return next_version


def get_latest(feature_name: str) -> pd.DataFrame:
    con = _connect()
    row = con.execute(
        "SELECT parquet_path FROM feature_registry WHERE feature_name = ? AND is_latest = 1",
        (feature_name,),
    ).fetchone()
    con.close()
    if row is None:
        raise KeyError(f"No registered versions for feature: {feature_name}")
    return pd.read_parquet(row[0])


def get_version(feature_name: str, version: int) -> pd.DataFrame:
    con = _connect()
    row = con.execute(
        "SELECT parquet_path FROM feature_registry WHERE feature_name = ? AND version = ?",
        (feature_name, version),
    ).fetchone()
    con.close()
    if row is None:
        raise KeyError(f"No version {version} for feature: {feature_name}")
    return pd.read_parquet(row[0])


def list_versions(feature_name: str) -> pd.DataFrame:
    con = _connect()
    df = pd.read_sql(
        "SELECT * FROM feature_registry WHERE feature_name = ? ORDER BY version DESC",
        con,
        params=(feature_name,),
    )
    con.close()
    return df
