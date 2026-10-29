"""Score one or more customers using the same build_features code path as training."""

import sys

sys.path.insert(0, ".")

from features.build import build_features


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python scripts/score_customer.py <as_of_date> <customer_id> [customer_id ...]")
        print("Example: python scripts/score_customer.py 2026-08-01 42 100")
        sys.exit(1)

    as_of = sys.argv[1]
    customer_ids = [int(x) for x in sys.argv[2:]]

    print(f"Scoring customer_ids={customer_ids} as_of={as_of}")
    result = build_features(as_of, customer_ids=customer_ids)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
