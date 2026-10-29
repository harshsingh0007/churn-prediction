"""Compare all registered versions of each versioned feature and write VERSION_COMPARISON.md."""

import sys

import pandas as pd

sys.path.insert(0, ".")

from feature_store import store

VERSIONED_FEATURES = ["spend_velocity", "engagement_score"]


def compare_feature(feature_name: str) -> str:
    versions_meta = store.list_versions(feature_name)
    versions = sorted(versions_meta["version"].tolist())

    dfs = {v: store.get_version(feature_name, v) for v in versions}

    lines = [f"## {feature_name}\n"]
    lines.append(f"Versions registered: {versions}\n")

    for i, v in enumerate(versions):
        df = dfs[v]
        col = feature_name
        vals = df[col]
        lines.append(f"### v{v}")
        params = versions_meta[versions_meta["version"] == v]["parameters"].iloc[0]
        lines.append(f"Parameters: {params}")
        lines.append(f"- mean={vals.mean():.4f}, std={vals.std():.4f}, "
                     f"min={vals.min():.4f}, p25={vals.quantile(0.25):.4f}, "
                     f"p50={vals.median():.4f}, p75={vals.quantile(0.75):.4f}, "
                     f"max={vals.max():.4f}")
        lines.append(f"- non-zero customers: {(vals > 0).sum()} / {len(vals)}\n")

    # pairwise diffs between consecutive versions
    for idx in range(len(versions) - 1):
        va, vb = versions[idx], versions[idx + 1]
        merged = dfs[va][["customer_id", feature_name]].merge(
            dfs[vb][["customer_id", feature_name]],
            on="customer_id",
            suffixes=(f"_v{va}", f"_v{vb}"),
        )
        col_a = f"{feature_name}_v{va}"
        col_b = f"{feature_name}_v{vb}"
        changed = (merged[col_a] != merged[col_b]).sum()
        diff = (merged[col_b] - merged[col_a])
        lines.append(f"### v{va} → v{vb} comparison")
        lines.append(f"- Customers whose value changed: {changed} / {len(merged)}")
        lines.append(f"- Mean absolute change: {diff.abs().mean():.4f}")
        lines.append(f"- Mean signed change: {diff.mean():.4f}")
        lines.append(f"- Customers with value increase: {(diff > 0).sum()}")
        lines.append(f"- Customers with value decrease: {(diff < 0).sum()}")
        lines.append(f"- Customers unchanged: {(diff == 0).sum()}")

        # rank-order impact: how many customers shift by more than 1 decile
        merged["rank_a"] = merged[col_a].rank(pct=True)
        merged["rank_b"] = merged[col_b].rank(pct=True)
        rank_shift = (merged["rank_b"] - merged["rank_a"]).abs()
        large_shift = (rank_shift > 0.1).sum()
        lines.append(f"- Customers shifting >10 percentile points in rank: {large_shift}\n")

        lines.append("**Interpretation:**")
        if feature_name == "spend_velocity":
            lines.append(
                "Moving from a 30-day to a 14-day short window amplifies velocity signals for "
                "customers with very recent spend changes but suppresses them for customers whose "
                "spend pattern is stable month-over-month. The mean signed change indicates whether "
                "the shorter window systematically raises or lowers velocity scores. A model consuming "
                "this feature would notice the change if the rank-shift count is substantial — customers "
                "near a decision boundary would re-rank."
            )
        elif feature_name == "engagement_score":
            lines.append(
                "Raising the electronics multiplier from 1.5 to 2.0 increases scores for customers "
                "who bought electronics in the 60-day window and leaves all other customers unchanged. "
                "The magnitude of change per affected customer equals (2.0 - 1.5) × number of "
                "electronics transactions in the window. A model would notice this only for the subset "
                "of customers with recent electronics purchases; the rank shift among that cohort could "
                "be significant."
            )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    sections = ["# VERSION_COMPARISON.md\n"]
    sections.append(
        "Per-feature version comparison for the spec-defined versioning exercise.\n"
    )
    for fname in VERSIONED_FEATURES:
        sections.append(compare_feature(fname))

    output = "\n".join(sections)
    with open("VERSION_COMPARISON.md", "w") as f:
        f.write(output)
    print(output)
    print("Written: VERSION_COMPARISON.md")


if __name__ == "__main__":
    main()
