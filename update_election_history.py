import logging

logger = logging.getLogger(__name__)


from polymarket_elections import (
    get_election_markets,
    prepare_election_markets,
    capture_and_update_election_history,
)

def main():
    logger.info("Fetching current Polymarket election markets...")

    markets = get_election_markets()

    if not markets:
        logger.warning("No markets were retrieved. History was not updated.")
        return

    logger.info("Retrieved %s markets.", len(markets))

    election_df = prepare_election_markets(markets)

    for market in markets:
        if "Abigail Spanberger" in market.get("question", ""):
            print(
                "Question:", market.get("question"),
                "\nMarket ID:", market.get("id"),
                "\nToken IDs:", market.get("clobTokenIds"),
                "\nOutcomes:", market.get("outcomes")
            )


    if election_df.empty:
        logger.warning("No eligible election markets were prepared.")
        return

    logger.info("Prepared %s election markets.", len(election_df))
    ##logger.info("Updating historical data...")

    ##history_df = capture_and_update_election_history(election_df)

    ##logger.info("Update complete. Historical records: %s", len(history_df))
    ##logger.info("File: election_market_history.csv")


if __name__ == "__main__":
    main()
