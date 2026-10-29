"""Feature store tests — versioning, retrieval, is_latest correctness."""

import os
import shutil
import tempfile

import pandas as pd
import pytest

import feature_store.store as store_module


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Redirect store paths to a temp dir for each test."""
    monkeypatch.setattr(store_module, "REGISTRY_PATH", str(tmp_path / "registry.db"))
    monkeypatch.setattr(store_module, "VALUES_DIR", str(tmp_path / "values"))
    yield


def _sample_df(feature_name: str, n: int = 5) -> pd.DataFrame:
    return pd.DataFrame({
        "customer_id": list(range(1, n + 1)),
        feature_name: [float(i) for i in range(1, n + 1)],
        "as_of_date": ["2026-08-01"] * n,
    })


def test_register_and_get_version():
    v = store_module.register_version(
        "spend_velocity",
        _sample_df("spend_velocity"),
        description="test v1",
        source_columns="data/transactions.db:transactions.amount",
        transform_summary="test",
        business_rationale="test",
        parameters={"short_window_days": 30},
    )
    assert v == 1
    df = store_module.get_version("spend_velocity", 1)
    assert list(df["spend_velocity"]) == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_two_versions_independently_retrievable():
    v1 = store_module.register_version(
        "spend_velocity",
        _sample_df("spend_velocity"),
        description="v1",
        source_columns="s",
        transform_summary="t",
        business_rationale="b",
        parameters={"short_window_days": 30},
    )

    df2 = _sample_df("spend_velocity")
    df2["spend_velocity"] *= 2  # different values
    v2 = store_module.register_version(
        "spend_velocity",
        df2,
        description="v2",
        source_columns="s",
        transform_summary="t",
        business_rationale="b",
        parameters={"short_window_days": 14},
    )

    assert v1 == 1
    assert v2 == 2
    r1 = store_module.get_version("spend_velocity", 1)
    r2 = store_module.get_version("spend_velocity", 2)
    assert r1["spend_velocity"].iloc[0] != r2["spend_velocity"].iloc[0]


def test_is_latest_points_to_highest_version():
    for _ in range(3):
        store_module.register_version(
            "engagement_score",
            _sample_df("engagement_score"),
            description="v",
            source_columns="s",
            transform_summary="t",
            business_rationale="b",
            parameters={},
        )
    latest = store_module.get_latest("engagement_score")
    versions = store_module.list_versions("engagement_score")
    assert versions[versions["is_latest"] == 1]["version"].iloc[0] == 3
    assert len(latest) == 5  # correct parquet loaded


def test_list_versions_returns_all_with_distinct_paths():
    for i in range(3):
        df = _sample_df("spend_velocity")
        df["spend_velocity"] += i
        store_module.register_version(
            "spend_velocity", df,
            description=f"v{i+1}", source_columns="s", transform_summary="t",
            business_rationale="b", parameters={"short_window_days": 30 - i * 8},
        )
    versions = store_module.list_versions("spend_velocity")
    assert len(versions) == 3
    assert versions["parquet_path"].nunique() == 3
    for path in versions["parquet_path"]:
        assert os.path.exists(path)


def test_get_version_raises_for_missing():
    with pytest.raises(KeyError):
        store_module.get_version("spend_velocity", 99)


def test_no_overwrite_of_existing_version(tmp_path, monkeypatch):
    """Registering again after manually pre-creating the parquet must raise."""
    monkeypatch.setattr(store_module, "REGISTRY_PATH", str(tmp_path / "registry.db"))
    values_dir = str(tmp_path / "values")
    monkeypatch.setattr(store_module, "VALUES_DIR", values_dir)
    os.makedirs(values_dir)

    # pre-create the file that v1 would write
    open(os.path.join(values_dir, "spend_velocity__v1.parquet"), "w").close()

    with pytest.raises(FileExistsError):
        store_module.register_version(
            "spend_velocity",
            _sample_df("spend_velocity"),
            description="v1",
            source_columns="s",
            transform_summary="t",
            business_rationale="b",
            parameters={},
        )
