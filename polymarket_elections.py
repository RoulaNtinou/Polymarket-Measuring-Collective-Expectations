import requests
import json
import pandas as pd
import numpy as np
import time
import logging
import streamlit as st

logging.basicConfig(
    filename="election_history.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)



ELECTION_TYPES = [
    "US Presidential",
    "US Midterms",
    "US Senate",
    "US House",
    "Global Elections"
]

url = "https://gamma-api.polymarket.com/markets"

params = {
    "limit": 100,
    "active": True
}

response = requests.get(url, params=params)
response.raise_for_status()

markets = response.json()


def get_price_history(token, days=7, chunk_days=7):

    history_url = "https://clob.polymarket.com/prices-history"

    # ------------------------------------------------
    # We request a little extra time because the API
    # works with timestamps while we want calendar days.
    # ------------------------------------------------

    end_ts = int(time.time())

    start_ts = end_ts - ((days + 1) * 24 * 60 * 60)

    all_history = []

    current_start = start_ts

    while current_start < end_ts:

        current_end = min(
            current_start + (chunk_days * 24 * 60 * 60),
            end_ts
        )

        history_params = {
            "market": token,
            "startTs": current_start,
            "endTs": current_end
        }

        try:

            response = requests.get(
                history_url,
                params=history_params,
                timeout=30
            )

            if response.status_code != 200:
                current_start = current_end
                continue

            data = response.json()

            history = data.get("history", [])

            if history:
                all_history.extend(history)

        except requests.RequestException:
            pass

        current_start = current_end

    # ------------------------------------------------
    # No history found
    # ------------------------------------------------

    if not all_history:

        return pd.DataFrame(
            columns=["date", "probability"]
        )

    # ------------------------------------------------
    # Convert to DataFrame
    # ------------------------------------------------

    history_df = pd.DataFrame(all_history)

    if "t" not in history_df.columns or "p" not in history_df.columns:

        return pd.DataFrame(
            columns=["date", "probability"]
        )

    # ------------------------------------------------
    # Convert timestamp to date
    # ------------------------------------------------

    history_df["date"] = pd.to_datetime(
        history_df["t"],
        unit="s",
        utc=True
    ).dt.tz_localize(None)

    history_df["probability"] = (
        pd.to_numeric(history_df["p"], errors="coerce") * 100
    )

    history_df = history_df.dropna(
        subset=["date", "probability"]
    )

    # ------------------------------------------------
    # Remove duplicate timestamps
    # ------------------------------------------------

    history_df = (
        history_df
        .drop_duplicates(subset=["t"])
        .sort_values("date")
    )

    # ------------------------------------------------
    # Convert to daily probability
    #
    # Last available price of each calendar day
    # ------------------------------------------------

    daily_df = (
        history_df
        .set_index("date")["probability"]
        .resample("D")
        .last()
        .dropna()
        .reset_index()
    )

    # ------------------------------------------------
    # Keep EXACTLY the requested number of days
    # ------------------------------------------------

    if len(daily_df) > days:
        daily_df = daily_df.tail(days).reset_index(drop=True)

    return daily_df

def get_election_markets():

    url = "https://gamma-api.polymarket.com/markets"

    all_markets = []
    offset = 0
    limit = 100

    while True:

        params = {
            "limit": limit,
            "offset": offset,
            "active": True
        }

        response = requests.get(
            url,
            params=params
        )

        if response.status_code == 422:
            print(f"API stopped pagination at offset {offset}")
            break

        response.raise_for_status()

        markets = response.json()

        if not markets:
            break

        all_markets.extend(markets)

        print(
            f"Retrieved {len(markets)} markets "
            f"(total: {len(all_markets)})"
        )

        if len(markets) < limit:
            break

        offset += limit

    election_markets = []

    for market in all_markets:

        question = market.get("question", "")
        event_title = market.get("eventTitle", "")

        election_type = classify_election(
            question,
            event_title
)

        if election_type is not None:

            market["election_type"] = election_type

            election_markets.append(market)

    # -------------------------
    # Summary output
    # -------------------------

    print(
        f"\nAPI stopped pagination at offset {offset}"
    )

    print(
        f"Total markets retrieved: {len(all_markets)}"
    )

    print(
        f"Election markets found: {len(election_markets)}"
    )

    return election_markets




def get_election_event(question):

    text = question.lower()

    if "2028 us presidential election" in text:
        return "2028 US Presidential Election"

    if "2028 democratic presidential nomination" in text:
        return "2028 Democratic Presidential Nomination"

    if "2028 republican presidential nomination" in text:
        return "2028 Republican Presidential Nomination"

    return question


def get_election_country(question, election_type):
    """
    Identify the country/region associated with an election market.
    """

    q = question.lower()

    # ------------------------------------------------
    # US FEDERAL ELECTIONS
    # ------------------------------------------------

    if election_type == "US Presidential":
        return "United States"

    if election_type in ["US Midterms", "US House"]:
        return "United States"

    # ------------------------------------------------
    # US STATE / LOCAL / CONGRESSIONAL DISTRICTS
    # ------------------------------------------------

    us_states = {
        "alabama": "Alabama",
        "alaska": "Alaska",
        "arizona": "Arizona",
        "arkansas": "Arkansas",
        "california": "California",
        "colorado": "Colorado",
        "connecticut": "Connecticut",
        "delaware": "Delaware",
        "florida": "Florida",
        "georgia": "Georgia",
        "hawaii": "Hawaii",
        "idaho": "Idaho",
        "illinois": "Illinois",
        "indiana": "Indiana",
        "iowa": "Iowa",
        "kansas": "Kansas",
        "kentucky": "Kentucky",
        "louisiana": "Louisiana",
        "maine": "Maine",
        "maryland": "Maryland",
        "massachusetts": "Massachusetts",
        "michigan": "Michigan",
        "minnesota": "Minnesota",
        "mississippi": "Mississippi",
        "missouri": "Missouri",
        "montana": "Montana",
        "nebraska": "Nebraska",
        "nevada": "Nevada",
        "new hampshire": "New Hampshire",
        "new jersey": "New Jersey",
        "new mexico": "New Mexico",
        "new york": "New York",
        "north carolina": "North Carolina",
        "north dakota": "North Dakota",
        "ohio": "Ohio",
        "oklahoma": "Oklahoma",
        "oregon": "Oregon",
        "pennsylvania": "Pennsylvania",
        "rhode island": "Rhode Island",
        "south carolina": "South Carolina",
        "south dakota": "South Dakota",
        "tennessee": "Tennessee",
        "texas": "Texas",
        "utah": "Utah",
        "vermont": "Vermont",
        "virginia": "Virginia",
        "washington": "Washington",
        "west virginia": "West Virginia",
        "wisconsin": "Wisconsin",
        "wyoming": "Wyoming"
    }

    # ------------------------------------------------
    # US CONGRESSIONAL DISTRICTS
    # Examples:
    # AZ-02
    # MA-06
    # NH-01
    # FL-19
    # MN-05
    # ------------------------------------------------

    district_to_state = {
        "al": "Alabama",
        "ak": "Alaska",
        "az": "Arizona",
        "ar": "Arkansas",
        "ca": "California",
        "co": "Colorado",
        "ct": "Connecticut",
        "de": "Delaware",
        "fl": "Florida",
        "ga": "Georgia",
        "hi": "Hawaii",
        "id": "Idaho",
        "il": "Illinois",
        "in": "Indiana",
        "ia": "Iowa",
        "ks": "Kansas",
        "ky": "Kentucky",
        "la": "Louisiana",
        "me": "Maine",
        "md": "Maryland",
        "ma": "Massachusetts",
        "mi": "Michigan",
        "mn": "Minnesota",
        "ms": "Mississippi",
        "mo": "Missouri",
        "mt": "Montana",
        "ne": "Nebraska",
        "nv": "Nevada",
        "nh": "New Hampshire",
        "nj": "New Jersey",
        "nm": "New Mexico",
        "ny": "New York",
        "nc": "North Carolina",
        "nd": "North Dakota",
        "oh": "Ohio",
        "ok": "Oklahoma",
        "or": "Oregon",
        "pa": "Pennsylvania",
        "ri": "Rhode Island",
        "sc": "South Carolina",
        "sd": "South Dakota",
        "tn": "Tennessee",
        "tx": "Texas",
        "ut": "Utah",
        "vt": "Vermont",
        "va": "Virginia",
        "wa": "Washington",
        "wv": "West Virginia",
        "wi": "Wisconsin",
        "wy": "Wyoming"
    }

    import re

    # Look for patterns such as AZ-02, MA-06, NH-01
    district_match = re.search(
        r'\b([a-z]{2})[-\s](\d{1,2})\b',
        q
    )

    if district_match:

        state_abbreviation = district_match.group(1)

        if state_abbreviation in district_to_state:

            state_name = district_to_state[state_abbreviation]

            return f"United States - {state_name}"

    # ------------------------------------------------
    # US STATE / LOCAL ELECTIONS
    # ------------------------------------------------

    if election_type == "US State/Local":

        for state_key, state_name in us_states.items():

            if state_key in q:
                return f"United States - {state_name}"

        # Major US cities that may appear without state name
        us_cities = {
            "los angeles": "California",
            "new york city": "New York",
            "chicago": "Illinois",
            "houston": "Texas",
            "phoenix": "Arizona",
            "philadelphia": "Pennsylvania",
            "san antonio": "Texas",
            "san diego": "California",
            "dallas": "Texas",
            "austin": "Texas",
            "boston": "Massachusetts",
            "seattle": "Washington",
            "denver": "Colorado",
            "miami": "Florida",
            "atlanta": "Georgia"
        }

        for city, state in us_cities.items():

            if city in q:
                return f"United States - {state}"

        return "United States - Other"

    # ------------------------------------------------
    # GLOBAL ELECTIONS
    # ------------------------------------------------

    if election_type == "Global Elections":

        # Brazil
        if (
            "brazil" in q
            or "brasileir" in q
            or "lula" in q
            or "bolsonaro" in q
        ):
            return "Brazil"

        # France
        if (
            "france" in q
            or "french" in q
            or "français" in q
            or "macron" in q
            or "le pen" in q
            or "lecornu" in q
        ):
            return "France"

        # Germany
        if (
            "germany" in q
            or "german" in q
            or "berlin" in q
            or "merz" in q
            or "cdu" in q
            or "spd" in q
            or "afd" in q
        ):
            return "Germany"

        # Israel
        if "israel" in q or "israeli" in q:
            return "Israel"

        # Sweden
        if (
            "sweden" in q
            or "swedish" in q
        ):
            return "Sweden"

        # Latvia
        if (
            "latvia" in q
            or "latvian" in q
        ):
            return "Latvia"

        # Canada / Quebec
        if (
            "québec" in q
            or "quebec" in q
            or "parti québécois" in q
        ):
            return "Canada - Quebec"

        if "canada" in q or "canadian" in q:
            return "Canada"

        # Somaliland
        if "somaliland" in q:
            return "Somaliland"

        # Morocco
        if (
            "morocco" in q
            or "moroccan" in q
            or "akhannouch" in q
        ):
            return "Morocco"

        # Guinea-Bissau
        if (
            "guinea-bissau" in q
            or "guinea bissau" in q
        ):
            return "Guinea-Bissau"

        # Taiwan
        if (
            "taiwan" in q
            or "taiwanese" in q
            or "kuomintang" in q
            or "(kmt)" in q
            or "(dpp)" in q
            or "democratic progressive party" in q
        ):
            return "Taiwan"

        # Ukraine
        if (
            "ukraine" in q
            or "ukrainian" in q
            or "zelenskyy" in q
        ):
            return "Ukraine"

        # Russia
        if (
            "russia" in q
            or "russian" in q
            or "putin" in q
        ):
            return "Russia"

        # Argentina
        if (
            "argentina" in q
            or "argentine" in q
            or "milei" in q
        ):
            return "Argentina"

        # Spain
        if (
            "spain" in q
            or "spanish" in q
            or "pedro sánchez" in q
            or "pedro sanchez" in q
        ):
            return "Spain"

        # Italy
        if "italy" in q or "italian" in q:
            return "Italy"

        # India
        if "india" in q or "indian" in q:
            return "India"

        # Japan
        if "japan" in q or "japanese" in q:
            return "Japan"

        # South Korea
        if (
            "south korea" in q
            or "south korean" in q
            or "korea" in q
        ):
            return "South Korea"

        # North Korea
        if (
            "north korea" in q
            or "kim jong" in q
        ):
            return "North Korea"

        # Democratic Republic of Congo
        if (
            "drc" in q
            or "democratic republic of congo" in q
            or "tshisekedi" in q
        ):
            return "Democratic Republic of the Congo"

        # Republic of the Congo
        if (
            "republic of the congo" in q
            or "nguesso" in q
        ):
            return "Republic of the Congo"

        # Central African Republic
        if (
            "central african republic" in q
            or "car national assembly" in q
        ):
            return "Central African Republic"

        # ------------------------------------------------
        # US LOCATION APPEARING INSIDE GLOBAL MARKETS
        # ------------------------------------------------

        if "los angeles" in q:
            return "United States - Los Angeles"

        # US state names can still appear in markets
        # that Polymarket has labelled Global Elections.
        for state_key, state_name in us_states.items():

            if state_key in q:

                political_keywords = [
                    "election",
                    "elected",
                    "governor",
                    "senate",
                    "senator",
                    "house",
                    "representative",
                    "nominee",
                    "primary",
                    "mayor",
                    "governorship",
                    "race",
                    "district",
                    "seat"
                ]

                if any(keyword in q for keyword in political_keywords):
                    return f"United States - {state_name}"

        return "Other"

    # ------------------------------------------------
    # OTHER / UNKNOWN
    # ------------------------------------------------

    return "Other"



def classify_market_category(question, election_type):

    q = question.lower().strip()



    # ------------------------------------------------
    # SPORTS
    # ------------------------------------------------
    sports_keywords = [
        "ballon d'or",
        "lol worlds",
        "lck",
        "ufc",
        "nba",
        "nfl",
        "mlb",
        "nhl",
        "fifa",
        "world cup",
        "super bowl",
        "formula 1",
        "f1",
        "champion"
    ]

    if any(keyword in q for keyword in sports_keywords):
        return "Sports"

    # ------------------------------------------------
    # US ELECTIONS
    # ------------------------------------------------
    if election_type == "US Presidential":
        return "US Elections"

    if election_type in [
        "US Midterms",
        "US House",
        "US State/Local"
    ]:
        return "US Elections"

    # ------------------------------------------------
    # GLOBAL ELECTIONS
    # ------------------------------------------------
    election_keywords = [
        "presidential election",
        "parliamentary election",
        "general election",
        "presidential nomination",
        "win the most seats",
        "governor",
        "senate race",
        "senate nominee",
        "senate primary",
        "mayoral election",
        "mayor",
        "democratic primary",
        "republican primary",
        "qualify for",
        "runoff",
        "nominee for senate"
    ]

    if any(keyword in q for keyword in election_keywords):
        return "Global Election"
    if (
    "election" in q
    and any(
        word in q
        for word in [
            "presidential",
            "parliamentary",
            "governor",
            "senate",
            "mayor",
            "nominee",
            "party"
        ]
    )
):
     return "Global Election"

    # ------------------------------------------------
    # GEOPOLITICAL
    # ------------------------------------------------
    geopolitical_keywords = [
        "peace deal",
        "peace treaty",
        "peace referendum",
        "nato",
        "invade",
        "military clash",
        "strike",
        "cede territory",
        "cede",
        "give up territory",
        "russia",
        "ukraine",
        "nuclear",
        "nuke",
        "trade deal",
        "recognize palestine",
        "recognizes palestine",
        "recognise palestine",
        "recognizes russian sovereignty",
        "join nato",
        "annex",
        "abraham accords",
        "normalize relations",
        "normalise relations",
        "recognize somaliland",
        "recognise somaliland"
    ]

    if any(keyword in q for keyword in geopolitical_keywords):
        return "Geopolitical"

    # ------------------------------------------------
    # POLITICAL EVENTS
    # ------------------------------------------------
    political_keywords = [
        "visit",
        "meet with",
        "meet next",
        "out as president",
        "out as chancellor",
        "out as pm",
        "out as prime minister",
        "prime minister",
        "coalition",
        "government",
        "secretary general of the united nations",
        "supreme leader",
        "president before",
        "pm by",
        "chancellor by"
    ]

    if any(keyword in q for keyword in political_keywords):
        return "Political Event"

    # ------------------------------------------------
    # DEFAULT
    # ------------------------------------------------
    return "Other"



import re


def extract_candidate(question, election_type=None):

    if not question:
        return "other", None

    q = question.strip()

    # Work with lowercase only for classification.
    # Keep the original q for extracting the actual candidate name.
    q_lower = q.lower()



    # ============================================================
    # 1. AGGREGATE / NON-CANDIDATE MARKETS
    # ============================================================

    aggregate_patterns = [

        # Generic candidate / outcome markets
        r"\bany presidential candidate\b",
        r"\bany candidate\b",
        r"\ban independent win\b",

        # Control of institutions
        r"\bcontrol the house\b",
        r"\bcontrol the senate\b",

        # Number of seats / governors / members
        r"\bhold \d+ or more\b",
        r"\bhold \d+ or fewer\b",
        r"\bhold exactly\b",
        r"\bhold between\b",
        r"\bhold below\b",
        r"\bhold fewer\b",
        r"\bhold more\b",
        r"\bnumber of .* (members|seats|governors)\b",

        # Retirement / counts
        r"\bnumber of .* retire\b",

        # Wealth / policy / referendum type questions
        r"\bwealth tax\b",
        r"\bpasses in\b",
        r"\bpass(es)? in\b",
    ]

    if any(re.search(pattern, q_lower) for pattern in aggregate_patterns):
        return "aggregate", None

    # ============================================================
    # 2. PARTY MARKETS
    # ============================================================

    if (
        q_lower.startswith("will the democrats ")
        or q_lower.startswith("will the republicans ")
    ):
        return "party", None

    # ============================================================
    # 3. NON-PERSON / GENERIC MARKETS
    # ============================================================

    generic_patterns = [

        r"\bthe winner\b",
        r"\bwho will win\b",
        r"\bwhich party\b",
        r"\bwhat party\b",
        r"\bwill .* election be\b",
    ]

    if any(re.search(pattern, q_lower) for pattern in generic_patterns):
        return "aggregate", None

    # ============================================================
    # 4. REMOVE "Will"
    # ============================================================

    candidate_text = re.sub(
        r"^Will\s+",
        "",
        q,
        flags=re.IGNORECASE
    ).strip()



    # ============================================================
    # 5. CANDIDATE ACTIONS
    #
    # We remove the action + everything after it.
    # This works across Brazil and US markets.
    # ============================================================

    action_patterns = [

        # "Aziz Akhannouch out as Morocco Prime Minister..."
        r"\s+out as\b",

        # "Tarcisio de Freitas win the..."
        r"\s+win\b",

        # "Tarcisio qualify for..."
        r"\s+qualify\b",

        # "Tarcisio advance from..."
        r"\s+advance\b",

        # "Tarcisio be the Democratic nominee..."
        r"\s+be the\b",

        # "Tarcisio become..."
        r"\s+become\b",

        # "Tarcisio win..."
        r"\s+wins?\b",
    ]

    positions = []

    for pattern in action_patterns:

        match = re.search(
            pattern,
            candidate_text,
            flags=re.IGNORECASE
        )

        if match:
            positions.append(match.start())

    # Take the first candidate-action occurrence
    if positions:

        candidate = candidate_text[:min(positions)].strip()

        # Remove trailing punctuation
        candidate = candidate.rstrip(" ?!.,:")

        # --------------------------------------------------------
        # Validate that this looks like a person name
        # --------------------------------------------------------

        if candidate and not _looks_like_non_candidate(candidate):

            return "candidate", candidate

    # ============================================================
    # 6. FALLBACK
    # ============================================================

    return "other", None


def _looks_like_non_candidate(candidate):

    candidate_lower = candidate.lower().strip()

    non_candidate_words = [

        "the",
        "any",
        "an independent",
        "independent",
        "democratic party",
        "republican party",
        "democrats",
        "republicans",
        "democrat",
        "republican",
    ]

    if candidate_lower in non_candidate_words:
        return True

    # Avoid returning things such as:
    # "Democratic Party"
    # "Republican Party"
    if " party" in candidate_lower:
        return True

    return False


def normalize_candidate_name(candidate):

    if not candidate:
        return None

    candidate = candidate.strip()

    # Normalize common punctuation/spelling variations
    candidate_aliases = {
        "Tarcisio de Frietas": "Tarcisio de Freitas",
    }

    # Normalize J.D. Vance / JD Vance
    if candidate.lower().replace(".", "").replace(" ", "") == "jdvance":
        return "JD Vance"

    return candidate_aliases.get(
        candidate,
        candidate
    )


def prepare_election_markets(markets):

    election_data = []

    for market in markets:

        question = market.get("question", "")

        # ------------------------------------------------
        # Event information
        # ------------------------------------------------

        event_title = market.get("eventTitle", "")

        if not event_title:
            event_title = question

        # ------------------------------------------------
        # Election classification
        # ------------------------------------------------

        election_type = classify_election(
            question,
            event_title
        )

        election_country = get_election_country(
            question,
            election_type
        )

        market_category = classify_market_category(
            question,
            election_type
        )

        # ------------------------------------------------
        # Token IDs
        # ------------------------------------------------

        clob_token_ids = market.get("clobTokenIds")

        if not clob_token_ids:
            continue

        try:
            token_ids = json.loads(clob_token_ids)
        except (TypeError, json.JSONDecodeError):
            continue

        if not token_ids:
            continue

        yes_token = token_ids[0]

        # ------------------------------------------------
        # Candidate extraction
        # ------------------------------------------------

        market_type, candidate = extract_candidate(
            question,
            election_type
        )

        candidate = normalize_candidate_name(candidate)

        # ------------------------------------------------
        # Validation metadata
        # ------------------------------------------------

        condition_id = market.get("conditionId")

        neg_risk = market.get("negRisk")

        neg_risk_market_id = market.get("negRiskMarketID")

        active = market.get("active")

        closed = market.get("closed")

        accepting_orders = market.get("acceptingOrders")

        outcomes = market.get("outcomes")

        outcome_prices = market.get("outcomePrices")

        # ------------------------------------------------
        # Store
        # ------------------------------------------------

        election_data.append({

            "election_type": election_type,
            "election_country": election_country,
            "market_category": market_category,

            "event": event_title,
            "market_name": question,

            "market_type": market_type,
            "candidate": candidate,

            "market_id": market.get("id"),
            "condition_id": condition_id,

            "yes_token": yes_token,

            # Validation
            "negRisk": neg_risk,
            "negRiskMarketID": neg_risk_market_id,
            "active": active,
            "closed": closed,
            "accepting_orders": accepting_orders,
            "outcomes": outcomes,
            "outcome_prices": outcome_prices,

            "volume": float(
                market.get("volume", 0) or 0
            ),

            "liquidity": float(
                market.get("liquidity", 0) or 0
            )
        })

    return pd.DataFrame(election_data)



def get_all_election_history(election_df, days=7):

    all_history = []

    total_markets = len(election_df)

    print(f"Getting history for {total_markets} markets...")

    # ------------------------------------------------
    # Metadata columns captured in prepare_election_markets
    # ------------------------------------------------

    metadata_columns = [
        "election_type",
        "election_country",
        "market_category",
        "event",
        "market_name",
        "market_type",
        "candidate",
        "market_id",
        "condition_id",
        "yes_token",

        # Validation fields
        "negRisk",
        "negRiskMarketID",
        "active",
        "closed",
        "accepting_orders",
        "outcomes",
        "outcome_prices",

        # Market statistics
        "volume",
        "liquidity"
    ]

    # ------------------------------------------------
    # Get history for each market
    # ------------------------------------------------

    for i, (_, row) in enumerate(
        election_df.iterrows(),
        start=1
    ):

        candidate = row["candidate"]

        print(
            f"[{i}/{total_markets}] {candidate}"
        )

        daily_df = get_price_history(
            row["yes_token"],
            days=days
        )

        if daily_df.empty:

            print("  -> no history")

            continue

        print(
            f"  -> {len(daily_df)} daily observations"
        )

        # ------------------------------------------------
        # Add market metadata to every daily observation
        # ------------------------------------------------

        for col in metadata_columns:

            if col in row.index:

                daily_df[col] = row[col]

        # ------------------------------------------------
        # Store
        # ------------------------------------------------

        all_history.append(daily_df)

    # ------------------------------------------------
    # No history at all
    # ------------------------------------------------

    if not all_history:

        return pd.DataFrame(
            columns=[
                "date",
                "probability"
            ] + metadata_columns
        )

    # ------------------------------------------------
    # Combine all markets
    # ------------------------------------------------

    history_df = pd.concat(
        all_history,
        ignore_index=True
    )

    # ------------------------------------------------
    # Ensure correct ordering
    # ------------------------------------------------

    history_df = (
        history_df
        .sort_values(
            ["date", "candidate"]
        )
        .reset_index(drop=True)
    )

    return history_df


def calculate_kpis(df):
    """
    Calculate KPIs for a filtered election market group.

    Parameters
    ----------
    df : pd.DataFrame
        Historical market data, optionally filtered by:
        election_type and/or election_subtype.

    Returns
    -------
    dict
        Dictionary containing:
        - latest_date
        - leader
        - leader_probability
        - biggest_gainer
        - biggest_gainer_change
        - total_volume
        - total_markets
    """

    if df is None or df.empty:
        return {}

    data = df.copy()

    # ============================================================
    # 1. ENSURE CORRECT DATA TYPES
    # ============================================================

    data["date"] = pd.to_datetime(
        data["date"],
        errors="coerce"
    )

    data["probability"] = pd.to_numeric(
        data["probability"],
        errors="coerce"
    )

    data["volume"] = pd.to_numeric(
        data["volume"],
        errors="coerce"
    )

    data["market_id"] = (
        data["market_id"]
        .astype(str)
        .str.strip()
    )

    # Remove rows without valid dates
    data = data.dropna(
        subset=["date"]
    )

    if data.empty:
        return {}

    # ============================================================
    # 2. LATEST SNAPSHOT
    # ============================================================

    latest_date = data["date"].max()

    latest_data = data[
        data["date"] == latest_date
    ].copy()

    # One row per market
    latest_data = latest_data.drop_duplicates(
        subset=["market_id"]
    )

    # ============================================================
    # 3. CURRENT LEADER
    # ============================================================

    valid_probability = latest_data.dropna(
        subset=["probability"]
    )

    if not valid_probability.empty:

        leader = valid_probability.loc[
            valid_probability["probability"].idxmax()
        ]

        leader_name = leader["market_name"]
        leader_probability = float(
            leader["probability"]
        )

    else:

        leader_name = None
        leader_probability = None

    # ============================================================
    # 4. STARTING SNAPSHOT
    # ============================================================

    start_date = data["date"].min()

    start_data = data[
        data["date"] == start_date
    ].copy()

    start_data = start_data.drop_duplicates(
        subset=["market_id"]
    )

    # ============================================================
    # 5. CALCULATE START → LATEST CHANGES
    # ============================================================

    start_probabilities = (
        start_data[
            [
                "market_id",
                "market_name",
                "probability"
            ]
        ]
        .rename(
            columns={
                "market_name": "start_market_name",
                "probability": "start_probability"
            }
        )
    )

    latest_probabilities = (
        latest_data[
            [
                "market_id",
                "market_name",
                "probability"
            ]
        ]
        .rename(
            columns={
                "market_name": "latest_market_name",
                "probability": "latest_probability"
            }
        )
    )

    changes_df = start_probabilities.merge(
        latest_probabilities,
        on="market_id",
        how="inner"
    )

    changes_df["change"] = (
        changes_df["latest_probability"]
        - changes_df["start_probability"]
    )

    # ============================================================
    # 6. BIGGEST GAINER
    # ============================================================

    valid_changes = changes_df.dropna(
        subset=["change"]
    )

    if not valid_changes.empty:

        biggest_gainer = valid_changes.loc[
            valid_changes["change"].idxmax()
        ]

        biggest_gainer_name = (
            biggest_gainer["latest_market_name"]
        )

        biggest_gainer_change = float(
            biggest_gainer["change"]
        )

    else:

        biggest_gainer_name = None
        biggest_gainer_change = None

    # ============================================================
    # 7. TOTAL LATEST VOLUME
    # ============================================================

    total_volume = (
        latest_data["volume"]
        .fillna(0)
        .sum()
    )

    # ============================================================
    # 8. TOTAL MARKETS
    # ============================================================

    total_markets = (
        latest_data["market_id"]
        .nunique()
    )

    # ============================================================
    # 9. RETURN KPIs
    # ============================================================

    return {
        "latest_date": latest_date,
        "leader": leader_name,
        "leader_probability": leader_probability,
        "biggest_gainer": biggest_gainer_name,
        "biggest_gainer_change": biggest_gainer_change,
        "total_volume": float(total_volume),
        "total_markets": int(total_markets)
    }


def classify_election(question, event_title=""):
    """
    Classify a market into an election type.

    Categories:
        - US Presidential
        - US Midterms
        - US House
        - US State/Local
        - Global Elections
        - Other
    """

    import re

    q = str(question).lower()
    e = str(event_title).lower()
    text = f"{q} {e}"

    # ============================================================
    # REFERENCE LISTS
    # ============================================================

    foreign_countries = [
        "brazil",
        "france",
        "germany",
        "berlin",
        "israel",
        "sweden",
        "latvia",
        "québec",
        "quebec",
        "somaliland",
        "morocco",
        "guinea-bissau",
        "ukraine",
        "russia",
        "argentina",
        "taiwan",
        "central african republic",
        "republic of the congo",
        "democratic republic of the congo",
        "drc",
    ]

    us_states = [
        "alabama",
        "alaska",
        "arizona",
        "arkansas",
        "california",
        "colorado",
        "connecticut",
        "delaware",
        "florida",
        "georgia",
        "hawaii",
        "idaho",
        "illinois",
        "indiana",
        "iowa",
        "kansas",
        "kentucky",
        "louisiana",
        "maine",
        "maryland",
        "massachusetts",
        "michigan",
        "minnesota",
        "mississippi",
        "missouri",
        "montana",
        "nebraska",
        "nevada",
        "new hampshire",
        "new jersey",
        "new mexico",
        "new york",
        "north carolina",
        "north dakota",
        "ohio",
        "oklahoma",
        "oregon",
        "pennsylvania",
        "rhode island",
        "south carolina",
        "south dakota",
        "tennessee",
        "texas",
        "utah",
        "vermont",
        "virginia",
        "washington",
        "west virginia",
        "wisconsin",
        "wyoming",
    ]

    # ============================================================
    # 1. US CONGRESSIONAL DISTRICTS — HIGHEST PRIORITY
    # ============================================================
    #
    # Examples:
    #   AZ-02
    #   MA-06
    #   NH-01
    #   FL-19
    #   MN-05
    #
    # These are US House districts, regardless of whether the
    # question says "Democratic", "Republican", "nominee", "seat",
    # "win", etc.
    #
    # IMPORTANT: this must happen BEFORE global election detection.

    district_pattern = r"\b(?:[a-z]{2})[-–]\d{1,2}\b"

    if re.search(district_pattern, text, flags=re.IGNORECASE):
        return "US Midterms"

    # Also catch explicit congressional-district wording
    congressional_district_patterns = [
        r"\b[a-z]{2}\s+congressional district\b",
        r"\bcongressional district\s+\d+\b",
        r"\b\d+(?:st|nd|rd|th)\s+congressional district\b",
    ]

    if any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in congressional_district_patterns
    ):
        return "US Midterms"

    # ============================================================
    # 2. EXPLICIT US Midterms MARKETS
    # ============================================================

    house_keywords = [
        "us house",
        "u.s. house",
        "united states house",
        "house of representatives",
        "house seat",
        "house election",
        "house race",
        "house nominee",
        "house representative",
        "representative for",
        "congressional election",
        "congressional race",
        "congressional seat",
        "congressional nominee",
    ]

    if any(keyword in text for keyword in house_keywords):

        # Avoid foreign contexts
        if not any(country in text for country in foreign_countries):
            return "US Midterms"

    # Specific US House nomination wording
    if (
        ("democratic nominee" in text or "republican nominee" in text)
        and (
            "house" in text
            or "representative" in text
            or "congress" in text
        )
    ):
        return "US Midterms"

    # ============================================================
    # 3. US PRESIDENTIAL ELECTION
    # ============================================================
    #
    # Be careful here:
    #
    # "Will Mike Pence announce a presidential run before 2027?"
    #
    # is NOT necessarily a US Presidential election market.
    #
    # We therefore require an actual US presidential election /
    # nomination context.

    us_presidential_patterns = [
        "2028 us presidential election",
        "2028 presidential election",
        "2028 united states presidential election",
        "2028 democratic presidential nomination",
        "2028 republican presidential nomination",
        "2028 democratic presidential nominee",
        "2028 republican presidential nominee",
        "win the 2028 presidential election",
        "win the 2028 democratic presidential nomination",
        "win the 2028 republican presidential nomination",
        "2028 presidential nominee",
        "2028 presidential nomination",
        "2028 president",
    ]

    if any(pattern in text for pattern in us_presidential_patterns):
        return "US Presidential"

    # Explicit US presidential election wording
    explicit_us_presidential = [
        "us presidential election",
        "u.s. presidential election",
        "united states presidential election",
        "us president election",
        "u.s. president election",
        "president of the united states election",
    ]

    if any(pattern in text for pattern in explicit_us_presidential):
        return "US Presidential"

    # ============================================================
    # 4. US MIDTERMS
    # ============================================================


    # Senate and House races are US Midterms,
    # even when a US state is mentioned in the question.
    if (
        "senate" in text
        or "senator" in text
        or "house of representatives" in text
        or "congressional" in text
    ):
        if not any(country in text for country in foreign_countries):
            return "US Midterms"

    midterm_keywords = [
        "2026 midterm",
        "2026 midterms",
        "2026 u.s. election",
        "2026 us election",
        "2026 election",
        "2026 election cycle",
        "2026 cycle",
        "senate election",
        "senate race",
        "senate seat",
        "senate nominee",
        "senate primary",
        "senator",
        "senate incumbents",
        "house incumbents",
        "house members",
        "senate members",
        "congressional election",
        "congressional race",
        "trifecta",
        "midterms",
        "midterm",
    ]

    if any(keyword in text for keyword in midterm_keywords):

        # Strong US indicators
        us_indicators = [
            "us",
            "u.s.",
            "united states",
            "senate",
            "senator",
            "house",
            "congress",
            "republican",
            "democratic",
            "democrat",
        ]

        if any(indicator in text for indicator in us_indicators):

            # Don't let an explicitly foreign election become a
            # US midterm market.
            if not any(country in text for country in foreign_countries):
                return "US Midterms"

    # ============================================================
    # 5. US STATE / LOCAL ELECTIONS
    # ============================================================


    # ------------------------------------------------------------
    # 2026 Governor general elections belong to US Midterms
    # ------------------------------------------------------------

    if (
        "governor" in text
        and "2026" in text
        and "primary" not in text
        and "nomination" not in text
        and "nominee" not in text
    ):
        return "US Midterms"

    us_local_keywords = [
        "governor",
        "governorship",
        "state election",
        "state elections",
        "mayor",
        "mayoral election",
        "mayoral race",
        "city election",
        "city elections",
        "local election",
        "local elections",
        "state legislature",
        "state senate",
        "state house",
        "county election",
        "county elections",
    ]

    # ------------------------------------------------------------
    # Los Angeles
    # ------------------------------------------------------------
    #
    # Los Angeles is US State/Local, not Global Elections.
    #
    # But require election/political context so that an unrelated
    # market merely mentioning Los Angeles isn't classified as an
    # election.

    if "los angeles" in text:
        if any(
            keyword in text
            for keyword in [
                "election",
                "elections",
                "mayor",
                "mayoral",
                "governor",
                "governorship",
                "race",
                "candidate",
                "nominee",
                "primary",
                "ballot",
                "seat",
                "win",
            ]
        ):
            return "US State/Local"

    # ------------------------------------------------------------
    # Major US cities
    # ------------------------------------------------------------

    us_cities = [
        "new york city",
        "nyc",
        "chicago",
        "houston",
        "phoenix",
        "philadelphia",
        "san antonio",
        "san diego",
        "dallas",
        "austin",
        "san jose",
        "jacksonville",
        "fort worth",
        "columbus",
        "charlotte",
        "seattle",
        "denver",
        "boston",
        "nashville",
        "detroit",
        "portland",
        "memphis",
        "las vegas",
        "baltimore",
        "milwaukee",
        "atlanta",
        "miami",
    ]

    if any(city in text for city in us_cities):
        if any(keyword in text for keyword in us_local_keywords):
            return "US State/Local"

    # ------------------------------------------------------------
    # US state + election/political context
    # ------------------------------------------------------------

    political_keywords = [
        "election",
        "elections",
        "elected",
        "governor",
        "governorship",
        "senate",
        "senator",
        "house",
        "representative",
        "nominee",
        "primary",
        "mayor",
        "mayoral",
        "race",
        "ballot",
        "seat",
        "candidate",
    ]

    if any(state in text for state in us_states):
        if any(keyword in text for keyword in political_keywords):

            if not any(
                country in text for country in foreign_countries
            ):
                return "US State/Local"

    # ------------------------------------------------------------
    # Explicit local/state terminology
    # ------------------------------------------------------------

    if any(keyword in text for keyword in us_local_keywords):

        if "governor" in text:
            if (
                "primary" not in text
                and "nomination" not in text
                and "nominee" not in text
            ):
                pass
            else:
                if not any(
                    country in text
                    for country in foreign_countries
                ):
                    return "US State/Local"

        else:
            if not any(
                country in text
                for country in foreign_countries
            ):
                return "US State/Local"

    # ============================================================
    # 6. GEOPOLITICAL MARKETS
    # ============================================================

    geopolitical_keywords = [
        "normalize relations",
        "peace deal",
        "join nato",
        "joins nato",
        "not to join nato",
        "give up",
        "cede territory",
        "military clash",
        "invade",
        "strike",
        "nuke",
        "nuclear",
        "recognize palestine",
        "recognizes palestine",
        "trade deal",
        "visit",
        "meet",
        "annex",
        "recognize russian sovereignty",
        "recognizes russian sovereignty",
        "limit size of armed forces",
        "peace parlay",
        "coalition break",
        "peace referendum",
        "abraham accords",
        "secretary general of the united nations",
        "recognize somaliland",
        "recognizes somaliland",
]

    geopolitical_leader_patterns = [
        "out as president",
        "out as president of",
        "out as chancellor",
        "out as supreme leader",
        "out as pm",
        "out as french pm",
]

    if any(keyword in text for keyword in geopolitical_keywords):
        return "Geopolitical"

    if any(pattern in text for pattern in geopolitical_leader_patterns):
        return "Geopolitical"



    # ============================================================
    # 7. GLOBAL ELECTIONS
    # ============================================================

    global_election_keywords = [
        "election",
        "elections",
        "presidential election",
        "french presidential election",
        "swedish parliamentary election",
        "president",
        "prime minister",
        "parliament",
        "parliamentary",
        "national assembly",
        "local elections",
        "state elections",
        "nominee",
        "government",
        "governor",
        "presidential nominee",
    ]

    # Only classify as Global Elections when there is BOTH:
    #   1. clear election/political context
    #   2. a foreign country/region
    #
    # US districts have already been caught above.

    foreign_election_patterns = [
    "french presidential election",
    "swedish parliamentary election",
]

    if (
        (
            any(keyword in text for keyword in global_election_keywords)
            and any(country in text for country in foreign_countries)
        )
        or any(pattern in text for pattern in foreign_election_patterns)
    ):
        return "Global Elections"
    # ============================================================
    # 7. DEFAULT
    # ============================================================

    return "Other"



def classify_election_country_region(event, election_type):
    """
    Classify an election market by country or region.

    US elections are grouped under United States.
    Global elections are classified using keywords in the event/question.
    """

    if not isinstance(event, str):
        return "Unknown"

    text = event.lower()

    # -------------------------
    # United States
    # -------------------------
    if election_type in ["US Presidential", "US Midterms", "US House"]:
        return "United States"

    # -------------------------
    # Global elections
    # -------------------------

    # Brazil
    if any(x in text for x in [
        "brazil",
        "brazilian",
        "bolsonaro",
        "lula da silva",
        "tarcisio de freitas",
        "tarcisio de frietas",
        "fernando haddad",
        "flávio bolsonaro",
        "flavio bolsonaro",
        "michelle bolsonaro",
        "eduardo bolsonaro",
        "renan santos",
        "ronaldo caiado",
        "romeu zema",
        "camilo santana",
        "geraldo alckmin",
        "eduardo leite",
        "aldo rebelo",
        "tereza cristina",
        "helder barbalho",
        "pablo marçal",
        "pablo marcal"
    ]):
        return "Brazil"

    # France
    if any(x in text for x in [
        "france",
        "french",
        "marine le pen",
        "jordan bardella",
        "éric zemmour",
        "eric zemmour",
        "édouard philippe",
        "edouard philippe",
        "xavier bertrand",
        "gabriel attal",
        "françois hollande",
        "francois hollande",
        "jean-luc mélenchon",
        "jean-luc melenchon",
        "marine tondelier",
        "olivier faure"
    ]):
        return "France"

    # Israel
    if any(x in text for x in [
        "israel",
        "israeli",
        "benjamin netanyahu",
        "naftali bennett",
        "yair lapid",
        "gadi eisenkot",
        "gadi eizenkot",
        "benny gantz",
        "avigdor lieberman",
        "yossi cohen",
        "yair golan",
        "itamar ben gvir",
        "gideon sa'ar",
        "gideon sa’ar",
        "yariv levin",
        "moshe feiglin",
        "ayelet shaked",
        "yoaz hendel",
        "israel katz",
        "nir barkat",
        "amir ohana",
        "gilad erdan"
    ]):
        return "Israel"

    # Canada / Quebec
    if any(x in text for x in [
        "quebec",
        "québec",
        "coalition avenir québec",
        "coalition avenir quebec",
        "parti québécois",
        "parti quebecois",
        "parti libéral du québec",
        "parti liberal du quebec",
        "québec solidaire",
        "quebec solidaire",
        "parti conservateur du québec",
        "parti conservateur du quebec",
        "parti vert du québec",
        "parti vert du quebec"
    ]):
        return "Canada - Quebec"

    # Sweden
    if any(x in text for x in [
        "sweden",
        "swedish",
        "swedish social democratic party",
        "sweden democrats",
        "moderate party",
        "centre party",
        "left party",
        "christian democrats",
        "green party",
        "liberals (l)"
    ]):
        return "Sweden"

    # Latvia
    if any(x in text for x in [
        "latvia",
        "latvian",
        "jaunā vienotība",
        "jauna vienotiba",
        "zaļo un zemnieku savienība",
        "zalo un zemnieku savieniba",
        "apvienotais saraksts",
        "nacionālā apvienība",
        "nacionala apvieniba",
        "stabilitātei",
        "latvija pirmajā vietā",
        "latvija pirmaja vieta",
        "progresīvie",
        "progresivie",
        "suverēnā vara",
        "suverena vara",
        "saskaņa",
        "saskana"
    ]):
        return "Latvia"

    # Guinea-Bissau
    if any(x in text for x in [
        "guinea-bissau",
        "guinea bissau",
        "umaro sissoco embalo",
        "mamadu iaia djalo",
        "honório augusto lopes",
        "honorio augusto lopes",
        "joão bernardo vieira",
        "joao bernardo vieira",
        "baciro djá",
        "baciro dja"
    ]):
        return "Guinea-Bissau"

    # Somaliland
    if any(x in text for x in [
        "somaliland",
        "kulmiye",
        "waddani",
        "justice and welfare party",
        "ucid"
    ]):
        return "Somaliland"

    # Morocco
    if any(x in text for x in [
        "morocco",
        "moroccan",
        "aziz akhannouch"
    ]):
        return "Morocco"

    # Greece
    if any(x in text for x in [
        "greece",
        "greek",
        "mitsotakis",
        "tsipras"
    ]):
        return "Greece"

    # Germany
    if any(x in text for x in [
        "germany",
        "german",
        "bundestag",
        "merz",
        "scholz"
    ]):
        return "Germany"

    # United Kingdom
    if any(x in text for x in [
        "united kingdom",
        "uk election",
        "british",
        "britain",
        "labour party",
        "conservative party"
    ]):
        return "United Kingdom"

    # Italy
    if any(x in text for x in [
        "italy",
        "italian",
        "meloni"
    ]):
        return "Italy"

    # Spain
    if any(x in text for x in [
        "spain",
        "spanish",
        "sánchez",
        "sanchez"
    ]):
        return "Spain"

    # -------------------------
    # Fallback
    # -------------------------
    return "Other / Unknown"






def get_country(event):
    event_lower = event.lower()

    if "brazil" in event_lower or "brazilian" in event_lower:
        return "Brazil"
    elif "french" in event_lower or "france" in event_lower:
        return "France"
    elif "israel" in event_lower or "israeli" in event_lower:
        return "Israel"
    elif "swedish" in event_lower or "sweden" in event_lower:
        return "Sweden"
    elif "latvian" in event_lower or "latvia" in event_lower:
        return "Latvia"
    elif "québec" in event_lower or "quebec" in event_lower:
        return "Quebec"
    elif "somaliland" in event_lower:
        return "Somaliland"
    elif "morocco" in event_lower or "morocco prime minister" in event_lower:
        return "Morocco"
    elif "guinea-bissau" in event_lower:
        return "Guinea-Bissau"
    elif "ukraine" in event_lower or "ukrainian" in event_lower:
        return "Ukraine"
    else:
        return "Other"


def create_election_group(df):
    df = df.copy()

    df["election_group"] = df["event"]

    # Brazil
    brazil_mask = df["election_country"].eq("Brazil")

    df.loc[
        brazil_mask & df["event"].str.contains(
            "Brazilian presidential election",
            case=False,
            na=False
        ),
        "election_group"
    ] = "2026 Brazilian presidential election"

    df.loc[
        brazil_mask & df["event"].str.contains(
            "presidential runoff",
            case=False,
            na=False
        ),
        "election_group"
    ] = "Brazil presidential runoff"

    df.loc[
        brazil_mask & df["event"].str.contains(
            "first round",
            case=False,
            na=False
        ),
        "election_group"
    ] = "Brazil presidential election — first round"

    # Israel
    israel_mask = df["election_country"].eq("Israel")

    df.loc[
        israel_mask & df["event"].str.contains(
            "next Prime Minister",
            case=False,
            na=False
        ),
        "election_group"
    ] = "Next Prime Minister of Israel"

    # Germany
    germany_mask = df["election_country"].eq("Germany")

    df.loc[
        germany_mask & df["event"].str.contains(
            "Berlin state elections",
            case=False,
            na=False
        ),
        "election_group"
    ] = "2026 Berlin state elections"

    # Latvia
    latvia_mask = df["election_country"].eq("Latvia")

    df.loc[
        latvia_mask & df["event"].str.contains(
            "Latvian parliamentary election",
            case=False,
            na=False
        ),
        "election_group"
    ] = "2026 Latvian parliamentary election"

    # Taiwan
    taiwan_mask = df["election_country"].eq("Taiwan")

    df.loc[
        taiwan_mask & df["event"].str.contains(
            "Taiwan local elections",
            case=False,
            na=False
        ),
        "election_group"
    ] = "2026 Taiwan local elections"

    # Somaliland
    somaliland_mask = df["election_country"].eq("Somaliland")

    df.loc[
        somaliland_mask & df["event"].str.contains(
            "Somaliland parliamentary election",
            case=False,
            na=False
        ),
        "election_group"
    ] = "Somaliland parliamentary election"

    return df



def capture_election_market(election_df, capture_date=None):
    """
    Capture a daily snapshot of election market data.

    Parameters
    ----------
    election_df : pd.DataFrame
        Output from prepare_election_markets().

    capture_date : str or None
        Date of the snapshot. If None, today's date is used.

    Returns
    -------
    pd.DataFrame
        Daily election market snapshot.
    """

    if election_df is None or election_df.empty:
        return pd.DataFrame()

    # ------------------------------------------------
    # Capture date
    # ------------------------------------------------

    if capture_date is None:
        capture_date = pd.Timestamp.now().normalize()
    else:
        capture_date = pd.to_datetime(capture_date).normalize()

    daily_df = election_df.copy()

    daily_df["date"] = capture_date

    # ------------------------------------------------
    # Extract YES probability
    # ------------------------------------------------

    def extract_yes_probability(row):

        outcomes = row.get("outcomes")
        prices = row.get("outcome_prices")

        if outcomes is None or prices is None:
            return None

        try:

            # Convert JSON strings to Python lists
            if isinstance(outcomes, str):
                outcomes = json.loads(outcomes)

            if isinstance(prices, str):
                prices = json.loads(prices)

            # Find the price corresponding to YES
            for outcome, price in zip(outcomes, prices):

                if str(outcome).strip().lower() == "yes":
                    return float(price)

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError
        ):
            return None

        return None

    daily_df["yes_probability"] = daily_df.apply(
        extract_yes_probability,
        axis=1
    )

    # Convert probability to percentage points
    daily_df["probability"] = (
        daily_df["yes_probability"] * 100
    )

    # ------------------------------------------------
    # Ensure numeric market fields
    # ------------------------------------------------

    for col in ["volume", "liquidity"]:

        if col in daily_df.columns:
            daily_df[col] = pd.to_numeric(
                daily_df[col],
                errors="coerce"
            )

    # ------------------------------------------------
    # Final columns
    # ------------------------------------------------

    final_columns = [
        "date",

        "election_type",
        "election_country",
        "market_category",

        "event",
        "market_name",
        "market_type",
        "candidate",

        "market_id",
        "condition_id",
        "negRiskMarketID",
        "yes_token",

        "yes_probability",
        "probability",

        "volume",
        "liquidity",

        "negRisk",
        "active",
        "closed",
        "accepting_orders",

        "outcomes",
        "outcome_prices"
    ]

    # Keep only columns that exist
    final_columns = [
        col
        for col in final_columns
        if col in daily_df.columns
    ]

    daily_df = daily_df[final_columns]

    return daily_df



def update_election_history(history_df, daily_snapshot):
    """
    Append a daily election market snapshot to historical data.

    Parameters
    ----------
    history_df : pd.DataFrame or None
        Existing historical election market data.

    daily_snapshot : pd.DataFrame
        Output from capture_election_market().

    Returns
    -------
    pd.DataFrame
        Updated historical election market data.
    """

    # ------------------------------------------------
    # Validate daily snapshot
    # ------------------------------------------------

    if daily_snapshot is None or daily_snapshot.empty:

        if history_df is None:
            return pd.DataFrame()

        return history_df.copy()

    daily_snapshot = daily_snapshot.copy()

    # ------------------------------------------------
    # Standardize market ID
    # ------------------------------------------------

    if "market_id" in daily_snapshot.columns:

        daily_snapshot["market_id"] = (
            daily_snapshot["market_id"]
            .astype(str)
            .str.strip()
        )

    # ------------------------------------------------
    # No existing history
    # ------------------------------------------------

    if history_df is None or history_df.empty:

        history = daily_snapshot.copy()

    else:

        history = history_df.copy()

        # Standardize existing market ID

        if "market_id" in history.columns:

            history["market_id"] = (
                history["market_id"]
                .astype(str)
                .str.strip()
            )

        # ------------------------------------------------
        # Combine
        # ------------------------------------------------

        history = pd.concat(
            [history, daily_snapshot],
            ignore_index=True
        )

    # ------------------------------------------------
    # Remove duplicate snapshots
    # ------------------------------------------------

    history = history.drop_duplicates(
        subset=["date", "market_id"],
        keep="last"
    )

    # ------------------------------------------------
    # Sort
    # ------------------------------------------------

    history = history.sort_values(
        ["date", "market_id"]
    ).reset_index(drop=True)

    return history


def save_election_history(history_df, filepath="election_market_history.csv"):
    """
    Save election market history to a CSV file.

    Parameters
    ----------
    history_df : pd.DataFrame
        Historical election market data.

    filepath : str
        Path where the CSV file will be saved.

    Returns
    -------
    None
    """

    if history_df is None or history_df.empty:
        print("Nothing to save.")
        return

    history_df.to_csv(
        filepath,
        index=False
    )

    print(
        f"Election history saved: {len(history_df)} rows"
    )
    print(
        f"File: {filepath}"
    )




def load_election_history(filepath="election_market_history.csv"):
    """
    Load election market history from a CSV file.

    Parameters
    ----------
    filepath : str
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Historical election market data.
    """

    try:

        history_df = pd.read_csv(
            filepath,
            parse_dates=["date"]
        )

        # ------------------------------------------------
        # Ensure identifiers have consistent types
        # ------------------------------------------------

        if "market_id" in history_df.columns:
            history_df["market_id"] = (
                history_df["market_id"]
                .astype(str)
                .str.strip()
            )

        if "condition_id" in history_df.columns:
            history_df["condition_id"] = (
                history_df["condition_id"]
                .astype(str)
                .str.strip()
            )

        if "negRiskMarketID" in history_df.columns:
            history_df["negRiskMarketID"] = (
                history_df["negRiskMarketID"]
                .astype(str)
                .str.strip()
            )

        if "yes_token" in history_df.columns:
            history_df["yes_token"] = (
                history_df["yes_token"]
                .astype(str)
                .str.strip()
            )

        print(
            f"Election history loaded: {len(history_df)} rows"
        )

        return history_df

    except FileNotFoundError:

        print(
            f"No history file found: {filepath}"
        )

        return pd.DataFrame()



def capture_and_update_election_history(
    election_df,
    history_filepath="election_market_history.csv",
    capture_date=None
):
    """
    Capture today's election market data and update historical data.

    Parameters
    ----------
    election_df : pd.DataFrame
        Output from prepare_election_markets().

    history_filepath : str
        Path to the historical CSV file.

    capture_date : str or None
        Date of the snapshot. If None, today's date is used.

    Returns
    -------
    pd.DataFrame
        Updated historical election market data.
    """

    # ------------------------------------------------
    # Capture daily snapshot
    # ------------------------------------------------

    daily_snapshot = capture_election_market(
        election_df,
        capture_date=capture_date
    )

    if daily_snapshot.empty:
        print("No election market data captured.")
        return load_election_history(history_filepath)

    # ------------------------------------------------
    # Load existing history
    # ------------------------------------------------

    history_df = load_election_history(
        history_filepath
    )

    # ------------------------------------------------
    # Update history
    # ------------------------------------------------

    history_df = update_election_history(
        history_df,
        daily_snapshot
    )

    # ------------------------------------------------
    # Save updated history
    # ------------------------------------------------

    save_election_history(
        history_df,
        history_filepath
    )

    return history_df




def calculate_probability_changes(history_df):
    """
    Calculate probability changes between consecutive
    snapshots for each market.

    Parameters
    ----------
    history_df : pd.DataFrame
        Historical election market data.

    Returns
    -------
    pd.DataFrame
        Latest snapshot for each market with previous
        probability and probability change.
    """

    if history_df is None or history_df.empty:
        return pd.DataFrame()

    df = history_df.copy()

    # ------------------------------------------------
    # Ensure correct data types
    # ------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["market_id"] = (
        df["market_id"]
        .astype(str)
        .str.strip()
    )

    df["probability"] = pd.to_numeric(
        df["probability"],
        errors="coerce"
    )

    # ------------------------------------------------
    # Sort chronologically within each market
    # ------------------------------------------------

    df = df.sort_values(
        ["market_id", "date"]
    ).reset_index(drop=True)

    # ------------------------------------------------
    # Previous probability
    # ------------------------------------------------

    df["previous_probability"] = (
        df.groupby("market_id")["probability"]
        .shift(1)
    )

    # ------------------------------------------------
    # Change from previous snapshot
    # ------------------------------------------------

    df["probability_change"] = (
        df["probability"]
        - df["previous_probability"]
    )

    # ------------------------------------------------
    # Keep latest snapshot only
    # ------------------------------------------------

    latest_date = df["date"].max()

    result = df[
        df["date"] == latest_date
    ].copy()

    # ------------------------------------------------
    # Sort by current probability
    # ------------------------------------------------

    result = result.sort_values(
        "probability",
        ascending=False
    ).reset_index(drop=True)

    return result





def get_biggest_movers(df, n=5):
    """
    Identify the biggest probability increases and decreases
    on the latest available date.

    Parameters
    ----------
    df : pd.DataFrame
        Output from calculate_probability_changes().

    n : int
        Number of biggest movers to return for each direction.

    Returns
    -------
    dict
        Dictionary containing biggest gainers and losers.
    """

    if df is None or df.empty:
        return {
            "gainers": pd.DataFrame(),
            "losers": pd.DataFrame()
        }

    # ------------------------------------------------
    # Latest date
    # ------------------------------------------------

    latest_date = df["date"].max()

    latest_data = df[
        df["date"] == latest_date
    ].copy()

    # ------------------------------------------------
    # Remove rows without a probability change
    #
    # On the first day of history all changes are NaN.
    # ------------------------------------------------

    movers = latest_data[
        latest_data["probability_change"].notna()
    ].copy()

    # ------------------------------------------------
    # Biggest gainers
    # ------------------------------------------------

    gainers = (
        movers[
            movers["probability_change"] > 0
        ]
        .sort_values(
            "probability_change",
            ascending=False
        )
        .head(n)
    )

    # ------------------------------------------------
    # Biggest losers
    # ------------------------------------------------

    losers = (
        movers[
            movers["probability_change"] < 0
        ]
        .sort_values(
            "probability_change",
            ascending=True
        )
        .head(n)
    )

    # ------------------------------------------------
    # Keep useful columns
    # ------------------------------------------------

    columns = [
        "date",
        "candidate",
        "market_name",
        "market_id",
        "probability",
        "previous_probability",
        "probability_change"
    ]

    gainers = gainers[
        [col for col in columns if col in gainers.columns]
    ]

    losers = losers[
        [col for col in columns if col in losers.columns]
    ]

    return {
        "gainers": gainers,
        "losers": losers
    }


def calculate_market_trends(df):
    """
    Calculate probability trends for each market.

    Parameters
    ----------
    df : pd.DataFrame
        Election market history containing multiple dates.

    Returns
    -------
    pd.DataFrame
        Market-level probability trends.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    required_columns = [
        "date",
        "market_name",
        "probability"
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Make a copy
    data = df.copy()

    # Ensure correct types
    data["date"] = pd.to_datetime(data["date"])

    data["probability"] = pd.to_numeric(
        data["probability"],
        errors="coerce"
    )

    # Sort chronologically
    data = data.sort_values(
        ["market_name", "date"]
    )

    # Calculate start and latest probability
    trends = (
        data.groupby("market_id")
        .agg(
            market_name=("market_name", "first"),
            start_date=("date", "min"),
            latest_date=("date", "max"),
            start_probability=("probability", "first"),
            latest_probability=("probability", "last")
        )
        .reset_index()
    )

    # Calculate change
    trends["probability_change"] = (
        trends["latest_probability"]
        - trends["start_probability"]
    )

    # Direction
    trends["trend"] = np.select(
        [
            trends["probability_change"] > 0,
            trends["probability_change"] < 0
        ],
        [
            "Up",
            "Down"
        ],
        default="Unchanged"
    )

    # Sort by absolute movement
    trends["absolute_change"] = (
        trends["probability_change"].abs()
    )

    trends = trends.sort_values(
        "absolute_change",
        ascending=False
    ).reset_index(drop=True)

    return trends


def get_top_market_movers(trend_df, n=5):

    # Top markets with probability increases
    gainers = (
        trend_df[
            trend_df["probability_change"] > 0
        ]
        .sort_values(
            "probability_change",
            ascending=False
        )
        .head(n)
        .reset_index(drop=True)
    )

    # Top markets with probability decreases
    losers = (
        trend_df[
            trend_df["probability_change"] < 0
        ]
        .sort_values(
            "probability_change",
            ascending=True
        )
        .head(n)
        .reset_index(drop=True)
    )

    return {
        "gainers": gainers,
        "losers": losers
    }




def calculate_candidate_trends(df):

    # Remove rows without a candidate
    candidate_df = df.dropna(subset=["candidate"]).copy()

    # Aggregate market-level information by candidate
    candidate_trends = (
        candidate_df
        .groupby("candidate")
        .agg(
            markets=("market_id", "nunique"),
            average_probability=("probability", "mean"),
            total_volume=("volume", "sum"),
            total_change=("probability_change", "sum"),
            average_change=("probability_change", "mean")
        )
        .reset_index()
    )

    # Determine overall trend
    candidate_trends["trend"] = np.select(
        [
            candidate_trends["total_change"] > 0,
            candidate_trends["total_change"] < 0
        ],
        [
            "Up",
            "Down"
        ],
        default="Unchanged"
    )

    return candidate_trends



def classify_presidential_subtype(question, event_title=""):
    """
    Classify a US Presidential market into its specific stage.

    Categories:
        - Democratic Nomination
        - Republican Nomination
        - Presidential General Election
        - Other
    """

    text = f"{str(question).lower()} {str(event_title).lower()}"

    # Democratic nomination
    if (
        "democratic presidential nomination" in text
        or "democratic presidential nominee" in text
    ):
        return "Democratic Nomination"

    # Republican nomination
    if (
        "republican presidential nomination" in text
        or "republican presidential nominee" in text
    ):
        return "Republican Nomination"

    # General presidential election
    if (
        "us presidential election" in text
        or "u.s. presidential election" in text
        or "united states presidential election" in text
        or "presidential election" in text
    ):
        return "Presidential General Election"

    return "Other"



def classify_election_subtype(question, event_title=""):
    """
    Classify the subtype/stage of an election market.

    Returns categories such as:
        - Democratic Nomination
        - Republican Nomination
        - General Election
        - Senate
        - House
        - Governor
        - Mayoral
        - State Legislature
        - Presidential
        - Parliamentary
        - Other
    """

    import re

    q = str(question).lower()
    e = str(event_title).lower()
    text = f"{q} {e}"

    # ============================================================
    # 1. PARTY NOMINATIONS — HIGHEST PRIORITY
    # ============================================================

    democratic_patterns = [
        "democratic presidential nomination",
        "democratic presidential nominee",
        "democratic nomination",
        "democratic nominee",
        "democrat nomination",
        "democrat nominee",
    ]

    republican_patterns = [
        "republican presidential nomination",
        "republican presidential nominee",
        "republican nomination",
        "republican nominee",
    ]

    if any(pattern in text for pattern in democratic_patterns):
        return "Democratic Nomination"

    if any(pattern in text for pattern in republican_patterns):
        return "Republican Nomination"

    # ============================================================
    # 2. GENERAL US PRESIDENTIAL ELECTION
    # ============================================================

    presidential_patterns = [
        "us presidential election",
        "u.s. presidential election",
        "united states presidential election",
        "2028 presidential election",
        "win the 2028 presidential election",
        "2028 us president",
        "2028 president",
    ]

    if any(pattern in text for pattern in presidential_patterns):
        return "General Election"

    # ============================================================
    # 3. SENATE
    # ============================================================

    senate_keywords = [
        "senate election",
        "senate race",
        "senate seat",
        "senate nominee",
        "nominee for senate",
        "senate primary",
        "us senate",
        "u.s. senate",
        "control the senate",
    ]

    if any(keyword in text for keyword in senate_keywords):

        if "nomination" in text or "nominee" in text or "primary" in text:
            if "democratic" in text or "democrat" in text:
                return "Democratic Nomination"

            if "republican" in text:
                return "Republican Nomination"

        return "Senate"

    # ============================================================
    # 4. HOUSE
    # ============================================================

    house_keywords = [
        "house election",
        "house race",
        "house seat",
        "house nominee",
        "house primary",
        "house of representatives",
        "house representative",
        "congressional election",
        "congressional race",
        "congressional seat",
        "congressional nominee",
        "control the house",
    ]

    if any(keyword in text for keyword in house_keywords):

        if "nomination" in text or "nominee" in text or "primary" in text:
            if "democratic" in text or "democrat" in text:
                return "Democratic Nomination"

            if "republican" in text:
                return "Republican Nomination"

        return "House"

    # ============================================================
    # 5. GOVERNOR
    # ============================================================

    governor_keywords = [
        "governor election",
        "governor race",
        "governor primary",
        "governorship",
        "gubernatorial",
        ]

    if any(keyword in text for keyword in governor_keywords) or (
        "governor" in text
        and "primary" in text
    ):

        if "nomination" in text or "nominee" in text or "primary" in text:
            if "democratic" in text or "democrat" in text:
                return "Democratic Nomination"

            if "republican" in text:
                return "Republican Nomination"

        return "Governor"

    # ============================================================
    # 6. MAYORAL
    # ============================================================

    mayor_keywords = [
        "mayor election",
        "mayoral election",
        "mayoral race",
        "mayor race",
    ]

    if any(keyword in text for keyword in mayor_keywords):

        if "nomination" in text or "nominee" in text or "primary" in text:
            if "democratic" in text or "democrat" in text:
                return "Democratic Nomination"

            if "republican" in text:
                return "Republican Nomination"

        return "Mayoral"

    # ============================================================
    # 7. STATE LEGISLATURE
    # ============================================================

    state_legislature_keywords = [
        "state legislature",
        "state senate",
        "state house",
        "state representative",
    ]

    if any(keyword in text for keyword in state_legislature_keywords):

        if "nomination" in text or "nominee" in text or "primary" in text:
            if "democratic" in text or "democrat" in text:
                return "Democratic Nomination"

            if "republican" in text:
                return "Republican Nomination"

        return "State Legislature"

    # ============================================================
    # 8. GLOBAL ELECTIONS
    # ============================================================

    if "parliament" in text or "parliamentary" in text:
        return "Parliamentary"

    if "prime minister" in text:
        return "Prime Minister"

    if "presidential election" in text:
        return "Presidential"

    # ============================================================
    # 9. DEFAULT
    # ============================================================

    return "Other"


def filter_markets(
    df,
    market_category=None,
    election_type=None,
    election_subtype=None,
    country=None,
    candidate=None
):
    """
    Filter market history using optional hierarchical filters.
    """

    filtered = df.copy()

    if market_category is not None:
        filtered = filtered[
            filtered["market_category"] == market_category
        ]

    if election_type is not None:
        filtered = filtered[
            filtered["election_type"] == election_type
        ]

    if election_subtype is not None:
        filtered = filtered[
            filtered["election_subtype"] == election_subtype
        ]

    if country is not None:
        filtered = filtered[
            filtered["election_country"] == country
        ]

    if candidate is not None:
        filtered = filtered[
            filtered["candidate"] == candidate
        ]

    return filtered


def calculate_nomination_kpis(df):
    """
    Calculate KPIs for a specific party nomination market group.

    Expected input:
        A filtered DataFrame containing only one nomination group,
        e.g. US Presidential + Democratic Nomination.

    Returns:
        Dictionary containing nomination KPIs.
    """

    latest_date = df["date"].max()

    latest_data = df[
        df["date"] == latest_date
    ].copy()

    # Candidate with highest probability
    leader = latest_data.loc[
        latest_data["probability"].idxmax()
    ]

    # Total trading volume
    total_volume = latest_data["volume"].sum()

    # Number of candidates/markets
    total_markets = latest_data["market_id"].nunique()

    return {
        "latest_date": latest_date,
        "leader": leader["candidate"],
        "leader_market": leader["market_name"],
        "leader_probability": float(
            leader["probability"]
        ),
        "total_volume": float(total_volume),
        "total_markets": total_markets
    }




def get_candidate_ranking(df):
    """
    Rank candidates by latest probability.

    Expected input:
        A filtered candidate-based election market DataFrame,
        e.g. US Presidential + Democratic Nomination
        or US Presidential + General Election.

    Returns
    -------
    pd.DataFrame
        Candidate ranking based on latest probability.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    required_columns = [
        "date",
        "candidate",
        "market_name",
        "market_id",
        "probability",
        "volume",
        "liquidity"
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    data = df.copy()

    # ------------------------------------------------
    # Ensure correct data types
    # ------------------------------------------------

    data["date"] = pd.to_datetime(
        data["date"],
        errors="coerce"
    )

    data["probability"] = pd.to_numeric(
        data["probability"],
        errors="coerce"
    )

    data["volume"] = pd.to_numeric(
        data["volume"],
        errors="coerce"
    )

    data["liquidity"] = pd.to_numeric(
        data["liquidity"],
        errors="coerce"
    )

    data["market_id"] = (
        data["market_id"]
        .astype(str)
        .str.strip()
    )

    # ------------------------------------------------
    # Latest snapshot
    # ------------------------------------------------

    latest_date = data["date"].max()

    latest_data = data[
        data["date"] == latest_date
    ].copy()

    # ------------------------------------------------
    # One row per market
    # ------------------------------------------------

    latest_data = (
        latest_data
        .drop_duplicates(
            subset=["market_id"]
        )
    )

    # ------------------------------------------------
    # Rank by probability
    # ------------------------------------------------

    ranking = (
        latest_data[
            [
                "candidate",
                "market_name",
                "market_id",
                "probability",
                "volume",
                "liquidity"
            ]
        ]
        .sort_values(
            "probability",
            ascending=False
        )
        .reset_index(drop=True)
    )

    ranking["rank"] = ranking.index + 1

    # ------------------------------------------------
    # Final column order
    # ------------------------------------------------

    return ranking[
        [
            "rank",
            "candidate",
            "market_name",
            "market_id",
            "probability",
            "volume",
            "liquidity"
        ]
    ]



def get_candidate_trends(df, full_history=None):
    """
    Calculate candidate-level probability trends.

    Probability Change:
        Latest probability minus the first available
        probability within the selected calendar period.

    Weekly Change:
        Latest probability minus the latest available
        probability approximately one week earlier.

    Entrance Date:
        First date this exact market appears in the
        full historical dataset.

    Markets are identified by BOTH market_id and event,
    because the same market_id can appear with different
    event questions in the dataset.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    required_columns = [
        "date",
        "candidate",
        "market_id",
        "event",
        "probability",
        "volume"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    data = df.copy()



    # ============================================================
    # 1. ENSURE CORRECT DATA TYPES
    # ============================================================

    data["date"] = pd.to_datetime(
        data["date"],
        errors="coerce"
    )

    data["probability"] = pd.to_numeric(
        data["probability"],
        errors="coerce"
    )

    data["volume"] = pd.to_numeric(
        data["volume"],
        errors="coerce"
    )

    data["market_id"] = (
        data["market_id"]
        .astype(str)
        .str.strip()
    )

    data["event"] = (
        data["event"]
        .astype(str)
        .str.strip()
    )

    data = data.dropna(
        subset=["date"]
    )


    if data.empty:
        return pd.DataFrame()

    # ============================================================
    # 2. CREATE UNIQUE MARKET KEY
    # ============================================================

    data["_market_key"] = (
        data["candidate"].astype(str)
        + "||"
        + data["event"].astype(str)
    )

    # ============================================================
    # 3. SELECTED PERIOD
    # ============================================================

    start_date = data["date"].min()
    latest_date = data["date"].max()

    # ============================================================
    # 4. LATEST OBSERVATION FOR EACH MARKET
    # ============================================================

    latest_data = (
        data
        .sort_values("date")
        .drop_duplicates(
            subset=["_market_key"],
            keep="last"
        )
        .copy()
    )




    latest_prob = (
        latest_data[
            [
                "_market_key",
                "market_id",
                "candidate",
                "event",
                "date",
                "probability",
                "volume"
            ]
        ]
        .rename(
            columns={
                "date": "latest_date",
                "probability": "latest_probability",
                "volume": "latest_volume"
            }
        )
    )

    # ============================================================
    # 5. FIRST AVAILABLE OBSERVATION WITHIN SELECTED PERIOD
    # ============================================================

    start_data = (
        data
        .sort_values("date")
        .drop_duplicates(
            subset=["_market_key"],
            keep="first"
        )
        .copy()
    )

    start_prob = (
        start_data[
            [
                "_market_key",
                "date",
                "probability"
            ]
        ]
        .rename(
            columns={
                "date": "period_start_date",
                "probability": "start_probability"
            }
        )
    )

    # ============================================================
    # 6. MERGE START AND LATEST
    # ============================================================

    trends = latest_prob.merge(
        start_prob,
        on="_market_key",
        how="left"
    )

    # ============================================================
    # 7. PROBABILITY CHANGE
    # ============================================================

    trends["probability_change"] = (
        trends["latest_probability"]
        - trends["start_probability"]
    )

    # ============================================================
    # 8. MARKET ENTRANCE DATE
    # ============================================================

    if full_history is not None:

        entrance_source = full_history.copy()

        entrance_source["date"] = pd.to_datetime(
            entrance_source["date"],
            errors="coerce"
        )

        entrance_source["market_id"] = (
            entrance_source["market_id"]
            .astype(str)
            .str.strip()
        )

        entrance_source["event"] = (
            entrance_source["event"]
            .astype(str)
            .str.strip()
        )
        entrance_source["candidate"] = (
            entrance_source["candidate"]
            .astype(str)
            .str.strip()
        )

        entrance_source["_market_key"] = (
            entrance_source["candidate"].astype(str)
            + "||"
            + entrance_source["event"]
        )

        entrance_dates = (
            entrance_source
            .dropna(subset=["date"])
            .groupby("_market_key")["date"]
            .min()
            .reset_index()
            .rename(
                columns={
                    "date": "entrance_date"
                }
            )
        )

        trends = trends.merge(
            entrance_dates,
            on="_market_key",
            how="left"
        )

    else:

        trends["entrance_date"] = (
            trends["period_start_date"]
        )

    # ============================================================
    # 9. WEEKLY PROBABILITY CHANGE
    # ============================================================

    weekly_source = (
        full_history
        if full_history is not None
        else data
    ).copy()

    weekly_source["date"] = pd.to_datetime(
        weekly_source["date"],
        errors="coerce"
    )

    weekly_source["market_id"] = (
        weekly_source["market_id"]
        .astype(str)
        .str.strip()
    )

    weekly_source["event"] = (
        weekly_source["event"]
        .astype(str)
        .str.strip()
    )

    weekly_source["candidate"] = (
        weekly_source["candidate"]
        .astype(str)
        .str.strip()
    )

    weekly_source["probability"] = pd.to_numeric(
        weekly_source["probability"],
        errors="coerce"
    )

    weekly_source["_market_key"] = (
        weekly_source["candidate"].astype(str)
        + "||"
        + weekly_source["event"]
    )
   # ------------------------------------------------------------
   # Find the latest available observation for EACH market
   # ------------------------------------------------------------

    latest_market_dates = (
        trends[
            [
               "_market_key",
               "latest_date",
               "latest_probability"
            ]
        ]
        .copy()
    )

    # ------------------------------------------------------------
    # For each market, find the latest observation that is
    # available on or before 7 days before THAT MARKET'S
    # latest observation.
    # ------------------------------------------------------------

    weekly_results = []

    for _, market in latest_market_dates.iterrows():

        market_key = market["_market_key"]
        market_latest_date = market["latest_date"]

        market_history = weekly_source[
            weekly_source["_market_key"] == market_key
        ].copy()

        if market_history.empty:
            weekly_results.append({
                "_market_key": market_key,
                "week_ago_probability": np.nan
            })
            continue

        weekly_cutoff = (
        market_latest_date
        - pd.Timedelta(days=7)
        )

        previous_data = market_history[
            market_history["date"] <= weekly_cutoff
        ].copy()

        if previous_data.empty:
            weekly_results.append({
                "_market_key": market_key,
                "week_ago_probability": np.nan
            })
            continue

        previous_observation = (
            previous_data
            .sort_values("date")
            .iloc[-1]
        )

        weekly_results.append({
            "_market_key": market_key,
            "week_ago_probability":
                previous_observation["probability"]
        })

    weekly_data = pd.DataFrame(
        weekly_results
    )

    trends = trends.merge(
        weekly_data,
        on="_market_key",
        how="left"
    )

    trends["weekly_probability_change"] = (
            trends["latest_probability"]
            - trends["week_ago_probability"]
    )

    # ============================================================
    # 10. TREND CLASSIFICATION
    # ============================================================

    rounded_weekly_change = (
        trends["weekly_probability_change"]
        .round(1)
    )

    # Treat changes that round to 0.0 as unchanged
    rounded_weekly_change = rounded_weekly_change.mask(
        rounded_weekly_change == 0,
        0
    )

    trends["trend"] = np.select(
        [
            rounded_weekly_change > 0,
            rounded_weekly_change < 0
        ],
        [
            "Up",
            "Down"
        ],
        default="Unchanged"
    )

    # ============================================================
    # 11. MARKET STATUS
    # ============================================================

    # Markets that entered after the selected period started
    # do not have a meaningful Probability Change.
    trends.loc[
        trends["entrance_date"] > start_date,
        "probability_change"
    ] = np.nan

    # A market that has no observation 7 days before its
    # latest observation has no meaningful Weekly Change.
    trends.loc[
        trends["week_ago_probability"].isna(),
        "weekly_probability_change"
    ] = np.nan

    # Markets whose latest observation is before the end of
    # the selected period are considered to have left the market.
    trends.loc[
        trends["latest_date"] < latest_date,
        "weekly_probability_change"
    ] = np.nan

    trends.loc[
        trends["latest_date"] < latest_date,
        "trend"
    ] = "Left Market"

    # Markets that are still active but have no week-ago
    # observation are considered New.
    trends.loc[
        (trends["latest_date"] == latest_date)
        & (trends["week_ago_probability"].isna()),
        "trend"
    ] = "New"

    # ============================================================
    # 12. DEBUG
    # ============================================================


    # ============================================================
    # 13. SORT
    # ============================================================

    trends = (
        trends
        .sort_values(
            "latest_probability",
            ascending=False
        )
        .reset_index(drop=True)
    )

    # ============================================================
    # 14. FINAL OUTPUT
    # ============================================================

    return trends[
    [
        "candidate",
        "market_id",
        "entrance_date",
        "latest_date",
        "start_probability",
        "latest_probability",
        "probability_change",
        "weekly_probability_change",
        "trend",
        "latest_volume"
    ]
]



def extract_us_state(question):
    """
    Extract US state from a US election market question.
    """

    import re

    if not question:
        return None

    question = str(question)

    # --------------------------------------------------------
    # House district codes
    # Examples: CA-17, CA-22, TX-07, NY-03
    # --------------------------------------------------------

    state_abbreviations = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona",
        "AR": "Arkansas", "CA": "California", "CO": "Colorado",
        "CT": "Connecticut", "DE": "Delaware", "FL": "Florida",
        "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
        "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
        "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
        "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
        "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
        "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
        "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
        "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
        "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
        "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
        "SC": "South Carolina", "SD": "South Dakota",
        "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
        "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
        "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
    }

    match = re.search(r"\b([A-Z]{2})-\d{1,2}\b", question)

    if match:
        return state_abbreviations.get(match.group(1))

    states = (
        r"Alabama|Alaska|Arizona|Arkansas|California|Colorado|"
        r"Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|"
        r"Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|"
        r"Massachusetts|Michigan|Minnesota|Mississippi|Missouri|"
        r"Montana|Nebraska|Nevada|New Hampshire|New Jersey|"
        r"New Mexico|New York|North Carolina|North Dakota|Ohio|"
        r"Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|"
        r"South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|"
        r"Washington|West Virginia|Wisconsin|Wyoming"
    )

    # --------------------------------------------------------
    # Governor race questions
    # Example:
    # Will the Democrats win the Rhode Island governor race in 2026?
    # --------------------------------------------------------

    match = re.search(
        rf"\b({states})\s+governor\s+race\b",
        question,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1)

    # --------------------------------------------------------
    # Governor primary questions
    # Example:
    # Will Helena Foulkes win the 2026 Rhode Island Governor
    # Democratic primary election?
    # --------------------------------------------------------

    match = re.search(
        rf"\b20\d{{2}}\s+({states})\s+Governor\s+"
        rf"(?:Democratic|Republican)\s+primary\b",
        question,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1)

    # --------------------------------------------------------
    # Senate race questions
    # --------------------------------------------------------

    match = re.search(
        rf"\b({states})\s+Senate\s+race\b",
        question,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1)

    # --------------------------------------------------------
    # House race questions
    # --------------------------------------------------------

    match = re.search(
        rf"\b({states})\s+House\s+race\b",
        question,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1)

    # --------------------------------------------------------
    # Existing "in STATE" format
    # Example:
    # Will X win the Senate race in Rhode Island?
    # --------------------------------------------------------

    match = re.search(
        rf"\bin\s+({states})\??$",
        question,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1)


        # --------------------------------------------------------
    # Mayoral election questions
    # --------------------------------------------------------

    if re.search(r"\bLos Angeles\b", question, flags=re.IGNORECASE):
        return "California"

    if re.search(r"\bNYC\b|\bNew York City\b", question, flags=re.IGNORECASE):
        return "New York"

    # --------------------------------------------------------
    # State-level ballot measures and other elections
    # --------------------------------------------------------

    match = re.search(
        rf"\b({states})\b",
        question,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


def extract_parliamentary_party(question):
    """
    Extract the party name from a parliamentary market question.
    """

    import re

    if not question:
        return None

    question = str(question)

    if (
        "somaliland parliamentary election" in question.lower()
         and "no" in question.lower()
    ):
        return "No Somaliland election"

    match = re.search(
        r"^(?:Will )?(?:the )?(.+?) win the most seats",
        question,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    return None


def get_top_nomination_movers(trends_df, top_n=5):
    """
    Return the biggest gainers and losers among candidates.

    Parameters:
        trends_df: Output from get_nomination_trends()
        top_n: Number of gainers/losers to return

    Returns:
        Dictionary containing gainers and losers DataFrames.
    """

    gainers = (
        trends_df[
            trends_df["probability_change"] > 0
        ]
        .sort_values(
            "probability_change",
            ascending=False
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    losers = (
        trends_df[
            trends_df["probability_change"] < 0
        ]
        .sort_values(
            "probability_change",
            ascending=True
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    return {
        "gainers": gainers,
        "losers": losers
    }




def classify_market_category(question, event_title=""):
    """
    Classify a market into a broad dashboard category.

    Categories:
        - US Elections
        - Global Elections
        - Geopolitical
        - Other
    """

    q = str(question).lower()
    e = str(event_title).lower()
    text = f"{q} {e}"

    # ============================================================
    # 1. GEOPOLITICAL — CHECK FIRST
    # ============================================================
    #
    # Important:
    # Some geopolitical markets contain words such as
    # "president" or "government", which classify_election()
    # could otherwise interpret as Global Elections.
    #
    # Therefore geopolitical markets must be detected FIRST.

    geopolitical_patterns = [
        "xi jinping out",
        "putin out",
        "out as president of russia",
        "out before",
        "remain in power",
        "leave office",
        "removed from office",
        "removed as president",
        "resign as president",
        "step down as president",
    ]

    if any(pattern in text for pattern in geopolitical_patterns):
        return "Geopolitical"

    # ============================================================
    # 2. US ELECTIONS
    # ============================================================

    election_type = classify_election(question, event_title)

    if election_type in [
        "US Presidential",
        "US Midterms",
        "US House",
        "US State/Local",
    ]:
        return "US Elections"

    # ============================================================
    # 3. GLOBAL ELECTIONS
    # ============================================================

    if election_type == "Global Elections":
        return "Global Elections"

    # ============================================================
    # 4. DEFAULT
    # ============================================================

    return "Other"


def shorten_market_question(question):

    import re

    if not question:
        return question

    question = question.strip()

    # --------------------------------------------------------
    # Senate / House / Governor race questions
    # --------------------------------------------------------

    if " Senate race in " in question:
        parts = question.split(" Senate race in ")
        party = (
            parts[0]
            .replace("Will the ", "")
            .replace(" win the", "")
            .strip()
        )
        location = parts[1].replace("?", "").strip()
        return f"{party} — {location}"

    if " House race in " in question:
        parts = question.split(" House race in ")
        party = (
            parts[0]
            .replace("Will the ", "")
            .replace(" win the", "")
            .strip()
        )
        location = parts[1].replace("?", "").strip()
        return f"{party} — {location}"

    if " Governor race in " in question:
        parts = question.split(" Governor race in ")
        party = (
            parts[0]
            .replace("Will the ", "")
            .replace(" win the", "")
            .strip()
        )
        location = parts[1].replace("?", "").strip()
        return f"{party} — {location}"

    # Governor race questions such as:
    # "Will the Democrats win the New Mexico governor race in 2026?"
    # "Will the Republicans win the Rhode Island governor race in 2026?"
    # "Will an independent win the Rhode Island governor race in 2026?"

    match = re.search(
        r"^Will\s+(?:the\s+)?(.+?)\s+win\s+the\s+(.+?)\s+governor\s+race\s+in\s+\d{4}\?$",
        question,
        flags=re.IGNORECASE
    )

    if match:
        party = match.group(1).strip()
        location = match.group(2).strip()

        party = party.replace("Democrats", "Democrats")
        party = party.replace("Republicans", "Republicans")
        party = party.replace("an independent", "Independent")

        return f"{party} — {location} — Governor"

    # --------------------------------------------------------
    # Senate / House control markets
    # --------------------------------------------------------

    if "control the Senate" in question:

        if "Democratic Party" in question:
            return "Democrats — Senate Control"

        if "Republican Party" in question:
            return "Republicans — Senate Control"

    if "control the House" in question:

        if "Democratic Party" in question:
            return "Democrats — House Control"

        if "Republican Party" in question:
            return "Republicans — House Control"

    # --------------------------------------------------------
    # Senate seat-count markets
    # --------------------------------------------------------

    if "hold 47 or fewer Senate seats" in question:
        return "Republicans — 47 or fewer seats"

    if "hold 57 or more Senate seats" in question:
        return "Republicans — 57+ seats"

    if "hold exactly" in question and "Senate seats" in question:

        if "Republican Party" in question:
            party = "Republicans"

        elif "Democratic Party" in question:
            party = "Democrats"

        else:
            party = "Party"

        seat_part = question.split("hold exactly")[1]
        seat_part = seat_part.split("Senate seats")[0].strip()

        return f"{party} — {seat_part} seats"

    # --------------------------------------------------------
    # Governor seat-count markets
    # --------------------------------------------------------

    if "fewer than 22 governorships" in question:
        return "Republicans — Fewer than 22 governorships"

    if "hold exactly" in question and "governorships" in question:

        if "Republican Party" in question:
            party = "Republicans"

        elif "Democratic Party" in question:
            party = "Democrats"

        else:
            party = "Party"

        seat_part = question.split("hold exactly")[1]
        seat_part = seat_part.split("governorships")[0].strip()

        return f"{party} — {seat_part} governorships"

    if "32 or more governorships" in question:
        return "Republicans — 32+ governorships"

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return question



def format_volume(value):
    if pd.isna(value):
        return "N/A"

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"

    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"

    if value >= 1_000:
        return f"{value / 1_000:.1f}K"

    return f"{value:,.0f}"


def get_homepage_market_summary(df):
    """
    Build the three headline markets for the Home page:

    1. USA Election
    2. Global Election
    3. Geopolitical Issue

    For each headline market we return:
        - market_name
        - leader
        - probability
        - volume
        - trend_change
        - last_week_probability
    """

    if df is None or df.empty:
        return {
            "usa": None,
            "global": None,
            "geopolitical": None
        }

    data = df.copy()

    # --------------------------------------------------------
    # Make sure the required columns are numeric
    # --------------------------------------------------------

    data["probability"] = pd.to_numeric(
        data["probability"],
        errors="coerce"
    )

    data["volume"] = pd.to_numeric(
        data["volume"],
        errors="coerce"
    )

    data["date"] = pd.to_datetime(
        data["date"],
        errors="coerce"
    )

    data = data.dropna(
        subset=["date", "probability"]
    )

    if data.empty:
        return {
            "usa": None,
            "global": None,
            "geopolitical": None
        }

    latest_date = data["date"].max()

    # --------------------------------------------------------
    # Helper function
    # --------------------------------------------------------

    def build_market(category_df):

        if category_df.empty:
            return None

        # ----------------------------------------------------
        # Find the latest snapshot for each market
        # ----------------------------------------------------

        latest = category_df[
            category_df["date"] == category_df["date"].max()
        ].copy()

        if latest.empty:
            return None

        # ----------------------------------------------------
        # The leading market/outcome
        # ----------------------------------------------------

        leader_row = latest.sort_values(
            "probability",
            ascending=False
        ).iloc[0]

        market_name = leader_row["market_name"]

        # ----------------------------------------------------
        # Leader
        #
        # For election markets candidate is normally available.
        # For geopolitical markets the market itself is used
        # when there is no candidate.
        # ----------------------------------------------------

        leader = leader_row.get("candidate", None)

        if pd.isna(leader) or str(leader).strip() == "":
            leader = market_name

        # ----------------------------------------------------
        # Volume
        # ----------------------------------------------------

        volume = leader_row.get("volume", 0)

        if pd.isna(volume):
            volume = 0

        # ----------------------------------------------------
        # Find probability approximately one week earlier
        # ----------------------------------------------------

        market_history = category_df[
            category_df["market_name"] == market_name
        ].copy()

        week_ago_target = latest_date - pd.Timedelta(days=7)

        market_history["date_distance"] = (
            market_history["date"] - week_ago_target
        ).abs()

        last_week_row = market_history.sort_values(
            "date_distance"
        ).iloc[0]

        last_week_probability = last_week_row[
            "probability"
        ]

        # ----------------------------------------------------
        # Trend change
        # ----------------------------------------------------

        trend_change = (
            leader_row["probability"]
            - last_week_probability
        )

        return {
            "market_name": market_name,
            "leader": leader,
            "probability": leader_row["probability"],
            "volume": volume,
            "trend_change": trend_change,
            "last_week_probability": last_week_probability,
        }

    # ========================================================
    # USA ELECTION
    # ========================================================

    usa_df = data[
        (
            data["market_category"]
            .astype(str)
            .str.lower()
            .str.contains("election", na=False)
        )
        &
        (
            data["election_country"]
            .astype(str)
            .str.upper()
            .isin(["USA", "US", "UNITED STATES"])
        )
    ].copy()

    # Prefer Presidential elections when available
    presidential_usa = usa_df[
        usa_df["election_subtype"]
        .astype(str)
        .str.contains(
            "presidential",
            case=False,
            na=False
        )
    ]

    if not presidential_usa.empty:
        usa_df = presidential_usa

    usa_summary = build_market(usa_df)

    # ========================================================
    # GLOBAL ELECTION
    # ========================================================

    global_df = data[
        (
            data["market_category"]
            .astype(str)
            .str.lower()
            .str.contains("election", na=False)
        )
        &
        ~(
            data["election_country"]
            .astype(str)
            .str.upper()
            .isin(["USA", "US", "UNITED STATES"])
        )
    ].copy()

    global_summary = build_market(global_df)

    # ========================================================
    # GEOPOLITICAL
    # ========================================================

    geopolitical_df = data[
        data["market_category"]
        .astype(str)
        .str.lower()
        .str.contains(
            "geopolitical",
            na=False
        )
    ].copy()

    geopolitical_summary = build_market(
        geopolitical_df
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "usa": usa_summary,
        "global": global_summary,
        "geopolitical": geopolitical_summary
    }



markets = get_election_markets()




election_df = prepare_election_markets(markets)

capture_and_update_election_history(election_df)


event_check = (
    election_df
    .groupby("negRiskMarketID")
    .agg(
        n_markets=("market_id", "nunique"),
        n_candidates=("candidate", "nunique")
    )
    .reset_index()
)





candidate_df = election_df[
    election_df["market_type"] == "candidate"
].copy()




global_df = election_df[
    election_df["election_type"] == "Global Elections"
].copy()



elections = election_df[
    election_df["election_type"] != "Other"
].copy()




global_elections = election_df[
    election_df["election_type"] == "Global Elections"
].copy()

dem_election_df = election_df[
    (
        election_df["market_type"] == "candidate"
    )
    &
    (
        election_df["market_name"].str.contains(
            "2028 Democratic presidential nomination",
            case=False,
            na=False
        )
    )
].copy()

all_history_df = get_all_election_history(
    dem_election_df,
    days=7
)
all_history_df["election_group"] = all_history_df["market_name"].apply(
    lambda x: "2028 Democratic presidential nomination"
    if "2028 Democratic presidential nomination" in str(x)
    else None
)


event_daily_check = (
    all_history_df
    .groupby(["negRiskMarketID", "date"])
    .agg(
        n_candidates=("candidate", "nunique"),
        total_probability=("probability", "sum"),
        min_probability=("probability", "min"),
        max_probability=("probability", "max"),
        missing_probability=("probability", lambda x: x.isna().sum())
    )
    .reset_index()
)

event_daily_check["difference_from_100"] = (
    event_daily_check["total_probability"] - 100
)

event_daily_check["abs_difference"] = (
    event_daily_check["difference_from_100"].abs()
)


aggregate_history_df = all_history_df[
    all_history_df["market_type"] == "aggregate"
].copy()


candidate_history_df = all_history_df[
    all_history_df["market_type"] == "candidate"
].copy()

##final_df = all_history_df.merge(
   ##election_df[
        ##[
           ## "market_id",
            ##"election_country",
            ##"volume",
            ##"liquidity"
        ##]
    ##],
    ##on="market_id",
    ##how="left"
##)


candidate_history_df["election_group"] = (
    candidate_history_df["event"]
    .str.replace(
        r"Will .*? win the ",
        "",
        regex=True
    )
    .str.replace(
        "?",
        "",
        regex=False
    )
    .str.strip()
)


candidate_summary = (
    candidate_history_df
    .sort_values("date")
    .groupby(
        [
            "election_country",
            "event",
            "candidate"
        ]
    )["probability"]
    .agg(
        mean_probability="mean",
        min_probability="min",
        max_probability="max",
        first_probability="first",
        last_probability="last"
    )
    .reset_index()
)


candidate_summary["change_pp"] = (
    candidate_summary["last_probability"]
    - candidate_summary["first_probability"]
)


candidate_summary = candidate_summary.sort_values(
    "last_probability",
    ascending=False
)


candidate_daily_rank = (
    candidate_history_df
    .copy()
    .sort_values(
        [
            "election_country",
            "election_group",
            "date",
            "probability"
        ],
        ascending=[True, True, True, False]
    )
)

candidate_daily_rank["rank"] = (
    candidate_daily_rank
    .groupby(
        [
            "election_country",
            "election_group",
            "date"
        ]
    )["probability"]
    .rank(
        method="min",
        ascending=False
    )
    .astype(int)
)

daily_leaders = (
    candidate_daily_rank[
        candidate_daily_rank["rank"] == 1
    ]
    [
        [
            "date",
            "election_country",
            "election_group",
            "candidate",
            "probability"
        ]
    ]
    .rename(
        columns={
            "candidate": "leader",
            "probability": "leader_probability"
        }
    )
    .copy()
)

daily_second = (
    candidate_daily_rank[
        candidate_daily_rank["rank"] == 2
    ]
    [
        [
            "date",
            "election_country",
            "election_group",
            "candidate",
            "probability"
        ]
    ]
    .rename(
        columns={
            "candidate": "second_place",
            "probability": "second_probability"
        }
    )
    .copy()
)

daily_leader_gap = daily_leaders.merge(
    daily_second,
    on=[
        "date",
        "election_country",
        "election_group"
    ],
    how="left"
)

daily_leader_gap["leader_gap_pp"] = (
    daily_leader_gap["leader_probability"]
    - daily_leader_gap["second_probability"]
)



candidate_history_df = candidate_history_df.sort_values(
    ["election_country", "election_group", "candidate", "date"]
).copy()

candidate_history_df["daily_change_pp"] = (
    candidate_history_df
    .groupby(
        [
            "election_country",
            "election_group",
            "candidate"
        ]
    )["probability"]
    .diff()
)


daily_volatility = (
    candidate_history_df
    .groupby(
        [
            "election_country",
            "election_group",
            "candidate"
        ]
    )["daily_change_pp"]
    .std()
    .reset_index(
        name="daily_change_std_pp"
    )
)


daily_movement = (
    candidate_history_df
    .groupby(
        [
            "election_country",
            "election_group",
            "candidate"
        ]
    )["daily_change_pp"]
    .apply(
        lambda x: x.dropna().abs().mean()
    )
    .reset_index(
        name="avg_daily_movement_pp"
    )
)


candidate_momentum = (
    candidate_history_df
    .groupby(
        [
            "election_country",
            "election_group",
            "candidate"
        ]
    )
    .agg(
        mean_probability=("probability", "mean"),
        first_probability=("probability", "first"),
        last_probability=("probability", "last"),
        min_probability=("probability", "min"),
        max_probability=("probability", "max"),
        avg_daily_movement_pp=(
            "daily_change_pp",
            lambda x: x.dropna().abs().mean()
        ),
        daily_volatility_pp=(
            "daily_change_pp",
            "std"
        )
    )
    .reset_index()
)

candidate_momentum["net_change_pp"] = (
    candidate_momentum["last_probability"]
    - candidate_momentum["first_probability"]
)




latest_rank = (
    candidate_daily_rank
    .sort_values("date")
    .groupby(
        [
            "election_country",
            "election_group",
            "candidate"
        ]
    )
    .tail(1)
    [
        [
            "election_country",
            "election_group",
            "candidate",
            "rank"
        ]
    ]
    .rename(
        columns={"rank": "current_rank"}
    )
)


candidate_momentum = candidate_momentum.merge(
    latest_rank,
    on=[
        "election_country",
        "election_group",
        "candidate"
    ],
    how="left"
)

daily_leader = (
    candidate_daily_rank
    .sort_values(
        [
            "election_country",
            "election_group",
            "date",
            "rank"
        ]
    )
    .drop_duplicates(
        subset=[
            "election_country",
            "election_group",
            "date"
        ],
        keep="first"
    )
    .copy()
)


daily_leader["previous_leader"] = (
    daily_leader
    .groupby(
        [
            "election_country",
            "election_group"
        ]
    )["candidate"]
    .shift(1)
)


daily_leader["leader_changed"] = (
    daily_leader["candidate"]
    != daily_leader["previous_leader"]
)

daily_leader.loc[
    daily_leader["previous_leader"].isna(),
    "leader_changed"
] = False

daily_leader.loc[
    daily_leader["previous_leader"].isna(),
    "leader_changed"
] = False



candidate_daily_rank = candidate_daily_rank.sort_values(
    [
        "election_country",
        "election_group",
        "candidate",
        "date"
    ]
).copy()

candidate_daily_rank["previous_rank"] = (
    candidate_daily_rank
    .groupby(
        [
            "election_country",
            "election_group",
            "candidate"
        ]
    )["rank"]
    .shift(1)
)


candidate_daily_rank["rank_change"] = (
    candidate_daily_rank["previous_rank"]
    - candidate_daily_rank["rank"]
)


rank_movement_summary = (
    candidate_daily_rank
    .groupby(
        [
            "election_country",
            "election_group",
            "candidate"
        ]
    )
    .agg(
        current_rank=("rank", "last"),
        best_rank=("rank", "min"),
        worst_rank=("rank", "max"),
        rank_changes=(
            "rank_change",
            lambda x: (x.dropna() != 0).sum()
        ),
        rank_gain_events=(
            "rank_change",
            lambda x: (x.dropna() > 0).sum()
        ),
        rank_loss_events=(
            "rank_change",
            lambda x: (x.dropna() < 0).sum()
        )
    )
    .reset_index()
)


election_daily_summary = daily_leader_gap.merge(
    daily_leader[
        [
            "election_country",
            "election_group",
            "date",
            "leader_changed"
        ]
    ],
    on=[
        "election_country",
        "election_group",
        "date"
    ],
    how="left"
)


election_summary = (
    election_daily_summary
    .groupby(
        [
            "election_country",
            "election_group"
        ]
    )
    .agg(
        first_leader=("leader", "first"),
        last_leader=("leader", "last"),

        mean_leader_probability=(
            "leader_probability",
            "mean"
        ),

        first_leader_probability=(
            "leader_probability",
            "first"
        ),

        last_leader_probability=(
            "leader_probability",
            "last"
        ),

        mean_leader_gap_pp=(
            "leader_gap_pp",
            "mean"
        ),

        min_leader_gap_pp=(
            "leader_gap_pp",
            "min"
        ),

        max_leader_gap_pp=(
            "leader_gap_pp",
            "max"
        ),

        leader_changes=(
            "leader_changed",
            "sum"
        )
    )
    .reset_index()
)

election_summary["leader_probability_change_pp"] = (
    election_summary["last_leader_probability"]
    - election_summary["first_leader_probability"]
)

candidate_daily_rank["total_probability"] = (
    candidate_daily_rank
    .groupby(
        [
            "election_country",
            "election_group",
            "date"
        ]
    )["probability"]
    .transform("sum")
)


candidate_daily_rank["probability_share"] = (
    candidate_daily_rank["probability"]
    / candidate_daily_rank["total_probability"]
)


daily_concentration = (
    candidate_daily_rank
    .sort_values(
        [
            "election_country",
            "election_group",
            "date",
            "rank"
        ]
    )
    .groupby(
        [
            "election_country",
            "election_group",
            "date"
        ]
    )
    .agg(
        top_1_probability=("probability", "first"),
        top_2_probability=(
            "probability",
            lambda x: x.iloc[:2].sum()
        ),
        top_3_probability=(
            "probability",
            lambda x: x.iloc[:3].sum()
        ),
        total_probability=("probability", "sum")
    )
    .reset_index()
)

daily_concentration["top_1_share"] = (
    daily_concentration["top_1_probability"]
    / daily_concentration["total_probability"]
)

daily_concentration["top_2_share"] = (
    daily_concentration["top_2_probability"]
    / daily_concentration["total_probability"]
)

daily_concentration["top_3_share"] = (
    daily_concentration["top_3_probability"]
    / daily_concentration["total_probability"]
)


daily_concentration[
    [
        "top_1_share",
        "top_2_share",
        "top_3_share"
    ]
] *= 100


full_candidate_test = all_history_df[
    (all_history_df["market_type"] == "candidate") &
    (all_history_df["election_country"] == "United States")
].copy()








# ------------------------------------------------
# Democratic presidential candidates
# ------------------------------------------------

# Current market metadata
dem_candidates = election_df[
    (election_df["market_type"] == "candidate") &
    (
        election_df["market_name"].str.contains(
            "2028 Democratic presidential nomination",
            case=False,
            na=False
        )
    )
].copy()


dem_history = get_all_election_history(
    dem_candidates,
    days=7
)

dem_history = dem_history.sort_values(
    ["date", "probability"],
    ascending=[True, False]
).copy()

dem_history["rank"] = (
    dem_history
    .groupby("date")["probability"]
    .rank(
        method="min",
        ascending=False
    )
)





date_counts = (
    dem_history
    .groupby("date")["candidate"]
    .nunique()
)




top_10_history = (
    dem_history[
        dem_history["rank"] <= 10
    ]
    .sort_values(
        ["date", "rank"]
    )
)



dem_analysis = (
    dem_history[
        [
            "date",
            "candidate",
            "probability",
            "rank"
        ]
    ]
    .sort_values(
        ["date", "rank", "candidate"]
    )
    .reset_index(drop=True)
)



candidate_summary = (
    dem_analysis
    .groupby("candidate")
    .agg(
        initial_probability=("probability", "first"),
        final_probability=("probability", "last"),
        mean_probability=("probability", "mean"),
        max_probability=("probability", "max"),
        min_probability=("probability", "min"),
        initial_rank=("rank", "first"),
        final_rank=("rank", "last"),
        best_rank=("rank", "min"),
        worst_rank=("rank", "max")
    )
    .reset_index()
)

candidate_summary["probability_change"] = (
    candidate_summary["final_probability"]
    - candidate_summary["initial_probability"]
)

candidate_summary["rank_change"] = (
    candidate_summary["initial_rank"]
    - candidate_summary["final_rank"]
)



daily_probability_sum = (
    dem_analysis
    .groupby("date")["probability"]
    .sum()
    .reset_index(name="total_probability")
)





daily_market_summary = (
    dem_analysis
    .groupby("date")
    .agg(
        total_probability=("probability", "sum"),
        top_probability=("probability", "max"),
        mean_probability=("probability", "mean"),
        median_probability=("probability", "median"),
        n_candidates=("candidate", "nunique")
    )
    .reset_index()
)

daily_market_summary["unaccounted_probability"] = (
    100 - daily_market_summary["total_probability"]
)

daily_market_summary

daily_concentration = (
    dem_analysis
    .groupby("date")
    .agg(
        top_1=("probability", "nlargest")
    )
)

top_n_summary = (
    dem_analysis
    .sort_values(
        ["date", "probability"],
        ascending=[True, False]
    )
    .groupby("date")
    .agg(
        top_1=("probability", lambda x: x.iloc[:1].sum()),
        top_3=("probability", lambda x: x.iloc[:3].sum()),
        top_5=("probability", lambda x: x.iloc[:5].sum()),
        top_10=("probability", lambda x: x.iloc[:10].sum())
    )
    .reset_index()
)

top_n_summary




candidate_daily_rank = (
    dem_history
    .sort_values(
        [
            "election_country",
            "event",
            "date",
            "probability"
        ],
        ascending=[
            True,
            True,
            True,
            False
        ]
    )
    .copy()
)

candidate_daily_rank["rank"] = (
    candidate_daily_rank
    .groupby(
        [
            "election_country",
            "event",
            "date"
        ]
    )["probability"]
    .rank(
        method="min",
        ascending=False
    )
)



dem_candidates[
    [
        "candidate",
        "market_id",
        "condition_id",
        "negRisk",
        "negRiskMarketID",
        "active",
        "closed",
        "accepting_orders"
    ]
].sort_values("negRiskMarketID")


candidate_counts = (
    election_df
    .groupby("negRiskMarketID")
    .agg(
        n_candidates=("candidate", "nunique"),
        n_markets=("market_id", "nunique")
    )
    .reset_index()
)

candidate_counts.sort_values(
    "n_candidates",
    ascending=False
).head(20)




# Load election history
history_df = pd.read_csv(
   "election_market_history.csv",
    parse_dates=["date"]
)



history_df["election_type"] = history_df.apply(
    lambda row: classify_election(
        row["market_name"],
        row["event"]
    ),
    axis=1
)

history_df["election_subtype"] = history_df.apply(
    lambda row: classify_election_subtype(
        row["market_name"],
        row["event"]
    ),
    axis=1
)

history_df["market_category"] = history_df.apply(
    lambda row: classify_market_category(
        row["market_name"],
        row.get("event", "")
    ),
    axis=1
)

history_df.loc[
    history_df["market_category"] == "Geopolitical",
    "election_type"
] = "Geopolitical"

history_df.loc[
    history_df["market_category"] == "Geopolitical",
    "election_subtype"
] = "Geopolitical"


import os

os.makedirs("data", exist_ok=True)

history_df.to_csv(
    "data/history_df.csv",
    index=False
)

print("Saved:", len(history_df), "rows")
print("Columns:", history_df.columns.tolist())

import os

print(os.path.exists("data/history_df.csv"))
print(os.path.getsize("data/history_df.csv"))

nomination_markets = history_df[
    history_df["market_name"].str.contains(
        "nomination|nominee",
        case=False,
        na=False
    )
]


democratic_history = filter_markets(
    history_df,
    election_type="US Presidential",
    election_subtype="Democratic Nomination"
)

democratic_ranking = get_candidate_ranking(
    democratic_history
)

print(democratic_ranking.head(10))

print(len(democratic_history))

##democratic_trends = get_candidate_trends(
    ##democratic_history
##)

##print(democratic_trends.head(10))

##print("\n--- Filter Tests ---")

# ------------------------------------------------------------
# Test 1: Election type + subtype
# ------------------------------------------------------------

democratic_nomination = filter_markets(
    history_df,
    market_category="US Elections",
    election_type="US Presidential",
    election_subtype="Democratic Nomination"
)

general_election = filter_markets(
    history_df,
    market_category="US Elections",
    election_type="US Presidential",
    election_subtype="General Election"
)

geopolitical = filter_markets(
    history_df,
    market_category="Geopolitical"
)







# ------------------------------------------------
# Clean existing history file
# ------------------------------------------------

##history_df = load_election_history(
    ##"election_market_history.csv"
##)

##history_df = history_df.drop_duplicates(
   ## subset=["date", "market_id"],
    ##keep="last"
##)

##save_election_history(
    ##history_df,
    ##"election_market_history.csv"
##)



# Calculate probability changes
probability_df = calculate_probability_changes(
    history_df
)
# ------------------------------------------------
# Calculate probability change
# ------------------------------------------------

probability_df["previous_probability"] = (
    probability_df
    .groupby("market_id")["probability"]
    .shift(1)
)

probability_df["probability_change"] = (
    probability_df["probability"]
    - probability_df["previous_probability"]
).round(2)



# Get biggest movers
movers = get_biggest_movers(
    probability_df,
    n=5
)













market_trends = calculate_market_trends(history_df)


##democratic_test_trends = democratic_trends.copy()

##democratic_test_trends.loc[
   ## democratic_test_trends["candidate"] == "Gavin Newsom",
   ## "latest_probability"
##] += 2

##democratic_test_trends.loc[
    ##democratic_test_trends["candidate"] == "Alexandria Ocasio-Cortez",
    ##"latest_probability"
##] -= 2

##democratic_test_trends.loc[
   ## democratic_test_trends["candidate"] == "Pete Buttigieg",
    ##"latest_probability"
##] += 1

##democratic_test_trends["probability_change"] = (
   ## democratic_test_trends["latest_probability"]
   ## - democratic_test_trends["start_probability"]
##)

##democratic_test_trends["trend"] = np.select(
    ##[
       ## democratic_test_trends["probability_change"] > 0,
        ##democratic_test_trends["probability_change"] < 0
    ##],
    ##[
       ## "Up",
       ## "Down"
    ##],
    ##default="Unchanged"
##)

def get_homepage_market_summary(df):
    """
    Return the leading USA election, global election,
    and geopolitical market for the Home page.
    """

    if df is None or df.empty:
        return {
            "usa": None,
            "global": None,
            "geopolitical": None
        }

    data = df.copy()

    data["probability"] = pd.to_numeric(
        data["probability"],
        errors="coerce"
    )

    data["volume"] = pd.to_numeric(
        data["volume"],
        errors="coerce"
    )

    data["date"] = pd.to_datetime(
        data["date"],
        errors="coerce"
    )

    data = data.dropna(
        subset=["date", "probability"]
    )

    if data.empty:
        return {
            "usa": None,
            "global": None,
            "geopolitical": None
        }

    latest_date = data["date"].max()

    def build_market(category_df):

        if category_df.empty:
            return None

        latest = category_df[
            category_df["date"] == category_df["date"].max()
        ].copy()

        if latest.empty:
            return None

        # Highest probability market = leader
        row = latest.sort_values(
            "probability",
            ascending=False
        ).iloc[0]

        market_name = row["market_name"]

        leader = row.get("candidate", None)

        if pd.isna(leader) or str(leader).strip() == "":
            leader = market_name

        volume = row.get("volume", 0)

        if pd.isna(volume):
            volume = 0

        # ----------------------------------------------------
        # Find the closest observation to one week ago
        # ----------------------------------------------------

        market_history = category_df[
            category_df["market_name"] == market_name
        ].copy()

        target_date = latest_date - pd.Timedelta(days=7)

        market_history["date_distance"] = (
            market_history["date"] - target_date
        ).abs()

        last_week_row = market_history.sort_values(
            "date_distance"
        ).iloc[0]

        last_week_probability = last_week_row[
            "probability"
        ]

        trend_change = (
            row["probability"]
            - last_week_probability
        )

        return {
            "market_name": market_name,
            "leader": leader,
            "probability": row["probability"],
            "volume": volume,
            "trend_change": trend_change,
            "last_week_probability": last_week_probability
        }

    # ========================================================
    # USA ELECTION
    # ========================================================

    usa_df = data[
        data["election_country"]
        .astype(str)
        .str.upper()
        .isin([
            "USA",
            "US",
            "UNITED STATES"
        ])
    ].copy()

    usa_summary = build_market(usa_df)

    # ========================================================
    # GLOBAL ELECTION
    # ========================================================

    global_df = data[
        (
            data["market_category"]
            .astype(str)
            .str.lower()
            .str.contains("election", na=False)
        )
        &
        ~(
            data["election_country"]
            .astype(str)
            .str.upper()
            .isin([
                "USA",
                "US",
                "UNITED STATES"
            ])
        )
    ].copy()

    global_summary = build_market(global_df)

    # ========================================================
    # GEOPOLITICAL
    # ========================================================

    geopolitical_df = data[
        data["market_category"]
        .astype(str)
        .str.lower()
        .str.contains(
            "geopolitical",
            na=False
        )
    ].copy()

    geopolitical_summary = build_market(
        geopolitical_df
    )

    return {
        "usa": usa_summary,
        "global": global_summary,
        "geopolitical": geopolitical_summary
    }


##election_summary.to_csv(
    ##"election_summary.csv",
    ##index=False
##)

##election_daily_summary.to_csv(
    ##"election_daily_summary.csv",
    ##index=False
##)


##rank_movement_summary.to_csv(
    ##"rank_movement_summary.csv",
    ##index=False
##)

##daily_leader.to_csv(
    ##"daily_leader.csv",
    ##index=False
##)


##candidate_history_df.to_csv(
    ##"candidate_history.csv",
    ##index=False
##)

##candidate_daily_rank.to_csv(
    ##"candidate_daily_rank.csv",
    ##index=False
##)

##daily_leader_gap.to_csv(
    ##"daily_leader_gap.csv",
    ##index=False
##)













##final_df.to_csv(
   ## "election_price_history.csv",
    ##index=False
##)


##kpis = calculate_kpis(final_df)













##final_df.to_csv("election_data.csv", index=False)
