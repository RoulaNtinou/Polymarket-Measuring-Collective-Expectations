
import time
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

SOURCE_FILE = "election_market_history_merged_check.csv"
OUTPUT_FILE = "recovered_election_history_october.csv"

START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 10, 21, tzinfo=timezone.utc)
MISSING_DATES = {
    datetime(2026, 10, day).date()
    for day in list(range(1, 11)) + [14, 19, 20]
}

df = pd.read_csv(SOURCE_FILE, low_memory=False)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["market_id"] = df["market_id"].astype(str)
df["yes_token"] = df["yes_token"].fillna("").astype(str).str.strip()

target_ids = set(df["market_id"])

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

window_start = START

while window_start < END:
    window_end = min(window_start + timedelta(days=5), END)

    start_ts = int(window_start.timestamp())
    end_ts = int(window_end.timestamp())

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

                # Exclude any API points outside this requested window.
                if not start_ts <= timestamp < end_ts:
                    continue

                observation_date = datetime.fromtimestamp(
                    timestamp, timezone.utc
                ).date()

                if not START.date() <= observation_date < END.date():
                    continue
                if observation_date not in MISSING_DATES:
                    continue
                recovered.append({
                    "market_id": market_id,
                    "date": str(observation_date),
                    "probability": float(item["p"]) * 100,
                    "yes_token": token_id,
                })

        except Exception as exc:
            errors.append((market_id, str(window_start.date()), str(exc)))

        if i % 100 == 0:
            print(
                f"{window_start.date()}: checked {i}/{len(targets)} markets"
            )

        # Be polite to the API.
        time.sleep(0.03)

    print(
        f"Finished window {window_start.date()} to {window_end.date()}"
    )
    window_start = window_end

result = pd.DataFrame(recovered)

if not result.empty:
    result = result.drop_duplicates(["market_id", "date"])

    if __import__("os").path.exists(OUTPUT_FILE):
        existing = pd.read_csv(OUTPUT_FILE)
        result = pd.concat([existing, result], ignore_index=True)
        result = result.drop_duplicates(
            ["market_id", "date"],
            keep="last",
        )

    result.to_csv(OUTPUT_FILE, index=False)

print("\nRecovery check complete.")
print("Markets checked:", len(targets))
print("Observations recovered:", len(result))
print("Markets with observations:", result["market_id"].nunique()
      if not result.empty else 0)
print("Markets with API errors:", len(set(x[0] for x in errors)))
print("Total API errors:", len(errors))
print("Output:", OUTPUT_FILE if not result.empty else "No file created")

if errors:
    print("\nFirst 10 errors:")
    for error in errors[:10]:
        print(error)
