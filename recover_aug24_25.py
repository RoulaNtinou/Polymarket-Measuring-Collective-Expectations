
import time
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

SOURCE_FILE = "election_market_history_complete_check.csv"
OUTPUT_FILE = "recovered_election_history_aug24_25.csv"

START = datetime(2026, 8, 24, tzinfo=timezone.utc)
END = datetime(2026, 8, 26, tzinfo=timezone.utc)

df = pd.read_csv(
    SOURCE_FILE,
    usecols=["date", "market_id", "yes_token"],
    low_memory=False,
)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["market_id"] = df["market_id"].astype(str)
df["yes_token"] = df["yes_token"].fillna("").astype(str).str.strip()

# Target markets present immediately before or after the gap.
before = set(df.loc[df["date"] == "2026-08-23", "market_id"])
after = set(df.loc[df["date"] == "2026-08-27", "market_id"])
target_ids = before | after

token_map = (
    df[df["yes_token"] != ""]
    .drop_duplicates("market_id")
    .set_index("market_id")["yes_token"]
    .to_dict()
)

targets = {
    market_id: token_map[market_id]
    for market_id in sorted(target_ids)
    if market_id in token_map
}

print("Markets to check:", len(targets))

session = requests.Session()
recovered = []
errors = []

start_ts = int(START.timestamp())
end_ts = int(END.timestamp())

for i, (market_id, token_id) in enumerate(targets.items(), start=1):
    try:
        response = session.get(
            "https://clob.polymarket.com/prices-history",
            params={
                "market": token_id,
                "startTs": start_ts,
                "endTs": end_ts,
                "fidelity": 1440,
            },
            timeout=30,
        )
        response.raise_for_status()
        history = response.json().get("history", [])

        for item in history:
            timestamp = int(item["t"])

            if not start_ts <= timestamp < end_ts:
                continue

            observation_date = datetime.fromtimestamp(
                timestamp, timezone.utc
            ).date()

            if observation_date not in {
                START.date(),
                (START + timedelta(days=1)).date(),
            }:
                continue

            recovered.append({
                "market_id": market_id,
                "date": str(observation_date),
                "probability": float(item["p"]) * 100,
                "yes_token": token_id,
            })

    except Exception as exc:
        errors.append((market_id, str(exc)))

    if i % 100 == 0:
        print(f"Checked {i}/{len(targets)} markets")

    time.sleep(0.03)

result = pd.DataFrame(recovered)

if not result.empty:
    result = result.drop_duplicates(["market_id", "date"])
    result.to_csv(OUTPUT_FILE, index=False)

print("\nRecovery complete.")
print("Markets checked:", len(targets))
print("Observations recovered:", len(result))
print("Markets with observations:",
      result["market_id"].nunique() if not result.empty else 0)
print("API errors:", len(errors))
print("Output:", OUTPUT_FILE if not result.empty else "No file created")

if not result.empty:
    print("\nObservations per date:")
    print(result.groupby("date").size().to_string())

if errors:
    print("\nFirst 10 errors:")
    for error in errors[:10]:
        print(error)
