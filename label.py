"""
label.py — Interactive CLI to label collected rows as "good" or "bad".

Usage:
    python label.py --input ecommerce_dataset.csv
"""

import argparse
import pandas as pd


def label_dataset(path: str):
    df = pd.read_csv(path)
    unlabelled = df[df["label"].isna() | (df["label"] == "")].index.tolist()

    if not unlabelled:
        print("✅ All rows are already labelled.")
        return

    print(f"Found {len(unlabelled)} unlabelled rows. Press Ctrl+C to stop.\n")

    for idx in unlabelled:
        row = df.loc[idx]
        print("─" * 60)
        print(f"URL:              {row['url']}")
        print(f"Trust score:      {row.get('trust_score', '?')}/8")
        print(f"Performance:      {row.get('performance_score', '?')}/100")
        print(f"LCP:              {row.get('lcp_ms', '?')} ms")
        print(f"Popup count:      {row.get('popup_count', '?')}")
        print(f"Guest checkout:   {row.get('has_guest_checkout', '?')}")
        print(f"Click depth:      {row.get('click_depth_to_checkout', '?')}")
        print(f"Visual overall:   {row.get('visual_overall', '?')}/10")

        while True:
            choice = input("\nLabel [g=good / b=bad / s=skip]: ").strip().lower()
            if choice in ("g", "b", "s"):
                break
            print("Please enter g, b, or s.")

        if choice == "g":
            df.at[idx, "label"] = "good"
        elif choice == "b":
            df.at[idx, "label"] = "bad"
        else:
            print("Skipped.")

    df.to_csv(path, index=False)
    print(f"\n✅ Labels saved to {path}")
    print(df["label"].value_counts())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="CSV file to label")
    args = p.parse_args()
    label_dataset(args.input)
