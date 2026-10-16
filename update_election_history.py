
from polymarket_elections import (
    get_election_markets,
    prepare_election_markets,
    capture_and_update_election_history,
)

def main():
    print("Fetching current Polymarket election markets...")

    markets = get_election_markets()

    if not markets:
        print("No markets were retrieved. History was not updated.")
        return

    print(f"Retrieved {len(markets)} markets.")

    election_df = prepare_election_markets(markets)

    if election_df.empty:
        print("No eligible election markets were prepared.")
        return

    print(f"Prepared {len(election_df)} election markets.")
    print("Updating historical data...")

    history_df = capture_and_update_election_history(election_df)

    print(f"Update complete. Historical records: {len(history_df)}")
    print("File: election_market_history.csv")


if __name__ == "__main__":
    main()
