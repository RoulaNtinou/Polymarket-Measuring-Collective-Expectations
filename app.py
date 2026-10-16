import streamlit as st
import pandas as pd
import os
import altair as alt

from polymarket_elections import (
    shorten_market_question,
    classify_election,
    classify_election_subtype,
    classify_market_category,
    extract_candidate,
    normalize_candidate_name,
    filter_markets,
    calculate_kpis,
    calculate_market_trends,
    get_candidate_ranking,
    extract_us_state,
    get_candidate_trends,
    get_homepage_market_summary,
    format_volume,
    extract_parliamentary_party,


)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Polymarket Elections Dashboard",
    page_icon="🗳️",
    layout="wide"
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data(file_mtime):

    df = pd.read_csv(
        "election_market_history.csv",
        parse_dates=["date"],
        low_memory=False
    )

    # --------------------------------------------------------
    # Election classification
    # --------------------------------------------------------

    df["election_type"] = df.apply(
        lambda row: classify_election(
            row["market_name"],
            row.get("event", "")
        ),
        axis=1
    )

    df["election_subtype"] = df.apply(
        lambda row: classify_election_subtype(
            row["market_name"],
            row.get("event", "")
        ),
        axis=1
    )







    df["market_category"] = df.apply(
        lambda row: classify_market_category(
            row["event"],
            row["election_type"]
        ),
        axis=1
    )










    # --------------------------------------------------------
    # Geopolitical override
    # --------------------------------------------------------

    df.loc[
        df["market_category"] == "Geopolitical",
        "election_type"
    ] = "Geopolitical"

    df.loc[
        df["market_category"] == "Geopolitical",
        "election_subtype"
    ] = "Geopolitical"

    # --------------------------------------------------------
    # Candidate extraction
    # --------------------------------------------------------

    extracted = df["event"].apply(
    lambda x: extract_candidate(x)
    )


    df["candidate_type"] = extracted.apply(
        lambda x: x[0]
    )

    df["candidate"] = extracted.apply(
        lambda x: normalize_candidate_name(x[1])
    )

    df["state"] = df.apply(
        lambda row: (
            extract_us_state(row.get("event", ""))
            or extract_us_state(row.get("market_name", ""))
        ),
        axis=1
    )

    df["party"] = df["market_name"].apply(
        extract_parliamentary_party
    )




    return df


history_df = load_data(
    os.path.getmtime("election_market_history.csv")
)











# DEBUG: Check AOC Democratic Nomination history only

aoc_nomination = history_df[
    history_df["event"].astype(str).str.contains(
        "Alexandria Ocasio-Cortez",
        case=False,
        na=False
    )
    &
    history_df["event"].astype(str).str.contains(
        "Democratic presidential nomination",
        case=False,
        na=False
    )
].copy()






csv_debug = pd.read_csv(
    "election_market_history.csv",
    parse_dates=["date"]
)



# ============================================================
# TITLE
# ============================================================

st.title("🗳️ Polymarket Elections Dashboard")

st.markdown(
    "Explore election prediction markets, probabilities, "
    "candidate rankings, trends and market activity."
)

# ============================================================
# HOME PAGE
# ============================================================

##home_page = (
    ##selected_category == "All"
    ##if "selected_category" in locals()
    ##else True
##)

# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("Filters")


# --------------------------------------------------------
# Date filter
# --------------------------------------------------------

min_date = history_df["date"].min().date()
max_date = history_df["date"].max().date()



default_start_date = max(
    min_date,
    max_date - pd.Timedelta(days=7)
)

date_range = st.sidebar.date_input(
    "Date range",
    value=(default_start_date, max_date),
    min_value=min_date,
    max_value=max_date,
    key="date_range_filter"
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range

else:
    start_date = default_start_date
    end_date = max_date

# --------------------------------------------------------
# Apply date filter
# --------------------------------------------------------

filtered_history_df = history_df[
    (history_df["date"].dt.date >= start_date) &
    (history_df["date"].dt.date <= end_date)
].copy()

# ------------------------------------------------------------
# Elections
# ------------------------------------------------------------

election_categories = [
    "All",
    "US Elections",
    "Global Elections",
    "Geopolitical"
]



selected_elections = st.sidebar.selectbox(
    "Elections",
    election_categories
)




# ------------------------------------------------------------
# Build Elections-filtered dataframe
# ------------------------------------------------------------

category_df = history_df.copy()

if selected_elections == "US Elections":

    category_df = category_df[
        category_df["market_category"] == "US Elections"
    ]

elif selected_elections == "Global Elections":

    category_df = category_df[
        category_df["market_category"] == "Global Elections"
    ]



elif selected_elections == "Geopolitical":

    category_df = category_df[
        category_df["market_category"] == "Geopolitical"
    ]




# ------------------------------------------------------------
# Election type
# ------------------------------------------------------------

election_types = sorted(
    category_df["election_type"]
    .dropna()
    .unique()
)


# ------------------------------------------------------------
# Election Type
# ------------------------------------------------------------

if selected_elections == "Global Elections":

    election_type_options = [
        "All",
        "Presidential",
        "Parliamentary",
        "Prime Minister",
        "Other"
    ]

else:

    available_election_types = sorted(
        category_df["election_type"]
        .dropna()
        .unique()
    )

    election_type_options = [
        "All"
    ] + available_election_types

selected_election_type = st.sidebar.selectbox(
    "Election Type",
    election_type_options
)




# ------------------------------------------------------------
# Build election-type filtered dataframe
# ------------------------------------------------------------

type_df = category_df.copy()

if selected_elections == "Global Elections":

    if selected_election_type != "All":
        type_df = type_df[
            type_df["election_subtype"] == selected_election_type
        ]

else:

    if selected_election_type != "All":
        type_df = type_df[
            type_df["election_type"] == selected_election_type
        ]


# ------------------------------------------------------------
# Election subtype
# ------------------------------------------------------------

if selected_elections == "Global Elections":

    selected_subtype = "All"

else:

    subtypes = sorted(
        type_df["election_subtype"]
        .dropna()
        .unique()
    )

    selected_subtype = st.sidebar.selectbox(
        "Election Subtype",
        ["All"] + subtypes
    )


# ------------------------------------------------------------
# Build subtype-filtered dataframe
# ------------------------------------------------------------

subtype_df = type_df.copy()

if selected_subtype != "All":

    subtype_df = subtype_df[
        subtype_df["election_subtype"] == selected_subtype
    ]


# ------------------------------------------------------------
# Country
# ------------------------------------------------------------

countries = sorted(
    subtype_df["election_country"]
    .dropna()
    .astype(str)
    .unique()
)

if selected_elections == "Global Elections":
    selected_country = st.sidebar.selectbox(
        "Country",
        ["All"] + sorted(
            subtype_df["election_country"].dropna().unique().tolist()
        )
    )
else:
    selected_country = "All"



# --------------------------------------------------------
# US Midterm State filter
# --------------------------------------------------------

if (
    selected_elections == "US Elections"
    and selected_election_type == "US Midterms"
):

    selected_state = st.sidebar.selectbox(
        "State",
        ["All"] + sorted(
            subtype_df["state"]
            .dropna()
            .unique()
            .tolist()
        )
    )

else:

    selected_state = "All"

# ------------------------------------------------------------
# Candidate
# ------------------------------------------------------------

candidate_df = subtype_df.copy()

if selected_country != "All":

    candidate_df = candidate_df[
        candidate_df["election_country"].astype(str)
        == selected_country
    ]


candidate_values = sorted(
    candidate_df.loc[
        candidate_df["candidate"].notna(),
        "candidate"
    ]
    .astype(str)
    .unique()
)

selected_candidate = st.sidebar.selectbox(
    "Candidate",
    ["All"] + candidate_values
)


# ============================================================
# FINAL FILTER
# ============================================================




filtered_df = filter_markets(
    filtered_history_df,
    market_category=(
    None
    if selected_elections == "All"
    else (
        "US Elections"
        if selected_elections == "US Elections"
        else (
            "Global Elections"
            if selected_elections == "Global Elections"
            else "Geopolitical"
        )
    )
),
    election_type=(
        None
        if (
            selected_election_type == "All"
            or selected_elections == "Global Elections"
        )
        else selected_election_type
    ),
    election_subtype=(
        selected_election_type
        if (
            selected_elections == "Global Elections"
            and selected_election_type != "All"
        )
        else (
            None
            if selected_subtype == "All"
            else selected_subtype
        )
    ),
    country=(
        None
        if selected_country == "All"
        else selected_country
    ),
    candidate=(
        None
        if selected_candidate == "All"
        else selected_candidate
    )
)







# ============================================================
# DATE FILTER
# ============================================================

filtered_df = filtered_df[
    (filtered_df["date"].dt.date >= start_date)
    &
    (filtered_df["date"].dt.date <= end_date)
].copy()







# ============================================================
# EMPTY DATA CHECK
# ============================================================

if filtered_df.empty:

    st.warning(
        "No markets match the selected filters."
    )

    st.stop()



# ============================================================
# HOME PAGE
# ============================================================

show_homepage = (
    selected_elections == "All"
    and selected_election_type == "All"
    and selected_subtype == "All"
    and selected_country == "All"
    and selected_candidate == "All"
)

if show_homepage:

    st.subheader("Market Highlights")

    homepage = get_homepage_market_summary(history_df)

    home_col1, home_col2, home_col3 = st.columns(3)

    # ========================================================
    # USA ELECTION
    # ========================================================

    with home_col1:

        usa = homepage.get("usa")

        with st.container(border=True):

            st.markdown("### 🇺🇸 USA Election")

            if usa:

                st.caption(usa["market_name"])

                st.metric(
                    "Leader",
                    usa["leader"]
                )

                st.metric(
                    "Probability",
                    f"{usa['probability']:.1f}%",
                    f"{usa['trend_change']:+.1f}% vs last week"
                )

                st.caption(
                    f"Volume: {format_volume(usa['volume'])}"
                )

            else:

                st.info("No USA election market available.")


    # ========================================================
    # GLOBAL ELECTION
    # ========================================================

    with home_col2:

        global_market = homepage.get("global")

        with st.container(border=True):

            st.markdown("### 🌍 Global Election")

            if global_market:

                st.caption(
                    global_market["market_name"]
                )

                st.metric(
                    "Leader",
                    global_market["leader"]
                )

                st.metric(
                    "Probability",
                    f"{global_market['probability']:.1f}%",
                    f"{global_market['trend_change']:+.1f}% vs last week"
                )

                st.caption(
                    f"Volume: {format_volume(global_market['volume'])}"
                )

            else:

                st.info("No global election market available.")


    # ========================================================
    # GEOPOLITICAL
    # ========================================================

    with home_col3:

        geopolitical = homepage.get("geopolitical")

        with st.container(border=True):

            st.markdown("### 🌐 Geopolitical Issue")

            if geopolitical:

                st.caption(
                    geopolitical["market_name"]
                )

                st.metric(
                    "Probability",
                    f"{geopolitical['probability']:.1f}%",
                    f"{geopolitical['trend_change']:+.1f}% vs last week"
                )

                st.caption(
                    f"Volume: {format_volume(geopolitical['volume'])}"
                )

            else:

                st.info(
                    "No geopolitical market available."
                )

    st.divider()




# ============================================================
# US ELECTIONS VIEW
# ============================================================

show_us_elections = (
    selected_elections == "US Elections"
    and selected_election_type == "All"
    and selected_subtype == "All"
    and selected_country == "All"
    and selected_candidate == "All"
)

if show_us_elections:

    st.subheader("US Elections")

    # --------------------------------------------------------
    # Prepare the three BIG US election categories
    # --------------------------------------------------------

    presidential_df = history_df[
        history_df["election_type"] == "US Presidential"
    ].copy()

    midterms_df = history_df[
        history_df["election_type"] == "US Midterms"
    ].copy()

    state_local_df = history_df[
        history_df["election_type"] == "US State/Local"
    ].copy()

    election_cards = [
        ("🇺🇸 Presidential", presidential_df),
        ("🏛️ Midterms", midterms_df),
        ("🗳️ State & Local", state_local_df),
    ]

    card_col1, card_col2, card_col3 = st.columns(3)

    for card_col, (title, election_df) in zip(
        [card_col1, card_col2, card_col3],
        election_cards
    ):

        with card_col:

            with st.container(border=True):

                st.markdown(f"### {title}")

                if not election_df.empty:

                    if title == "🗳️ State & Local":

                        latest_date = election_df["date"].max()

                        latest_df = election_df[
                            election_df["date"] == latest_date
                        ].copy()

                        if not latest_df.empty:

                            leader_row = latest_df.loc[
                                latest_df["probability"].idxmax()
                            ]

                            previous_date = latest_date - pd.Timedelta(days=7)

                            previous_df = history_df[
                                (history_df["date"] == previous_date)
                                & (
                                    history_df["market_id"]
                                    == leader_row["market_id"]
                                )
                            ].copy()

                            if not previous_df.empty:

                                trend_change = (
                                    leader_row["probability"]
                                    - previous_df.iloc[0]["probability"]
                                )

                            else:

                                trend_change = None

                            usa = {
                                "market_name": leader_row["market_name"],
                                "leader": leader_row["candidate"],
                                "probability": leader_row["probability"],
                                "trend_change": trend_change,
                                "volume": leader_row["volume"]
                            }

                        else:
                            usa = None

                    else:

                        summary = get_homepage_market_summary(
                            election_df
                        )

                        usa = summary.get("usa")

                    if usa:

                        st.caption(
                            usa["market_name"]
                        )

                        st.metric(
                            "Leader",
                            usa["leader"]
                        )


                        trend_change = usa["trend_change"]

                        st.metric(
                            "Probability",
                            f"{usa['probability']:.1f}%",
                            (
                                f"{trend_change:+.1f}% vs last week"
                                if trend_change is not None
                                else "N/A vs last week"
                            )
                        )


                        st.caption(
                            f"Volume: {format_volume(usa['volume'])}"
                        )

                    else:

                        st.info(
                            "No market available."
                        )

                else:

                    st.info(
                        "No markets available yet."
                    )

    st.divider()




# ============================================================
# US PRESIDENTIAL VIEW
# ============================================================

show_us_presidential = (
    selected_elections == "US Elections"
    and selected_election_type == "US Presidential"
    and selected_subtype == "All"
    and selected_country == "All"
    and selected_candidate == "All"
)

if show_us_presidential:

    st.subheader("🇺🇸 Presidential Election")

    # --------------------------------------------------------
    # Prepare the three presidential categories
    # --------------------------------------------------------

    general_df = history_df[
        history_df["election_subtype"] == "General Election"
    ].copy()

    democratic_df = history_df[
        history_df["election_subtype"] == "Democratic Nomination"
    ].copy()

    republican_df = history_df[
        history_df["election_subtype"] == "Republican Nomination"
    ].copy()

    presidential_cards = [
        ("🇺🇸 General Election", general_df),
        ("🔵 Democratic Nomination", democratic_df),
        ("🔴 Republican Nomination", republican_df),
    ]

    card_col1, card_col2, card_col3 = st.columns(3)

    for card_col, (title, election_df) in zip(
        [card_col1, card_col2, card_col3],
        presidential_cards
    ):

        with card_col:

            with st.container(border=True):

                st.markdown(f"### {title}")

                if not election_df.empty:

                    summary = get_homepage_market_summary(
                        election_df
                    )

                    usa = summary.get("usa")

                    if usa:

                        st.caption(
                            usa["market_name"]
                        )

                        st.metric(
                            "Leader",
                            usa["leader"]
                        )

                        st.metric(
                            "Probability",
                            f"{usa['probability']:.1f}%",
                            f"{usa['trend_change']:+.1f}% vs last week"
                        )

                        st.caption(
                            f"Volume: {format_volume(usa['volume'])}"
                        )

                    else:

                        st.info(
                            "No market available."
                        )

                else:

                    st.info(
                        "No markets available."
                    )

    st.divider()




# ============================================================
# GLOBAL ELECTIONS VIEW
# ============================================================

show_global_elections = (
    selected_elections == "Global Elections"
    and selected_election_type == "All"
    and selected_subtype == "All"
    and selected_candidate == "All"
)

if show_global_elections and selected_country == "All":

    st.subheader("Global Elections")

    # --------------------------------------------------------
    # All global election markets
    # --------------------------------------------------------

    global_df = filtered_df.copy()

    if not global_df.empty:

        # Get countries represented in the data
        countries = sorted(
            global_df["election_country"]
            .dropna()
            .unique()
            .tolist()
        )

        # One card per country, up to three cards
        card_data = []

        for country in countries:

            country_df = global_df[
                global_df["election_country"] == country
            ].copy()

            summary = get_homepage_market_summary(
                country_df
            )

            market = summary.get("global")


            if market:
                card_data.append(
                    (country, market)
                )

        card_data = card_data[:3]

        if card_data:

            cols = st.columns(len(card_data))

            for col, (country, market) in zip(
                cols,
                card_data
            ):

                with col:

                    with st.container(border=True):

                        st.markdown(
                            f"### 🌍 {country}"
                        )

                        st.caption(
                            market["market_name"]
                        )

                        st.metric(
                            "Leader",
                            market["leader"]
                        )

                        st.metric(
                            "Probability",
                            f"{market['probability']:.1f}%",
                            f"{market['trend_change']:+.1f}% vs last week"
                        )

                        st.caption(
                            f"Volume: {format_volume(market['volume'])}"
                        )

        else:

            st.info(
                "No global election markets available."
            )

    else:

        st.info(
            "No global election markets available."
        )

    st.divider()


# ============================================================
# GLOBAL PRESIDENTIAL ELECTIONS VIEW
# ============================================================

show_global_presidential = (
    selected_elections == "Global Elections"
    and selected_subtype == "All"
    and selected_candidate == "All"
    and (
        selected_election_type == "Presidential"
        or (
            selected_election_type == "All"
            and selected_country != "All"
        )
    )
)

if show_global_presidential:

    st.subheader("🌍 Global Presidential Elections")

    global_presidential_df = filtered_df[
        filtered_df["election_subtype"] == "Presidential"
    ].copy()

    if not global_presidential_df.empty:

        countries = sorted(
            global_presidential_df["election_country"]
            .dropna()
            .unique()
        )

        for country in countries:

            st.markdown(f"### 🇺🇳 {country}")

            country_df = global_presidential_df[
                global_presidential_df["election_country"] == country
            ].copy()

            latest_date = country_df["date"].max()

            latest_country_df = country_df[
                country_df["date"] == latest_date
            ].copy()


            if not latest_country_df.empty:

                market_questions = (
                    latest_country_df["market_name"]
                    .dropna()
                    .unique()
                )

                if len(market_questions) > 0:

                    st.caption(
                        f"Market question: {market_questions[0]}"
                    )

                leader_row = latest_country_df.loc[
                    latest_country_df["probability"].idxmax()
                ]

                # ------------------------------------------------
                # Change vs last week
                # ------------------------------------------------

                previous_date = latest_date - pd.Timedelta(days=7)

                previous_df = history_df[
                    (history_df["date"] == previous_date)
                    & (
                        history_df["market_id"]
                        .isin(latest_country_df["market_id"])
                    )
                ].copy()

                if not previous_df.empty:

                    previous_leader = previous_df[
                        previous_df["market_id"]
                        == leader_row["market_id"]
                    ]

                    if not previous_leader.empty:

                        weekly_change = (
                            leader_row["probability"]
                            - previous_leader.iloc[0]["probability"]
                        )
                        st.caption(
                            f"Latest observation: {latest_date.strftime('%d %b %Y')}"
                        )

                    else:
                        weekly_change = None

                else:
                    weekly_change = None

                # ------------------------------------------------
                # KPI row
                # ------------------------------------------------

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Leader",
                        leader_row["candidate"]
                    )

                with col2:
                    st.metric(
                        "Probability",
                        f"{leader_row['probability']:.1f}%"
                    )

                with col3:

                    if weekly_change is not None:
                        st.metric(
                            "Change vs last week",
                            f"{weekly_change:+.1f}%"
                        )
                    else:
                        st.metric(
                            "Change vs last week",
                            "N/A"
                        )

                with col4:
                    total_volume = latest_country_df["volume"].sum()

                    st.metric(
                        "Total Volume",
                        format_volume(total_volume)
                    )


                # ------------------------------------------------
                # Probability by candidate — Top 10
                # ------------------------------------------------


                chart_data = latest_country_df[
                    [
                        "candidate",
                        "probability"
                    ]
                ].copy()

                chart_data = (
                    chart_data
                    .sort_values(
                        "probability",
                        ascending=False
                    )
                    .head(10)
                )

                chart = alt.Chart(chart_data).mark_bar().encode(
                    x=alt.X(
                        "probability:Q",
                        title="Probability (%)"
                    ),
                    y=alt.Y(
                        "candidate:N",
                        sort="-x",
                        title=None
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "candidate:N",
                            title="Candidate"
                        ),
                        alt.Tooltip(
                            "probability:Q",
                            title="Probability",
                            format=".1f"
                        )
                    ]
                ).properties(
                    height=350
                )

                st.altair_chart(
                    chart,
                    width="stretch"
                )

                # ------------------------------------------------
                # Candidate table
                # ------------------------------------------------

                table = latest_country_df[
                    [
                        "market_id",
                        "candidate",
                        "probability",
                        "volume"
                    ]
                ].copy()

                # ------------------------------------------------
                # Weekly change
                # ------------------------------------------------

                previous_date = latest_date - pd.Timedelta(days=7)

                previous_country_df = history_df[
                    (history_df["date"] == previous_date)
                    &
                    (history_df["market_id"].isin(table["market_id"]))
                ][
                    [
                        "market_id",
                        "probability"
                    ]
                ].copy()

                table = table.merge(
                    previous_country_df,
                    on="market_id",
                    how="left",
                    suffixes=(
                        "",
                        "_previous"
                    )
                )

                table["weekly_change"] = (
                    table["probability"]
                    - table["probability_previous"]
                )

                table["trend"] = table["weekly_change"].apply(
                    lambda x:
                        "Up" if x > 0
                        else "Down" if x < 0
                        else "Unchanged"
                    if pd.notna(x)
                    else "N/A"
                )

                table = table.sort_values(
                    "probability",
                    ascending=False
                )

                table = table.rename(
                    columns={
                        "candidate": "Candidate",
                        "probability": "Probability",
                        "weekly_change": "Change vs last week",
                        "trend": "Trend",
                        "volume": "Volume"
                    }
                )

                table["Probability"] = table[
                    "Probability"
                ].map(
                    lambda x: f"{x:.1f}%"
                )

                table["Change vs last week"] = table[
                    "Change vs last week"
                ].map(
                    lambda x:
                        f"{x:+.1f}%"
                        if pd.notna(x)
                        else "N/A"
                )

                table["Volume"] = table[
                    "Volume"
                ].map(format_volume)

                table = table[
                    [
                        "Candidate",
                        "Probability",
                        "Change vs last week",
                        "Trend",
                        "Volume"
                    ]
                ]


                st.dataframe(
                    table,
                    width="stretch",
                    hide_index=True
                )

            st.divider()

    else:

        st.info(
            "No global presidential election markets available."
        )



# ------------------------------------------------
# GLOBAL PARLIAMENTARY ELECTIONS VIEW
# ------------------------------------------------

show_global_parliamentary = (
    selected_elections == "Global Elections"
    and (
        selected_election_type == "Parliamentary"
        or (
            selected_election_type == "All"
            and selected_country != "All"
        )
    )
    and selected_subtype == "All"
    and selected_candidate == "All"
)

if show_global_parliamentary:

    st.subheader("🌍 Global Parliamentary Elections")

    global_parliamentary_df = filtered_df[
        filtered_df["election_subtype"] == "Parliamentary"
    ].copy()

    if not global_parliamentary_df.empty:

        countries = sorted(
            global_parliamentary_df["election_country"]
            .dropna()
            .unique()
        )

        for country in countries:

            st.markdown(f"### 🌍 {country}")

            country_df = global_parliamentary_df[
                global_parliamentary_df["election_country"] == country
            ].copy()

            latest_date = country_df["date"].max()

            latest_country_df = country_df[
                country_df["date"] == latest_date
            ].copy()

            if not latest_country_df.empty:

                market_questions = (
                    latest_country_df["market_name"]
                    .dropna()
                    .unique()
                )

                if len(market_questions) > 0:

                    market_question = market_questions[0]

                    if not market_question.lower().startswith("will "):
                        market_question = "Will " + market_question

                    st.caption(
                        f"Market question: {market_question}"
                    )

                leader_row = latest_country_df.loc[
                    latest_country_df["probability"].idxmax()
                ]

                previous_date = (
                    latest_date
                    - pd.Timedelta(days=7)
                )

                previous_df = history_df[
                    (history_df["date"] == previous_date)
                    &
                    (
                        history_df["market_id"]
                        .isin(
                            latest_country_df["market_id"]
                        )
                    )
                ].copy()

                if not previous_df.empty:

                    previous_leader = previous_df[
                        previous_df["market_id"]
                        == leader_row["market_id"]
                    ]

                    if not previous_leader.empty:

                        weekly_change = (
                            leader_row["probability"]
                            - previous_leader.iloc[0]["probability"]
                        )

                    else:
                        weekly_change = None

                else:
                    weekly_change = None

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.caption("Leader")
                    st.markdown(
                        f"**{leader_row['party']}**"
                    )

                with col2:
                    st.metric(
                        "Probability",
                        f"{leader_row['probability']:.1f}%"
                    )

                with col3:

                    if weekly_change is not None:
                        st.metric(
                            "Change vs last week",
                            f"{weekly_change:+.1f}%"
                        )
                    else:
                        st.metric(
                            "Change vs last week",
                            "N/A"
                        )

                with col4:

                    total_volume = (
                        latest_country_df["volume"]
                        .sum()
                    )

                    st.metric(
                        "Total Volume",
                        format_volume(total_volume)
                    )



                # ------------------------------------------------
                # Probability by party — Top 10
                # ------------------------------------------------

                chart_data = latest_country_df[
                    [
                        "party",
                        "probability"
                    ]
                ].copy()

                chart_data = chart_data.dropna(
                    subset=["party", "probability"]
                )

                chart_data = (
                    chart_data
                    .sort_values(
                        "probability",
                        ascending=False
                    )
                    .head(10)
                )

                chart = alt.Chart(chart_data).mark_bar().encode(
                    x=alt.X(
                        "probability:Q",
                        title="Probability (%)",
                        scale=alt.Scale(domain=[0, 100])
                    ),
                    y=alt.Y(
                        "party:N",
                        sort="-x",
                        title=None
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "party:N",
                            title="Party / Market"
                        ),
                        alt.Tooltip(
                            "probability:Q",
                            title="Probability",
                            format=".1f"
                        )
                    ]
                ).properties(
                    height=350
                )

                st.altair_chart(
                    chart,
                    width="stretch"
                )


                # Parliamentary Markets table

                table = latest_country_df[
                    [
                        "market_id",
                        "party",
                        "probability",
                        "volume"
                    ]
                ].copy()

                previous_date = latest_date - pd.Timedelta(days=7)

                previous_country_df = history_df[
                    (history_df["date"] == previous_date)
                    &
                    (
                        history_df["market_id"].isin(
                            table["market_id"]
                        )
                    )
                ][
                    ["market_id", "probability"]
                ].copy()

                table = table.merge(
                    previous_country_df,
                    on="market_id",
                    how="left",
                    suffixes=("", "_previous")
                )

                table["weekly_change"] = (
                    table["probability"]
                    - table["probability_previous"]
                )

                table["trend"] = table["weekly_change"].apply(
                    lambda x:
                        "Up" if x > 0
                        else "Down" if x < 0
                        else "Unchanged"
                    if pd.notna(x)
                    else "N/A"
                )

                table = table.sort_values(
                    "probability",
                    ascending=False
                )

                table = table.rename(
                    columns={
                        "party": "Parliamentary Market",
                        "probability": "Probability",
                        "weekly_change": "Change vs last week",
                        "trend": "Trend",
                        "volume": "Volume"
                    }
                )

                table["Probability"] = table[
                    "Probability"
                ].map(
                    lambda x: f"{x:.1f}%"
                )

                table["Change vs last week"] = table[
                    "Change vs last week"
                ].map(
                    lambda x:
                        f"{x:+.1f}%"
                        if pd.notna(x)
                        else "N/A"
                )

                table["Volume"] = table[
                    "Volume"
                ].map(format_volume)

                table = table[
                    [
                        "Parliamentary Market",
                        "Probability",
                        "Change vs last week",
                        "Trend",
                        "Volume"
                    ]
                ]

                st.dataframe(
                    table,
                    width="stretch",
                    hide_index=True
                )



                st.divider()

    else:

        st.info(
            "No global parliamentary election markets available."
        )



# ------------------------------------------------
# GLOBAL PRIME MINISTER VIEW
# ------------------------------------------------



show_global_prime_minister = (
    selected_elections == "Global Elections"
    and (
        selected_election_type == "Prime Minister"
        or (
            selected_election_type == "All"
            and selected_country != "All"
        )
    )
    and selected_subtype == "All"
    and selected_candidate == "All"
)



if show_global_prime_minister:

    st.subheader("🌍 Global Prime Minister Markets")

    global_pm_df = filtered_df[
        filtered_df["election_subtype"] == "Prime Minister"
    ].copy()

    if not global_pm_df.empty:

        countries = sorted(
            global_pm_df["election_country"]
            .dropna()
            .unique()
        )

        for country in countries:

            st.markdown(f"### 🌍 {country}")

            country_df = global_pm_df[
                global_pm_df["election_country"] == country
            ].copy()

            latest_date = country_df["date"].max()

            latest_country_df = country_df[
                country_df["date"] == latest_date
            ].copy()

            if latest_country_df.empty:
                continue

            # Market question
            market_questions = (
                latest_country_df["market_name"]
                .dropna()
                .unique()
            )

            if len(market_questions) > 0:

                market_question = market_questions[0]

                if not market_question.lower().startswith("will "):
                    market_question = "Will " + market_question

                st.caption(
                    f"Market question: {market_question}"
                )

            # Leader
            leader_row = latest_country_df.loc[
                latest_country_df["probability"].idxmax()
            ]

            # Weekly change
            previous_date = latest_date - pd.Timedelta(days=7)

            previous_df = history_df[
                (history_df["date"] == previous_date)
                & (
                    history_df["market_id"].isin(
                        latest_country_df["market_id"]
                    )
                )
            ].copy()

            weekly_change = None

            if not previous_df.empty:

                previous_leader = previous_df[
                    previous_df["market_id"] == leader_row["market_id"]
                ]

                if not previous_leader.empty:
                    weekly_change = (
                        leader_row["probability"]
                        - previous_leader.iloc[0]["probability"]
                    )

            # KPI row
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.caption("Leader")
                st.markdown(f"**{leader_row['candidate']}**")

            with col2:
                st.metric(
                    "Probability",
                    f"{leader_row['probability']:.1f}%"
                )

            with col3:
                st.metric(
                    "Change vs last week",
                    (
                        f"{weekly_change:+.1f}%"
                        if weekly_change is not None
                        else "N/A"
                    )
                )

            with col4:
                total_volume = latest_country_df["volume"].sum()
                st.metric(
                    "Total Volume",
                    format_volume(total_volume)
                )




            # ------------------------------------------------
            # Probability by candidate — Top 10
            # ------------------------------------------------

            chart_data = latest_country_df[
                [
                    "candidate",
                    "probability"
                ]
            ].copy()

            chart_data = chart_data.dropna(
                subset=["candidate", "probability"]
            )

            chart_data = (
                chart_data
                .sort_values(
                    "probability",
                    ascending=False
                )
                .head(10)
            )

            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X(
                    "probability:Q",
                    title="Probability (%)",
                    scale=alt.Scale(domain=[0, 100])
                ),
                y=alt.Y(
                    "candidate:N",
                    sort="-x",
                    title=None
                ),
                tooltip=[
                    alt.Tooltip(
                        "candidate:N",
                        title="Candidate"
                    ),
                    alt.Tooltip(
                        "probability:Q",
                        title="Probability",
                        format=".1f"
                    )
                ]
            ).properties(
                height=350
            )

            st.altair_chart(
                chart,
                width="stretch"
            )



            # Prime Minister Markets table
            table = latest_country_df[
                [
                    "market_id",
                    "candidate",
                    "probability",
                    "volume"
                ]
            ].copy()

            previous_country_df = history_df[
                (history_df["date"] == previous_date)
                & (
                    history_df["market_id"].isin(
                        table["market_id"]
                    )
                )
            ][
                ["market_id", "probability"]
            ].copy()

            table = table.merge(
                previous_country_df,
                on="market_id",
                how="left",
                suffixes=("", "_previous")
            )

            table["weekly_change"] = (
                table["probability"]
                - table["probability_previous"]
            )

            table["trend"] = table["weekly_change"].apply(
                lambda x:
                    "Up" if x > 0
                    else "Down" if x < 0
                    else "Unchanged"
                if pd.notna(x)
                else "N/A"
            )

            table = table.sort_values(
                "probability",
                ascending=False
            ).rename(
                columns={
                    "candidate": "Market",
                    "probability": "Probability",
                    "weekly_change": "Change vs last week",
                    "trend": "Trend",
                    "volume": "Volume"
                }
            )

            table["Probability"] = table["Probability"].map(
                lambda x: f"{x:.1f}%"
            )

            table["Change vs last week"] = table[
                "Change vs last week"
            ].map(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A"
            )

            table["Volume"] = table["Volume"].map(format_volume)

            table = table[
                [
                    "Market",
                    "Probability",
                    "Change vs last week",
                    "Trend",
                    "Volume"
                ]
            ]

            st.dataframe(
                table,
                width="stretch",
                hide_index=True
            )

            if country != countries[-1]:
                st.divider()

    else:
        st.info("No global Prime Minister markets available.")


# ------------------------------------------------
# GLOBAL ELECTIONS — OTHER VIEW
# ------------------------------------------------


show_global_other = (
    selected_elections == "Global Elections"
    and (
        selected_election_type == "Other"
        or (
            selected_election_type == "All"
            and selected_country != "All"
        )
    )
    and selected_subtype == "All"
    and selected_candidate == "All"
)


if show_global_other:
    st.subheader("🌍 Global Elections — Other")

    global_other_df = filtered_df[
        filtered_df["election_subtype"] == "Other"
    ].copy()

    if not global_other_df.empty:

        countries = sorted(
            global_other_df["election_country"]
            .fillna("Other")
            .unique()
        )

        for country in countries:

            country_df = global_other_df[
                global_other_df["election_country"].fillna("Other")
                == country
            ].copy()

            latest_date = country_df["date"].max()

            latest_country_df = country_df[
                country_df["date"] == latest_date
            ].copy()

            if latest_country_df.empty:
                continue

            st.markdown(f"### 🌍 {country}")

            # Market question
            market_questions = (
                latest_country_df["event"]
                .dropna()
                .unique()
            )

            if len(market_questions) > 0:
                market_question = market_questions[0]
                if not market_question.lower().startswith("will "):
                    market_question = "Will " + market_question
                st.caption(f"Market question: {market_question}")

            # Leading market
            leader_row = latest_country_df.loc[
                latest_country_df["probability"].idxmax()
            ]

            previous_date = latest_date - pd.Timedelta(days=7)

            previous_df = history_df[
                (history_df["date"] == previous_date)
                & (
                    history_df["market_id"].isin(
                        latest_country_df["market_id"]
                    )
                )
            ].copy()

            previous_leader = previous_df[
                previous_df["market_id"] == leader_row["market_id"]
            ]

            weekly_change = None

            if not previous_leader.empty:
                weekly_change = (
                    leader_row["probability"]
                    - previous_leader.iloc[0]["probability"]
                )

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.caption("Leading market")
                st.markdown(f"**{leader_row['event']}**")

            with col2:
                st.metric(
                    "Probability",
                    f"{leader_row['probability']:.1f}%"
                )

            with col3:
                st.metric(
                    "Change vs last week",
                    f"{weekly_change:+.1f}%" if weekly_change is not None else "N/A"
                )

            with col4:
                st.metric(
                    "Total Volume",
                    format_volume(latest_country_df["volume"].sum())
                )

            # Probability by market — Top 10
            st.markdown("#### Probability by Market — Top 10")

            chart_data = latest_country_df[
                ["event", "probability"]
            ].copy()

            chart_data = chart_data.dropna(
                subset=["event", "probability"]
            )

            chart_data = (
                chart_data
                .sort_values("probability", ascending=False)
                .head(10)
            )

            if not chart_data.empty:
                chart = alt.Chart(chart_data).mark_bar().encode(
                    x=alt.X(
                        "probability:Q",
                        title="Probability (%)",
                        scale=alt.Scale(domain=[0, 100])
                    ),
                    y=alt.Y(
                        "event:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(labelLimit=350)
                    ),
                    tooltip=[
                        alt.Tooltip("event:N", title="Market"),
                        alt.Tooltip(
                            "probability:Q",
                            title="Probability",
                            format=".1f"
                        )
                    ]
                ).properties(height=350)

                st.altair_chart(
                    chart,
                    width="stretch"
                )

            # Detailed market table
            table = latest_country_df[
                ["market_id", "event", "probability", "volume"]
            ].copy()

            previous_country_df = history_df[
                (history_df["date"] == previous_date)
                & history_df["market_id"].isin(table["market_id"])
            ][["market_id", "probability"]].copy()

            table = table.merge(
                previous_country_df,
                on="market_id",
                how="left",
                suffixes=("", "_previous")
            )

            table["weekly_change"] = (
                table["probability"] - table["probability_previous"]
            )

            table["trend"] = table["weekly_change"].apply(
                lambda x: (
                    "Up" if x > 0
                    else "Down" if x < 0
                    else "Unchanged" if pd.notna(x)
                    else "N/A"
                )
            )

            table = table.sort_values(
                "probability",
                ascending=False
            ).rename(columns={
                "event": "Market",
                "probability": "Probability",
                "weekly_change": "Change vs last week",
                "trend": "Trend",
                "volume": "Volume"
            })

            table["Probability"] = table["Probability"].map(
                lambda x: f"{x:.1f}%"
            )

            table["Change vs last week"] = table[
                "Change vs last week"
            ].map(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A"
            )

            table["Volume"] = table["Volume"].map(format_volume)

            table = table[
                [
                    "Market",
                    "Probability",
                    "Change vs last week",
                    "Trend",
                    "Volume"
                ]
            ]

            st.dataframe(
                table,
                width="stretch",
                hide_index=True
            )

            if country != countries[-1]:
                st.divider()

    else:
        st.info("No Global Elections — Other markets available.")


# ============================================================
# GEOPOLITICAL VIEW
# ============================================================

show_geopolitical = (
    selected_elections == "Geopolitical"
    and selected_election_type == "All"
    and selected_subtype == "All"
    and selected_country == "All"
    and selected_candidate == "All"
)

if show_geopolitical:

    st.subheader("Geopolitical Issues")

    geopolitical_df = history_df[
        history_df["market_category"] == "Geopolitical"
    ].copy()





    if not geopolitical_df.empty:

        # Get unique geopolitical markets
        markets = (
            geopolitical_df[
                ["market_id", "market_name"]
            ]
            .drop_duplicates()
        )

        card_data = []

        for _, market_row in markets.iterrows():

            market_df = geopolitical_df[
                geopolitical_df["market_id"]
                == market_row["market_id"]
            ].copy()

            if market_df.empty:
                continue

            market_df = market_df.sort_values("date")

            # Latest observation within the selected date range
            range_df = market_df[
                market_df["date"].dt.normalize()
                <= pd.Timestamp(end_date)
            ]

            if range_df.empty:
                continue

            latest = range_df.iloc[-1]
            latest_probability = latest["probability"]
            latest_date = latest["date"]

            # --------------------------------------------
            # Change vs last week
            # --------------------------------------------
            one_week_ago = (
                latest_date - pd.Timedelta(days=7)
            )

            previous_df = market_df[
                market_df["date"] <= one_week_ago
            ]

            if not previous_df.empty:
                previous = previous_df.iloc[-1]

                trend_change = (
                    latest_probability
                    - previous["probability"]
                )
            else:
                trend_change = None

            # --------------------------------------------
            # Change vs selected date (start_date)
            # --------------------------------------------
            selected_date_df = market_df[
                market_df["date"].dt.normalize()
                <= pd.Timestamp(start_date)
            ]

            if not selected_date_df.empty:
                selected_date_row = selected_date_df.iloc[-1]

                selected_date_change = (
                    latest_probability
                    - selected_date_row["probability"]
                )
            else:
                selected_date_change = None

            card_data.append(
                {
                    "market_name": market_row["market_name"],
                    "probability": latest_probability,
                    "trend_change": trend_change,
                    "selected_date_change": selected_date_change,
                    "volume": latest["volume"]
                }
            )


        if card_data:

            cols = st.columns(
                min(len(card_data), 3)
            )

            for col, market in zip(
                cols,
                card_data[:3]
            ):

                with col:

                    with st.container(border=True):

                        st.markdown(
                            "### 🌐 Geopolitical Issue"
                        )

                        st.caption(
                            market["market_name"]
                        )




                        weekly_text = (
                            f"{market['trend_change']:+.1f} percentage points vs last week"
                            if market["trend_change"] is not None
                            else "N/A vs last week"
                        )

                        st.metric(
                            "Probability",
                            f"{market['probability']:.1f}%",
                            weekly_text
                        )

                        selected_change = market["selected_date_change"]

                        if selected_change is not None:
                            st.caption(
                                f"Change vs selected date: "
                                f"{selected_change:+.1f} percentage points"
                            )
                        else:
                            st.caption(
                                "Change vs selected date: N/A"
                            )




                        st.caption(
                            f"Volume: {format_volume(market['volume'])}"
                        )

        else:

            st.info(
                "No geopolitical markets available."
            )

    else:

        st.info(
            "No geopolitical markets available."
        )

    st.divider()


# ============================================================
# LATEST SNAPSHOT
# ============================================================



latest_date = filtered_df["date"].max()

latest_df = filtered_df[
    filtered_df["date"] == latest_date
].copy()





# ============================================================
# DETERMINE VIEW TYPE
# ============================================================


is_nomination = (
    selected_subtype != "All"
    and "Nomination" in selected_subtype
)

is_general_election = (
    selected_subtype == "General Election"
)

is_geopolitical = (
    selected_elections == "Geopolitical"
)




# ============================================================
# CANDIDATE PROFILE
# ============================================================

if selected_candidate != "All":

    candidate_history = filtered_df[
        filtered_df["candidate"] == selected_candidate
    ].copy()



    # --------------------------------------------------------
    # Candidate selected with Subtype = All
    # --------------------------------------------------------

    if selected_subtype == "All":

        is_party_profile = (
            not candidate_history.empty
            and (
                candidate_history["election_subtype"] == "Parliamentary"
            ).any()
        )

        profile_type = (
            "Party Profile"
            if is_party_profile
            else "Candidate Profile"
        )

        st.title(
            f"{selected_candidate} — {profile_type}"
        )

        available_stages = (
            candidate_history["election_subtype"]
            .dropna()
            .unique()
            .tolist()
        )

        for stage in [
            "General Election",
            "Democratic Nomination",
            "Republican Nomination",
            "Presidential",
            "Parliamentary",
            "Prime Minister",
            "Other"
        ]:

            if stage not in available_stages:
                continue

            stage_history = candidate_history[
                candidate_history["election_subtype"] == stage
            ].copy()

            if stage_history.empty:
                continue

            st.subheader(stage)

            stage_trends = get_candidate_trends(
                stage_history,
                full_history=history_df
            )

            if stage_trends.empty:
                continue

            stage_info = stage_trends.iloc[0]

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric(
                    "Probability",
                    f"{stage_info['latest_probability']:.1f}%"
                )

            with col2:
                st.metric(
                    "Change vs selected period",
                    (
                        f"{stage_info['probability_change']:+.1f} pp"
                        if pd.notna(
                            stage_info["probability_change"]
                        )
                        else "N/A"
                    )
                )

            with col3:
                st.metric(
                    "Change vs last week",
                    (
                        f"{stage_info['weekly_probability_change']:+.1f} pp"
                        if pd.notna(
                            stage_info["weekly_probability_change"]
                        )
                        else "N/A"
                    )
                )

            with col4:
                st.metric(
                    "Trend",
                    stage_info["trend"]
                )

            with col5:
                st.metric(
                    "Volume",
                    (
                        f"{stage_info['latest_volume'] / 1_000_000:.1f}M"
                        if pd.notna(
                            stage_info["latest_volume"]
                        )
                        else "N/A"
                    )
                )

            # Historical probability
            st.subheader("Historical Probability")

            chart_data = stage_history[
                ["date", "probability"]
            ].dropna().copy()

            chart_data = (
                chart_data
                .sort_values("date")
                .drop_duplicates(subset=["date"])
            )

            chart = (
                alt.Chart(chart_data)
                .mark_line(point=True)
                .encode(
                    x=alt.X(
                        "date:T",
                        title="Date"
                    ),
                    y=alt.Y(
                        "probability:Q",
                        title="Probability (%)"
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "date:T",
                            title="Date",
                            format="%d %b %Y"
                        ),
                        alt.Tooltip(
                            "probability:Q",
                            title="Probability",
                            format=".1f"
                        )
                    ]
                )
                .properties(
                    height=350
                )
            )

            st.altair_chart(
                chart,
                width="stretch"
            )

            # Market Information
            st.subheader("Market Information")

            market_info = stage_history.sort_values(
                "date"
            ).iloc[-1]

            info_col1, info_col2 = st.columns(2)

            with info_col1:
                st.write(
                    "**Election / Stage:**",
                    market_info["election_subtype"]
                )

                st.write(
                    "**Market Question:**",
                    market_info["event"]
                )

                st.write(
                    "**Entrance Date:**",
                    pd.to_datetime(
                        stage_info["entrance_date"]
                    ).strftime("%d %b %Y")
                )

            with info_col2:
                st.write(
                    "**Latest Observation:**",
                    pd.to_datetime(
                        market_info["date"]
                    ).strftime("%d %b %Y")
                )

                st.write(
                    "**Volume:**",
                    (
                        f"{market_info['volume'] / 1_000_000:.1f}M"
                        if pd.notna(market_info["volume"])
                        else "N/A"
                    )
                )

    # --------------------------------------------------------
    # Candidate selected with a specific Subtype
    # --------------------------------------------------------

    else:

        st.title(
            f"{selected_candidate} — {selected_subtype}"
        )

        trends = get_candidate_trends(
            candidate_history,
            full_history=history_df
        )

        if not trends.empty:

            candidate_info = trends.iloc[0]

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric(
                    "Probability",
                    f"{candidate_info['latest_probability']:.1f}%"
                )

            with col2:
                st.metric(
                    "Change vs selected period",
                    (
                        f"{candidate_info['probability_change']:+.1f} pp"
                        if pd.notna(
                            candidate_info["probability_change"]
                        )
                        else "N/A"
                    )
                )

            with col3:
                st.metric(
                    "Change vs last week",
                    (
                        f"{candidate_info['weekly_probability_change']:+.1f} pp"
                        if pd.notna(
                            candidate_info["weekly_probability_change"]
                        )
                        else "N/A"
                    )
                )

            with col4:
                st.metric(
                    "Trend",
                    candidate_info["trend"]
                )

            with col5:
                st.metric(
                    "Volume",
                    (
                        f"{candidate_info['latest_volume'] / 1_000_000:.1f}M"
                        if pd.notna(
                            candidate_info["latest_volume"]
                        )
                        else "N/A"
                    )
                )

            st.subheader("Historical Probability")

            chart_data = candidate_history[
                ["date", "probability"]
            ].dropna().copy()

            chart_data = (
                chart_data
                .sort_values("date")
                .drop_duplicates(subset=["date"])
            )

            chart = (
                alt.Chart(chart_data)
                .mark_line(point=True)
                .encode(
                    x=alt.X(
                        "date:T",
                        title="Date"
                    ),
                    y=alt.Y(
                        "probability:Q",
                        title="Probability (%)"
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "date:T",
                            title="Date",
                            format="%d %b %Y"
                        ),
                        alt.Tooltip(
                            "probability:Q",
                            title="Probability",
                            format=".1f"
                        )
                    ]
                )
                .properties(
                    height=350
                )
            )

            st.altair_chart(
                chart,
                width="stretch"
            )

            st.subheader("Market Information")

            market_info = candidate_history.sort_values(
                "date"
            ).iloc[-1]

            info_col1, info_col2 = st.columns(2)

            with info_col1:
                st.write(
                    "**Election / Stage:**",
                    market_info["election_subtype"]
                )

                st.write(
                    "**Market Question:**",
                    market_info["event"]
                )

                st.write(
                    "**Entrance Date:**",
                    pd.to_datetime(
                        candidate_info["entrance_date"]
                    ).strftime("%d %b %Y")
                )

            with info_col2:
                st.write(
                    "**Latest Observation:**",
                    pd.to_datetime(
                        market_info["date"]
                    ).strftime("%d %b %Y")
                )

                st.write(
                    "**Volume:**",
                    (
                        f"{market_info['volume'] / 1_000_000:.1f}M"
                        if pd.notna(market_info["volume"])
                        else "N/A"
                    )
                )

        else:
            st.info(
                "No candidate market information available."
            )


elif selected_election_type == "US Midterms":



    st.title("🇺🇸 Midterm Elections")

    # ========================================================
    # MIDTERM OVERVIEW
    # ========================================================

    if selected_subtype == "All":

        st.subheader("Midterm Overview")

        # ----------------------------------------------------
        # Apply State filter to Midterm Overview
        # ----------------------------------------------------

        overview_df = filtered_df.copy()

        if selected_state != "All":
            overview_df = overview_df[
                overview_df["state"] == selected_state
            ]



        overview_rows = []

        overview_subtypes = [
            ("Senate", "🏛️ Senate"),
            ("House", "🏛️ House"),
            ("Governor", "🏛️ Governor"),
            ("Democratic Nomination", "🔵 Democratic Nomination"),
            ("Republican Nomination", "🔴 Republican Nomination"),
            ("Other", "📋 Other")
        ]

        for subtype, label in overview_subtypes:

            subtype_history = overview_df[
                overview_df["election_subtype"] == subtype
            ].copy()

            if subtype_history.empty:
                continue

            latest_date = subtype_history["date"].max()

            latest_markets = subtype_history[
                subtype_history["date"] == latest_date
            ].copy()

            latest_markets = latest_markets.drop_duplicates(
                subset=["market_id"]
            )

            leader_row = latest_markets.loc[
                latest_markets["probability"].idxmax()
            ]

            one_week_ago = latest_date - pd.Timedelta(days=7)

            previous_markets = history_df[
                (history_df["election_subtype"] == subtype) &
                (history_df["date"] == one_week_ago)
            ].copy()

            previous_markets = previous_markets[
                [
                    "market_id",
                    "probability"
                ]
            ].rename(
                columns={
                    "probability": "previous_probability"
                }
            )

            overview_table = latest_markets.merge(
                previous_markets,
                on="market_id",
                how="left"
            )

            overview_table["weekly_change"] = (
                overview_table["probability"]
                - overview_table["previous_probability"]
            )

            overview_table["trend"] = overview_table[
                "weekly_change"
            ].apply(
                lambda x:
                    "Up" if x > 0
                    else (
                        "Down" if x < 0
                        else "Unchanged"
                    )
                    if pd.notna(x)
                    else "N/A"
            )

            leader_change = overview_table.loc[
                overview_table["market_id"]
                == leader_row["market_id"],
                "weekly_change"
            ].iloc[0]

            leader_trend = overview_table.loc[
                overview_table["market_id"]
                == leader_row["market_id"],
                "trend"
            ].iloc[0]

            leader_name = (
                leader_row["candidate"]
                if subtype in [
                    "Democratic Nomination",
                    "Republican Nomination"
                ]
                else leader_row["event"]
            )

            overview_rows.append(
                {
                    "Type": label,
                    "Leader": leader_name,
                    "State": leader_row.get("state"),
                    "Probability": leader_row["probability"],
                    "Change vs last week": leader_change,
                    "Trend": leader_trend,
                    "Volume": leader_row["volume"]
                }
            )

        # ----------------------------------------------------
        # Overview KPI cards
        # ----------------------------------------------------

        for i in range(0, len(overview_rows), 3):

            row = overview_rows[i:i + 3]

            cols = st.columns(3)

            for col, item in zip(cols, row):

                with col:

                    with st.container(border=True):

                        st.markdown(
                            f"### {item['Type']}"
                        )

                        st.caption(
                            item["Leader"]
                        )

                        st.metric(
                            "Probability",
                            f"{item['Probability']:.1f}%",
                            (
                                f"{item['Change vs last week']:+.1f} pp vs last week"
                                if pd.notna(
                                    item["Change vs last week"]
                                )
                                else None
                            )
                        )

                        st.metric(
                            "Trend",
                            item["Trend"]
                        )

                        st.caption(
                            f"Volume: {format_volume(item['Volume'])}"
                        )
        # ----------------------------------------------------
        # Overview leader table
        # ----------------------------------------------------

        if overview_rows:

            st.subheader("Current Midterm Leaders")

            overview_display = pd.DataFrame(
                overview_rows
            )

            overview_display["Probability"] = (
                overview_display["Probability"]
                .map(
                    lambda x:
                        f"{x:.1f}%"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            overview_display["Change vs last week"] = (
                overview_display["Change vs last week"]
                .map(
                    lambda x:
                        f"{x:+.1f} pp"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            overview_display["Volume"] = (
                overview_display["Volume"]
                .map(
                    lambda x:
                        f"{x / 1_000_000:.1f}M"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            overview_display = overview_display.rename(
                columns={
                    "Type": "Market Type",
                    "Leader": "Leader",
                    "State": "State",
                    "Probability": "Probability",
                    "Change vs last week": "Change vs last week",
                    "Trend": "Trend",
                    "Volume": "Volume"
                }
            )

            st.dataframe(
                overview_display,
                width="stretch",
                hide_index=True
            )

    # ========================================================
    # MIDTERM NOMINATIONS
    # ========================================================

    if selected_subtype in [
        "Democratic Nomination",
        "Republican Nomination"
    ]:

        st.subheader(f"🗳️ {selected_subtype}")

        nomination_history = filtered_df[
            filtered_df["election_subtype"] == selected_subtype
        ].copy()

        if not nomination_history.empty:

            latest_date = nomination_history["date"].max()

            latest_markets = nomination_history[
                nomination_history["date"] == latest_date
            ].copy()

            latest_markets = latest_markets.drop_duplicates(
                subset=["market_id"]
            )

            latest_markets = latest_markets.sort_values(
                "probability",
                ascending=False
            )

            leader_row = latest_markets.iloc[0]

            leader_market = leader_row["event"]
            leader_probability = leader_row["probability"]
            leader_volume = leader_row["volume"]

            one_week_ago = latest_date - pd.Timedelta(days=7)

            previous_markets = history_df[
                (history_df["election_subtype"] == selected_subtype) &
                (history_df["date"] == one_week_ago)
            ].copy()

            previous_markets = previous_markets[
                [
                    "market_id",
                    "probability"
                ]
            ].rename(
                columns={
                    "probability": "previous_probability"
                }
            )

            nomination_table = latest_markets.merge(
                previous_markets,
                on="market_id",
                how="left"
            )

            nomination_table["weekly_change"] = (
                nomination_table["probability"]
                - nomination_table["previous_probability"]
            )

            nomination_table["trend"] = nomination_table[
                "weekly_change"
            ].apply(
                lambda x:
                    "Up" if x > 0
                    else (
                        "Down" if x < 0
                        else "Unchanged"
                    )
                    if pd.notna(x)
                    else "N/A"
            )

            leader_change = nomination_table.loc[
                nomination_table["market_id"] == leader_row["market_id"],
                "weekly_change"
            ].iloc[0]

            leader_trend = nomination_table.loc[
                nomination_table["market_id"] == leader_row["market_id"],
                "trend"
            ].iloc[0]

            st.markdown(
                f"**Leader Market: {leader_market}**"
            )

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Probability",
                    f"{leader_probability:.1f}%"
                )

            with col2:
                st.metric(
                    "Change vs last week",
                    (
                        f"{leader_change:+.1f} pp"
                        if pd.notna(leader_change)
                        else "N/A"
                    )
                )

            with col3:
                st.metric(
                    "Trend",
                    leader_trend
                )

            with col4:
                st.metric(
                    "Total Volume Invested in the Market",
                    (
                        f"{leader_volume / 1_000_000:.1f}M"
                        if pd.notna(leader_volume)
                        else "N/A"
                    )
                )


            st.subheader("Current Candidate Probabilities")

            chart_data = latest_markets[
                ["candidate", "probability"]
            ].copy()

            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X(
                    "probability:Q",
                    title="Probability (%)"
                ),
                y=alt.Y(
                    "candidate:N",
                    sort="-x",
                    title=None
                ),
                tooltip=[
                    alt.Tooltip(
                        "candidate:N",
                        title="Candidate"
                ),
                    alt.Tooltip(
                        "probability:Q",
                        title="Probability",
                        format=".1f"
                    )
                ]
                ).properties(
                     height=300
            )

            st.altair_chart(
                chart,
                width="stretch"
            )




            st.subheader("Current Nomination Markets")

            nomination_table = nomination_table.sort_values(
                "probability",
                ascending=False
            )

            display_table = nomination_table[
                [
                    "candidate",
                    "state",
                    "probability",
                    "weekly_change",
                    "trend",
                    "volume"
                ]
            ].copy()

            display_table = display_table.rename(
                columns={
                    "candidate": "Candidate",
                    "state": "State",
                    "probability": "Probability",
                    "weekly_change": "Change vs last week",
                    "trend": "Trend",
                    "volume": "Volume"
                }
            )

            display_table["Probability"] = (
                display_table["Probability"]
                .map(
                    lambda x:
                        f"{x:.1f}%"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            display_table["Change vs last week"] = (
                display_table["Change vs last week"]
                .map(
                    lambda x:
                        f"{x:+.1f} pp"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            display_table["Volume"] = (
                display_table["Volume"]
                .map(
                    lambda x:
                        f"{x / 1_000_000:.1f}M"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            st.dataframe(
                display_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "Candidate": st.column_config.TextColumn(
                        "Candidate",
                        width="medium"
                    ),
                    "State": st.column_config.TextColumn(
                        "State",
                        width="medium"
                    ),
                    "Probability": st.column_config.TextColumn(
                        "Probability",
                        width="small"
                    ),
                    "Change vs last week": st.column_config.TextColumn(
                        "Change vs last week",
                        width="small"
                    ),
                    "Trend": st.column_config.TextColumn(
                        "Trend",
                        width="small"
                    ),
                    "Volume": st.column_config.TextColumn(
                        "Volume",
                        width="small"
                    )
                }
            )


    # ========================================================
    # SENATE
    # ========================================================

    if selected_subtype == "Senate":

        st.subheader("🏛️ Senate")

        senate_history = filtered_df[
            (filtered_df["election_subtype"] == "Senate") &
            (
                (filtered_df["state"] == selected_state)
                if selected_state != "All"
                else True
            )
        ].copy()

        if not senate_history.empty:

            latest_date = senate_history["date"].max()

            latest_markets = senate_history[
                senate_history["date"] == latest_date
            ].copy()

            latest_markets = latest_markets.drop_duplicates(
            subset=["market_id"]
            )

            leader_row = latest_markets.loc[
                latest_markets["probability"].idxmax()
            ]

            leader_market = leader_row["event"]
            leader_probability = leader_row["probability"]

            one_week_ago = latest_date - pd.Timedelta(days=7)

            previous_markets = history_df[
                (history_df["election_subtype"] == "Senate") &
                (history_df["date"] == one_week_ago)
            ].copy()

            previous_markets = previous_markets[
                [
                    "market_id",
                    "probability"
                ]
            ].rename(
                columns={
                    "probability": "previous_probability"
                }
            )

            senate_table = latest_markets.merge(
                previous_markets,
                on="market_id",
                how="left"
            )

            senate_table["weekly_change"] = (
                senate_table["probability"]
                - senate_table["previous_probability"]
            )

            senate_table["trend"] = senate_table[
                "weekly_change"
            ].apply(
                lambda x:
                    "Up" if x > 0
                    else (
                        "Down" if x < 0
                        else "Unchanged"
                    )
                    if pd.notna(x)
                    else "N/A"
            )

            leader_volume = leader_row["volume"]

            st.markdown(
                f"**Leader Market: {leader_market}**"
            )

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Probability",
                    f"{leader_probability:.1f}%"
                )

            leader_change = senate_table.loc[
                senate_table["market_id"]
                == leader_row["market_id"],
                "weekly_change"
            ].iloc[0]

            with col2:
                st.metric(
                    "Change vs last week",
                    (
                        f"{leader_change:+.1f} pp"
                        if pd.notna(leader_change)
                        else "N/A"
                    )
                )

            leader_trend = senate_table.loc[
                senate_table["market_id"]
                == leader_row["market_id"],
                "trend"
            ].iloc[0]

            with col3:
                st.metric(
                    "Trend",
                    leader_trend
                )

            with col4:
                st.metric(
                    "Total Volume Invested in the Market",
                    (
                        f"{leader_volume / 1_000_000:.1f}M"
                        if pd.notna(leader_volume)
                        else "N/A"
                    )
                )

            if selected_subtype == "Senate":
                st.subheader("Probability by Senate Market")

                chart_data = senate_table[
                    [
                        "event",
                        "probability",
                        "weekly_change",
                        "trend",
                        "volume"
                    ]
                ].copy()

                senate_table = senate_table.sort_values(
                    "probability",
                    ascending=False
                )

                chart_data = senate_table[
                    [
                        "event",
                        "probability",
                        "weekly_change",
                        "trend",
                        "volume"
                    ]
                ].head(10).copy()

                chart_data["short_market"] = chart_data["event"].apply(
                    shorten_market_question
                )


                chart = alt.Chart(chart_data).mark_bar().encode(
                    x=alt.X(
                        "probability:Q",
                        title="Probability (%)"
                    ),
                    y=alt.Y(
                        "short_market:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(
                            labelLimit=300
                        )
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "event:N",
                            title="Market"
                        ),
                        alt.Tooltip(
                            "probability:Q",
                            title="Probability",
                            format=".1f"
                        ),
                        alt.Tooltip(
                            "weekly_change:Q",
                            title="Change vs last week",
                            format="+.1f"
                        ),
                        alt.Tooltip(
                            "trend:N",
                            title="Trend"
                        ),
                        alt.Tooltip(
                            "volume:Q",
                            title="Volume",
                            format=",.0f"
                        )
                    ]
                ).properties(
                    height=450
                )

                st.altair_chart(
                    chart,
                    width="stretch"
                )

            st.subheader("Current Senate Markets")

            senate_table = senate_table.sort_values(
                "probability",
                ascending=False
            )

            display_table = senate_table[
                [
                    "event",
                    "probability",
                    "weekly_change",
                    "trend",
                    "volume"
                ]
            ].copy()

            display_table = display_table.rename(
                columns={
                    "event": "Market",
                    "probability": "Probability",
                    "weekly_change": "Change vs last week",
                    "trend": "Trend",
                    "volume": "Volume"
                }
            )

            display_table["Probability"] = (
                display_table["Probability"]
                .map(
                    lambda x:
                        f"{x:.1f}%"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            display_table["Change vs last week"] = (
                display_table["Change vs last week"]
                .map(
                    lambda x:
                        f"{x:+.1f} pp"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            display_table["Volume"] = (
                display_table["Volume"]
                .map(
                    lambda x:
                        f"{x / 1_000_000:.1f}M"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            st.dataframe(
                display_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "Market": st.column_config.TextColumn(
                        "Market",
                        width="large"
                    ),
                    "Probability": st.column_config.TextColumn(
                        "Probability",
                        width="small"
                    ),
                    "Change vs last week": st.column_config.TextColumn(
                        "Change vs last week",
                        width="small"
                    ),
                    "Trend": st.column_config.TextColumn(
                        "Trend",
                        width="small"
                    ),
                    "Volume": st.column_config.TextColumn(
                        "Volume",
                        width="small"
                    )
                }
            )

        else:

            st.info(
                "No Senate markets available."
            )



    # ========================================================
    # HOUSE
    # ========================================================
    if selected_subtype == "House":
        st.subheader("🏛️ House")


        house_history = filtered_df[
                filtered_df["election_subtype"] == "House"
        ].copy()

        if selected_state != "All":
            house_history = house_history[
                house_history["state"] == selected_state
            ]


        if not house_history.empty:

            latest_date = house_history["date"].max()

            latest_markets = house_history[
                house_history["date"] == latest_date
            ].copy()

            latest_markets = latest_markets.drop_duplicates(
                subset=["market_id"]
            )

            leader_row = latest_markets.loc[
                latest_markets["probability"].idxmax()
            ]

            leader_market = leader_row["event"]
            leader_probability = leader_row["probability"]

            one_week_ago = latest_date - pd.Timedelta(days=7)

            previous_markets = history_df[
                (history_df["election_subtype"] == "House") &
                (history_df["date"] == one_week_ago)
            ].copy()

            previous_markets = previous_markets[
                [
                    "market_id",
                    "probability"
                ]
            ].rename(
                columns={
                    "probability": "previous_probability"
                }
            )

            house_table = latest_markets.merge(
                previous_markets,
                on="market_id",
                how="left"
            )

            house_table["weekly_change"] = (
                house_table["probability"]
                - house_table["previous_probability"]
            )

            house_table["trend"] = house_table[
                "weekly_change"
            ].apply(
                lambda x:
                    "Up" if x > 0
                    else (
                        "Down" if x < 0
                        else "Unchanged"
                    )
                if pd.notna(x)
                else "N/A"
            )

            leader_volume = leader_row["volume"]

            st.markdown(
                 f"**Leader Market: {leader_market}**"
            )

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Probability",
                    f"{leader_probability:.1f}%"
                )

            leader_change = house_table.loc[
                house_table["market_id"]
                == leader_row["market_id"],
                "weekly_change"
            ].iloc[0]

            with col2:
                st.metric(
                    "Change vs last week",
                    (
                        f"{leader_change:+.1f} pp"
                        if pd.notna(leader_change)
                        else "N/A"
                    )
                )

            leader_trend = house_table.loc[
                house_table["market_id"]
                == leader_row["market_id"],
                "trend"
            ].iloc[0]

            with col3:
                st.metric(
                    "Trend",
                    leader_trend
                )

            with col4:
                st.metric(
                    "Total Volume Invested in the Market",
                        (
                            f"{leader_volume / 1_000_000:.1f}M"
                            if pd.notna(leader_volume)
                            else "N/A"
                        )
                    )


            if selected_subtype == "House":

                st.subheader("Probability by House Market")

                house_table = house_table.sort_values(
                    "probability",
                    ascending=False
                )

                chart_data = house_table[
                    [
                        "event",
                        "probability",
                        "weekly_change",
                        "trend",
                        "volume"
                    ]
                ].head(10).copy()

                chart_data["short_market"] = chart_data["event"].apply(
                    shorten_market_question
                )

                chart = alt.Chart(chart_data).mark_bar().encode(
                    x=alt.X(
                        "probability:Q",
                        title="Probability (%)"
                    ),
                    y=alt.Y(
                        "short_market:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(
                        labelLimit=300
                    )
                ),
                tooltip=[
                    alt.Tooltip(
                        "event:N",
                        title="Market"
                    ),
                    alt.Tooltip(
                        "probability:Q",
                        title="Probability",
                        format=".1f"
                    ),
                    alt.Tooltip(
                        "weekly_change:Q",
                        title="Change vs last week",
                        format="+.1f"
                    ),
                    alt.Tooltip(
                        "trend:N",
                        title="Trend"
                    ),
                    alt.Tooltip(
                        "volume:Q",
                        title="Volume",
                        format=",.0f"
                    )
                ]
                ).properties(
                    height=450
                )

                st.altair_chart(
                    chart,
                    width="stretch"
                )



            st.subheader("Current House Markets")

            house_table = house_table.sort_values(
                "probability",
                ascending=False
            )

            display_table = house_table[
                [
                    "event",
                    "probability",
                    "weekly_change",
                    "trend",
                    "volume"
                ]
            ].copy()

            display_table = display_table.rename(
                columns={
                    "event": "Market",
                    "probability": "Probability",
                    "weekly_change": "Change vs last week",
                    "trend": "Trend",
                    "volume": "Volume"
                }
            )

            display_table["Probability"] = (
                display_table["Probability"]
                .map(
                    lambda x:
                        f"{x:.1f}%"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            display_table["Change vs last week"] = (
                display_table["Change vs last week"]
                .map(
                    lambda x:
                        f"{x:+.1f} pp"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            display_table["Volume"] = (
                display_table["Volume"]
                .map(
                    lambda x:
                        f"{x / 1_000_000:.1f}M"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            st.dataframe(
                display_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "Market": st.column_config.TextColumn(
                        "Market",
                        width="large"
                    ),
                    "Probability": st.column_config.TextColumn(
                        "Probability",
                        width="small"
                    ),
                    "Change vs last week": st.column_config.TextColumn(
                        "Change vs last week",
                        width="small"
                    ),
                    "Trend": st.column_config.TextColumn(
                        "Trend",
                         width="small"
                    ),
                    "Volume": st.column_config.TextColumn(
                        "Volume",
                        width="small"
                    )
                }
            )

        else:

            st.info(
                "No House markets available."
            )



    # ========================================================
    # GOVERNOR
    # ========================================================


    if selected_subtype == "Governor":
        st.subheader("🏛️ Governor")



        governor_history = filtered_df[
            (filtered_df["election_subtype"] == "Governor") &
            (
                (filtered_df["state"] == selected_state)
                if selected_state != "All"
                else True
            )
        ].copy()


        if not governor_history.empty:

            latest_date = governor_history["date"].max()

            latest_markets = governor_history[
                governor_history["date"] == latest_date
            ].copy()

            latest_markets = latest_markets.drop_duplicates(
                subset=["market_id"]
            )

            leader_row = latest_markets.loc[
                latest_markets["probability"].idxmax()
            ]

            leader_market = leader_row["event"]
            leader_probability = leader_row["probability"]

            one_week_ago = latest_date - pd.Timedelta(days=7)

            previous_markets = history_df[
                (history_df["election_subtype"] == "Governor") &
                (history_df["date"] == one_week_ago)
            ].copy()

            previous_markets = previous_markets[
                [
                    "market_id",
                    "probability"
                ]
                ].rename(
                columns={
                    "probability": "previous_probability"
                }
            )

            governor_table = latest_markets.merge(
                previous_markets,
                on="market_id",
                how="left"
            )

            governor_table["weekly_change"] = (
                governor_table["probability"]
                - governor_table["previous_probability"]
            )

            governor_table["trend"] = governor_table[
                "weekly_change"
            ].apply(
                lambda x:
                    "Up" if x > 0
                    else (
                        "Down" if x < 0
                        else "Unchanged"
                    )
                    if pd.notna(x)
                    else "N/A"
            )

            leader_volume = leader_row["volume"]

            st.markdown(
                f"**Leader Market: {leader_market}**"
            )

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Probability",
                    f"{leader_probability:.1f}%"
                )

            leader_change = governor_table.loc[
                governor_table["market_id"]
                == leader_row["market_id"],
                "weekly_change"
            ].iloc[0]

            with col2:
                st.metric(
                    "Change vs last week",
                    (
                        f"{leader_change:+.1f} pp"
                        if pd.notna(leader_change)
                        else "N/A"
                    )
                )

            leader_trend = governor_table.loc[
                governor_table["market_id"]
                == leader_row["market_id"],
                "trend"
            ].iloc[0]

            with col3:
                st.metric(
                    "Trend",
                    leader_trend
                )

            with col4:
                st.metric(
                    "Total Volume Invested in the Market",
                    (
                        f"{leader_volume / 1_000_000:.1f}M"
                        if pd.notna(leader_volume)
                        else "N/A"
                    )
                )


            if selected_subtype == "Governor":

                st.subheader("Probability by Governor Market")

                governor_table = governor_table.sort_values(
                    "probability",
                    ascending=False
                )

                chart_data = governor_table[
                    [
                        "event",
                        "probability",
                        "weekly_change",
                        "trend",
                        "volume"
                    ]
                ].head(10).copy()

                chart_data["short_market"] = chart_data["event"].apply(
                    shorten_market_question
                )

                chart = alt.Chart(chart_data).mark_bar().encode(
                    x=alt.X(
                        "probability:Q",
                        title="Probability (%)"
                    ),
                    y=alt.Y(
                        "short_market:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(
                        labelLimit=300
                    )
                ),
                tooltip=[
                    alt.Tooltip(
                        "event:N",
                        title="Market"
                    ),
                    alt.Tooltip(
                        "probability:Q",
                        title="Probability",
                        format=".1f"
                    ),
                    alt.Tooltip(
                        "weekly_change:Q",
                        title="Change vs last week",
                        format="+.1f"
                    ),
                    alt.Tooltip(
                        "trend:N",
                        title="Trend"
                    ),
                    alt.Tooltip(
                        "volume:Q",
                        title="Volume",
                        format=",.0f"
                    )
                ]
                ).properties(
                    height=450
                )

                st.altair_chart(
                    chart,
                    width="stretch"
                )


            st.subheader("Current Governor Markets")

            governor_table = governor_table.sort_values(
                "probability",
                ascending=False
            )

            display_table = governor_table[
                [
                    "event",
                    "probability",
                    "weekly_change",
                    "trend",
                    "volume"
                ]
            ].copy()

            display_table = display_table.rename(
                columns={
                    "event": "Market",
                    "probability": "Probability",
                    "weekly_change": "Change vs last week",
                    "trend": "Trend",
                    "volume": "Volume"
                }
            )

            display_table["Probability"] = (
                display_table["Probability"]
                .map(
                    lambda x:
                        f"{x:.1f}%"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            display_table["Change vs last week"] = (
                display_table["Change vs last week"]
                .map(
                    lambda x:
                        f"{x:+.1f} pp"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            display_table["Volume"] = (
                display_table["Volume"]
                .map(
                    lambda x:
                        f"{x / 1_000_000:.1f}M"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            st.dataframe(
                display_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "Market": st.column_config.TextColumn(
                        "Market",
                        width="large"
                    ),
                    "Probability": st.column_config.TextColumn(
                        "Probability",
                        width="small"
                    ),
                    "Change vs last week": st.column_config.TextColumn(
                        "Change vs last week",
                        width="small"
                    ),
                    "Trend": st.column_config.TextColumn(
                        "Trend",
                        width="small"
                    ),
                    "Volume": st.column_config.TextColumn(
                        "Volume",
                        width="small"
                    )
                }
            )

        else:

            st.info(
                "No Governor markets available."
            )

    # ========================================================
    # OTHER MIDTERM MARKETS
    # ========================================================

    if selected_subtype == "Other":

        st.subheader("📋 Other Midterm Markets")

        other_history = filtered_df[
            filtered_df["election_subtype"] == "Other"
        ].copy()

        if selected_state != "All":
            other_history = other_history[
                other_history["state"] == selected_state
            ]

        if not other_history.empty:

            latest_date = other_history["date"].max()

            other_table = other_history[
                other_history["date"] == latest_date
            ].copy()

            other_table = other_table.drop_duplicates(
                subset=["market_id"]
            )

            other_table = other_table.sort_values(
                "probability",
                ascending=False
            )

            st.subheader("Current Other Markets")

            display_table = other_table[
                [
                    "event",
                    "probability",
                    "volume"
                ]
            ].copy()

            display_table = display_table.rename(
                columns={
                    "event": "Market",
                    "probability": "Probability",
                    "volume": "Volume"
                }
            )

            display_table["Probability"] = (
                display_table["Probability"].map(
                    lambda x: f"{x:.1f}%"
                    if pd.notna(x) else "N/A"
                )
            )

            display_table["Volume"] = (
                display_table["Volume"].map(
                    lambda x: f"{x / 1_000_000:.1f}M"
                    if pd.notna(x) else "N/A"
                )
            )

            st.dataframe(
                display_table,
                width="stretch",
                hide_index=True
            )

        else:
            st.info("No Other midterm markets available.")


elif selected_election_type == "US State/Local":

    st.title("🇺🇸 State/Local Elections")

    overview_df = filtered_df.copy()

    st.write(
        overview_df[
            overview_df["election_subtype"].isin(
                ["Mayoral", "Other"]
            )
        ][
            ["event", "market_name", "state", "election_subtype"]
        ].drop_duplicates().head(20)
    )

    if selected_state != "All":
        overview_df = overview_df[
            overview_df["state"] == selected_state
        ]

    if selected_subtype == "All":



        state_local_cards = []

        state_local_subtypes = [
            ("🔵 Democratic Nomination", "Democratic Nomination"),
            ("🔴 Republican Nomination", "Republican Nomination"),
            ("🏙️ Mayoral Elections", "Mayoral"),
            ("📋 Other Elections", "Other"),
        ]

        for title, subtype in state_local_subtypes:

            election_df = overview_df[
                overview_df["election_subtype"] == subtype
            ].copy()

            if not election_df.empty:
                state_local_cards.append((title, election_df))

        card_columns = st.columns(len(state_local_cards))

        for card_col, (title, election_df) in zip(
            card_columns,
            state_local_cards
        ):

            with card_col:

                with st.container(border=True):

                    st.markdown(f"### {title}")

                    if not election_df.empty:

                        latest_date = election_df["date"].max()

                        latest_df = election_df[
                            election_df["date"] == latest_date
                        ].copy()

                        if not latest_df.empty:

                            leader_row = latest_df.loc[
                                latest_df["probability"].idxmax()
                            ]

                            leader = leader_row["candidate"]
                            probability = leader_row["probability"]
                            market_name = leader_row["market_name"]
                            volume = leader_row["volume"]

                            # --------------------------------
                            # Change vs last week
                            # --------------------------------

                            previous_date = latest_date - pd.Timedelta(days=7)

                            previous_df = history_df[
                                (history_df["date"] == previous_date)
                                & (
                                    history_df["election_subtype"]
                                    == election_df["election_subtype"].iloc[0]
                                )
                                & (
                                    history_df["market_id"]
                                    == leader_row["market_id"]
                                )
                            ].copy()

                            if selected_state != "All":
                                previous_df = previous_df[
                                    previous_df["state"]
                                    == selected_state
                                ]

                            if not previous_df.empty:

                                previous_probability = (
                                    previous_df.iloc[0]["probability"]
                                )

                                change = (
                                    probability
                                    - previous_probability
                                )

                            else:

                                change = None

                            # --------------------------------
                            # Display
                            # --------------------------------

                            st.caption(
                                market_name
                            )

                            st.metric(
                                "Leader",
                                leader
                            )

                            if change is not None:

                                st.metric(
                                    "Probability",
                                    f"{probability:.1f}%",
                                    f"{change:+.1f} pp vs last week"
                                )

                            else:

                                st.metric(
                                    "Probability",
                                    f"{probability:.1f}%"
                                )

                            st.caption(
                                f"Volume: {format_volume(volume)}"
                            )

                        else:
                            st.info("No market available.")

                    else:
                        st.info("No market available.")

        st.divider()


    elif selected_subtype == "Other":

        st.title("🇺🇸 Other State/Local Markets")

        other_df = overview_df[
            overview_df["election_subtype"] == "Other"
        ].copy()

        if not other_df.empty:

            # Latest snapshot
            latest_date = other_df["date"].max()

            latest_df = other_df[
                other_df["date"] == latest_date
            ].copy()

            # Use the market question as the display label
            latest_df["event"] = latest_df["event"].fillna(
                latest_df["market_name"]
            )

            latest_df.loc[
                latest_df["event"].astype(str).str.strip().eq("Question"),
                "event"
            ] = latest_df["market_name"]

            latest_df = latest_df.dropna(
                subset=["event", "probability"]
            )

            if not latest_df.empty:

                # =========================================
                # PREVIOUS WEEK'S PROBABILITIES
                # =========================================

                previous_date = latest_date - pd.Timedelta(days=7)

                previous_df = history_df[
                    history_df["date"] == previous_date
                ][
                    ["market_id", "probability"]
                ].rename(
                    columns={
                        "probability": "previous_probability"
                    }
                )

                # One previous value per market
                previous_df = previous_df.drop_duplicates(
                    subset=["market_id"]
                )

                latest_df = latest_df.merge(
                    previous_df,
                    on="market_id",
                    how="left"
                )

                latest_df["change_vs_last_week"] = (
                    latest_df["probability"]
                    - latest_df["previous_probability"]
                )

                def get_market_trend(change):
                    if pd.isna(change):
                        return "N/A"
                    elif change > 0:
                        return "Up"
                    elif change < 0:
                        return "Down"
                    return "Unchanged"

                latest_df["Trend"] = latest_df[
                    "change_vs_last_week"
                ].apply(get_market_trend)

                # =========================================
                # LEADER QUESTION
                # =========================================

                latest_df = latest_df.sort_values(
                    "probability",
                    ascending=False
                )

                leader_row = latest_df.iloc[0]

                st.subheader("Leader Question")
                st.write(leader_row["event"])

                # =========================================
                # KPI ROW
                # =========================================

                probability = leader_row["probability"]
                change = leader_row["change_vs_last_week"]
                trend = leader_row["Trend"]
                volume = leader_row["volume"]

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Probability",
                        f"{probability:.1f}%"
                    )

                with col2:
                    st.metric(
                        "Change vs Last Week",
                        f"{change:+.1f} pp"
                        if pd.notna(change)
                        else "N/A"
                    )

                with col3:
                    st.metric("Trend", trend)

                with col4:
                    st.metric(
                        "Volume",
                        format_volume(volume)
                    )

                st.divider()

                # =========================================
                # PROBABILITY CHART
                # =========================================

                st.subheader("Probability by Market Question")

                chart_df = latest_df[
                    ["event", "probability"]
                ].copy()

                chart_df["short_question"] = chart_df[
                    "event"
                ].apply(shorten_market_question)

                chart = (
                    alt.Chart(chart_df)
                    .mark_bar()
                    .encode(
                        x=alt.X(
                            "probability:Q",
                            title="Probability (%)"
                        ),
                        y=alt.Y(
                            "short_question:N",
                            sort="-x",
                            title=None,
                            axis=alt.Axis(labelLimit=350)
                        ),
                        tooltip=[
                            alt.Tooltip(
                                "event:N",
                                title="Question"
                            ),
                            alt.Tooltip(
                                "probability:Q",
                                title="Probability",
                                format=".1f"
                            )
                        ]
                    )
                    .properties(
                        height=max(250, len(chart_df) * 35)
                    )
                )

                st.altair_chart(
                    chart,
                    width="stretch"
                )

                # =========================================
                # CURRENT MARKETS TABLE
                # =========================================

                st.subheader("Current Markets")

                table_df = latest_df[
                    [
                        "event",
                        "state",
                        "probability",
                        "change_vs_last_week",
                        "Trend",
                        "volume"
                    ]
                ].copy()

                table_df = table_df.rename(
                    columns={
                        "event": "Question",
                        "state": "State",
                        "probability": "Probability",
                        "change_vs_last_week": "Change vs Last Week",
                        "volume": "Volume"
                    }
                )

                table_df["State"] = table_df["State"].fillna("N/A")

                table_df["Probability"] = table_df[
                    "Probability"
                ].map(lambda x: f"{x:.1f}%")

                table_df["Change vs Last Week"] = table_df[
                    "Change vs Last Week"
                ].map(
                    lambda x: f"{x:+.1f} pp"
                    if pd.notna(x)
                    else "N/A"
                )

                table_df["Volume"] = table_df[
                    "Volume"
                ].map(
                    lambda x: format_volume(x)
                    if pd.notna(x)
                    else "N/A"
                )

                table_df = table_df[
                    [
                        "Question",
                        "State",
                        "Probability",
                        "Change vs Last Week",
                        "Trend",
                        "Volume"
                    ]
                ]

                st.dataframe(
                    table_df,
                    width="stretch",
                    hide_index=True
                )

            else:
                st.info("No valid market questions available.")

        else:
            st.info("No markets available.")

    else:
        nomination_df = overview_df[
            overview_df["election_subtype"] == selected_subtype
        ].copy()

        if not nomination_df.empty:

            latest_date = nomination_df["date"].max()

            latest_df = nomination_df[
                nomination_df["date"] == latest_date
            ].copy()

            # ====================================================
            # LEADER MARKET
            # ====================================================

            leader_row = latest_df.loc[
                latest_df["probability"].idxmax()
            ]

            leader = leader_row["candidate"]
            probability = leader_row["probability"]
            volume = leader_row["volume"]
            market_question = leader_row["event"]

            # ----------------------------------------------------
            # Change vs last week
            # ----------------------------------------------------

            previous_date = latest_date - pd.Timedelta(days=7)

            previous_df = history_df[
                (history_df["date"] == previous_date)
                & (
                    history_df["election_subtype"]
                    == selected_subtype
                )
                & (
                    history_df["market_id"]
                    == leader_row["market_id"]
                )
            ].copy()

            if selected_state != "All":
                previous_df = previous_df[
                    previous_df["state"] == selected_state
                ]

            if not previous_df.empty:

                previous_probability = (
                    previous_df.iloc[0]["probability"]
                )

                change = (
                    probability
                    - previous_probability
                )

            else:

                change = None

            # ====================================================
            # LEADER MARKET
            # ====================================================

            st.subheader("Leader Market")

            st.write(
                market_question
            )

            # ====================================================
            # KPI ROW
            # ====================================================

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Leader",
                    leader
                )

            with col2:
                st.metric(
                    "Probability",
                    f"{probability:.1f}%"
                )

            with col3:

                if change is not None:
                    st.metric(
                        "Change vs last week",
                        f"{change:+.1f} pp"
                    )
                else:
                    st.metric(
                        "Change vs last week",
                        "N/A"
                    )

            with col4:
                st.metric(
                    "Volume",
                    f"{volume:,.0f}"
                )

            st.divider()

            # ====================================================
            # CANDIDATE PROBABILITY
            # ====================================================

            st.subheader("Candidate Probability")

            chart_df = (
                latest_df[
                    ["candidate", "probability"]
                ]
                .dropna(subset=["candidate"])
                .sort_values(
                    "probability",
                    ascending=False
                )
            )

            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "probability:Q",
                        title="Probability (%)"
                    ),
                    y=alt.Y(
                        "candidate:N",
                        sort="-x",
                        title=None
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "candidate:N",
                            title="Candidate"
                        ),
                        alt.Tooltip(
                            "probability:Q",
                            title="Probability",
                            format=".1f"
                        )
                    ]
                )
                .properties(
                    height=max(
                        200,
                        len(chart_df) * 35
                    )
                )
            )

            st.altair_chart(
                chart,
                width="stretch"
            )

            # ====================================================
            # CURRENT NOMINATION MARKETS
            # ====================================================

            st.subheader(
                "Current Nomination Markets"
            )




            table_df = latest_df[
                [
                    "candidate",
                    "state",
                    "market_id",
                    "probability",
                    "volume"
                ]
            ].copy()

            # ============================================================
            # CHANGE VS LAST WEEK + TREND
            # ============================================================

            previous_date = latest_date - pd.Timedelta(days=7)

            previous_week_df = history_df[
                history_df["date"] == previous_date
            ].copy()

            previous_week_df = previous_week_df[
                previous_week_df["market_id"].isin(
                    table_df["market_id"]
                )
            ][
                ["market_id", "probability"]
            ].rename(
                columns={
                    "probability": "previous_probability"
                }
            )

            table_df = table_df.merge(
                previous_week_df,
                on="market_id",
                how="left"
            )

            table_df["change_vs_last_week"] = (
                table_df["probability"]
                - table_df["previous_probability"]
            )

            table_df["Trend"] = table_df[
                "change_vs_last_week"
            ].apply(
                lambda x:
                    "Up" if x > 0
                    else "Down" if x < 0
                    else "Unchanged"
            )

            table_df["Change vs last week"] = (
                table_df["change_vs_last_week"]
                .map(
                    lambda x:
                        f"{x:+.1f} pp"
                        if pd.notna(x)
                        else "N/A"
                )
            )

            table_df = table_df.sort_values(
                "probability",
                ascending=False
            )

            table_df = table_df.rename(
                columns={
                    "candidate": "Candidate",
                    "state": "State",
                    "probability": "Probability",
                    "volume": "Volume"
                }
            )

            table_df["Probability"] = (
                table_df["Probability"]
                .map(lambda x: f"{x:.1f}%")
            )

            table_df["Volume"] = (
                table_df["Volume"]
                .map(lambda x: f"{x:,.0f}")
            )

            table_df = table_df[
                [
                    "Candidate",
                    "State",
                    "Probability",
                    "Change vs last week",
                    "Trend",
                    "Volume"
                ]
            ]

            st.dataframe(
                table_df,
                width="stretch",
                hide_index=True
            )

        else:

            st.info(
                "No markets available."
            )

# ============================================================
# NOMINATION VIEW
# ============================================================

elif is_nomination:

    st.title(selected_subtype)
    st.subheader("Candidate Ranking")



    # Candidate trends
    trend_history = filter_markets(
        filtered_history_df,
        market_category="US Elections",
        election_type=selected_election_type,
        election_subtype=selected_subtype
    )





    trends = get_candidate_trends(
        trend_history,
        full_history=history_df
    )





    if not trends.empty:


        # ------------------------------------------------
        # Sort by latest probability
        # ------------------------------------------------

        ranking = (
            trends
            .sort_values(
                "latest_probability",
                ascending=False
            )
            .reset_index(drop=True)
            .copy()
        )

        # ------------------------------------------------
        # Add rank
        # ------------------------------------------------

        ranking["rank"] = ranking.index + 1


        # ------------------------------------------------
        # Current candidate probabilities
        # ------------------------------------------------

        chart_data = (
            trends[
                ["candidate", "latest_probability"]
            ]
            .sort_values(
                "latest_probability",
                ascending=False
            )
            .head(10)
            .copy()
        )

        st.subheader("Current Candidate Probabilities")

        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X(
                "latest_probability:Q",
                title="Probability (%)"
            ),
            y=alt.Y(
                "candidate:N",
                sort="-x",
                title=None
            ),
            tooltip=[
                alt.Tooltip(
                    "candidate:N",
                    title="Candidate"
                ),
                alt.Tooltip(
                    "latest_probability:Q",
                    title="Probability",
                    format=".1f"
                )
            ]
        ).properties(
            height=350
        )

        st.altair_chart(
            chart,
            width="stretch"
        )

        # ------------------------------------------------
        # Select and rename columns
        # ------------------------------------------------

        ranking = ranking[
            [
                "rank",
                "candidate",
                "entrance_date",
                "latest_date",
                "latest_probability",
                "probability_change",
                "weekly_probability_change",
                "trend",
                "latest_volume"
            ]
        ].rename(
            columns={
                "rank": "Rank",
                "candidate": "Candidate",
                "entrance_date": "Entrance Date",
                "latest_date": "Last Date",
                "latest_probability": "Probability",
                "probability_change": "Probability Change",
                "weekly_probability_change": "Weekly Change",
                "trend": "Trend",
                "latest_volume": "Volume"
            }
        )


        # ------------------------------------------------
        # Formatting
        # ------------------------------------------------

        ranking["Entrance Date"] = pd.to_datetime(
            ranking["Entrance Date"]
        ).dt.strftime("%d %b %Y")

        ranking["Last Date"] = pd.to_datetime(
            ranking["Last Date"]
        ).dt.strftime("%d %b %Y")


        ranking["Probability"] = ranking["Probability"].map(
            lambda x: (
                f"{x:.1f}%"
                if pd.notna(x)
                else "N/A"
            )
        )

        ranking["Probability Change"] = ranking["Probability Change"].map(
            lambda x: (
                f"{x:+.1f} pp"
                if pd.notna(x)
                else "N/A"
            )
        )

        ranking["Weekly Change"] = ranking["Weekly Change"].map(
            lambda x: (
                f"{x:+.1f} pp"
                if pd.notna(x)
                else "N/A"
            )
        )
        ranking["Volume"] = ranking["Volume"].map(
            lambda x: (
                f"{x / 1_000_000:.1f}M"
                if pd.notna(x)
                else "N/A"
            )
        )

        # ------------------------------------------------
        # Candidate ranking table
        # ------------------------------------------------

        st.dataframe(
            ranking,
            width="stretch",
            hide_index=True
        )

    else:
        st.info(
            "No candidate markets available."
        )




# ============================================================
# GENERAL ELECTION VIEW
# ============================================================

elif is_general_election:

    st.subheader("🇺🇸 General Election")

    candidate_history = filtered_df[
        filtered_df["candidate_type"] == "candidate"
    ].copy()




    trends = get_candidate_trends(
        candidate_history,
        full_history=history_df
    )



    if not trends.empty:

        # Sort by latest probability
        trends = trends.sort_values(
            "latest_probability",
            ascending=False
        ).copy()

       # ------------------------------------------------
       # Leader, volume share and probability concentration
       # ------------------------------------------------

        total_volume = trends["latest_volume"].sum()

        leader_volume_share = (
            trends.iloc[0]["latest_volume"]
            / total_volume * 100
           if total_volume > 0
            else 0
        )

        # Probability Concentration (HHI)
        #probability_shares = trends["latest_probability"]

        #probability_hhi = (
            #probability_shares ** 2
            #).sum()

        # ------------------------------------------------
        # KPIs
        # ------------------------------------------------

        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

        with kpi_col1:
            st.metric(
            "Leader",
            trends.iloc[0]["candidate"]
            )

        with kpi_col2:
            st.metric(
            "Probability",
            f"{trends.iloc[0]['latest_probability']:.1f}%"
            )

        with kpi_col3:
            st.metric(
            "Leader Volume Share",
            f"{leader_volume_share:.1f}%"
            )

        with kpi_col4:
            st.metric(
            "Total Volume",
            f"{total_volume / 1_000_000:.1f}M"
            )

        # ------------------------------------------------
        # Probability chart
        # ------------------------------------------------

        chart_data = trends[
            ["candidate", "latest_probability"]
            ].head(20).copy()

        chart_data = chart_data.rename(
            columns={
            "candidate": "Candidate",
            "latest_probability": "Probability"
             }
        )

        leader = trends.iloc[0]["candidate"]

        chart_data["Highlight"] = chart_data["Candidate"].apply(
            lambda x: "Leader" if x == leader else "Other"
        )

        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Probability:Q",
                    title="Probability (%)"
                ),
                y=alt.Y(
                    "Candidate:N",
                    sort="-x",
                    title=None
                ),
                color=alt.Color(
                    "Highlight:N",
                    scale=alt.Scale(
                        domain=["Leader", "Other"],
                        range=["#E45756", "#AFC6E9"]
                    ),
                    legend=None
                ),
                tooltip=[
                    alt.Tooltip(
                    "Candidate:N",
                    title="Candidate"
                ),
                    alt.Tooltip(
                        "Probability:Q",
                        title="Probability",
                        format=".1f"
                    )
                ]
            )
        )

        st.altair_chart(
            chart,
            width="stretch"
        )

        # ------------------------------------------------
        # Weekly probability movers
        # ------------------------------------------------

        movers = trends[
            [
               "candidate",
               "weekly_probability_change"
            ]
        ].dropna().copy()

        gainers = (
            movers[movers["weekly_probability_change"] > 0]
            .sort_values(
                "weekly_probability_change",
                 ascending=False
            )
           .head(10)
        )

        losers = (
            movers[movers["weekly_probability_change"] < 0]
            .sort_values(
                "weekly_probability_change",
                ascending=True
            )
           .head(10)
        )

        movers_chart_data = pd.concat(
            [gainers, losers]
        )

        movers_chart_data = movers_chart_data.rename(
            columns={
                "candidate": "Candidate",
                "weekly_probability_change": "Change"
            }
        )

        movers_chart = (
            alt.Chart(movers_chart_data)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Change:Q",
                    title="Probability change vs last week (pp)"
                ),
                y=alt.Y(
                    "Candidate:N",
                    sort="-x",
                    title=None
                ),
                color=alt.condition(
                    alt.datum.Change > 0,
                    alt.value("#4CAF50"),
                    alt.value("#E45756")
                ),
                tooltip=[
                    alt.Tooltip(
                        "Candidate:N",
                        title="Candidate"
                    ),
                    alt.Tooltip(
                        "Change:Q",
                        title="Change",
                        format="+.1f"
                    )
                ]
            )
        )

        st.subheader("Weekly Probability Movers")

        st.altair_chart(
             movers_chart,
            width="stretch"
        )

        # ------------------------------------------------
        # Candidate table
        # ------------------------------------------------

        ranking = trends[
            [
                "candidate",
                "latest_probability",
                "weekly_probability_change",
                "trend",
                "latest_volume"
            ]
        ].copy()

        ranking = ranking.rename(
            columns={
                "candidate": "Candidate",
                "latest_probability": "Probability",
                "weekly_probability_change": "Change vs last week",
                "trend": "Trend",
                "latest_volume": "Volume"
            }
        )

        ranking["Probability"] = ranking["Probability"].map(
            lambda x: f"{x:.1f}%"
        )

        ranking["Change vs last week"] = (
            ranking["Change vs last week"].map(
                lambda x: (
                    f"{x:+.1f} pp"
                    if pd.notna(x)
                    else "N/A"
                )
            )
        )

        ranking["Volume"] = ranking["Volume"].map(
            lambda x: f"{x / 1_000_000:.1f}M"
        )

        st.dataframe(
            ranking,
            width="stretch",
            hide_index=True
        )

    else:
        st.info(
            "No candidate markets available."
        )

# ============================================================
# GEOPOLITICAL VIEW
# ============================================================


elif is_geopolitical:

    st.subheader("Geopolitical Markets")

    # Latest observation for each market
    geopolitical_latest = (
        latest_df[
            latest_df["market_category"] == "Geopolitical"
        ][
            ["market_id", "market_name", "probability", "volume"]
        ]
        .drop_duplicates(subset=["market_id"])
        .copy()
    )

    # Calculate market trends
    geopolitical_trends = calculate_market_trends(
        filtered_df[
            filtered_df["market_category"] == "Geopolitical"
        ]
    )

    if not geopolitical_latest.empty:

        # Keep only the columns needed from the trends
        if not geopolitical_trends.empty:
            geopolitical_trends = geopolitical_trends[
                [
                    "market_id",
                    "probability_change",
                    "trend"
                ]
            ]

            geopolitical_table = geopolitical_latest.merge(
                geopolitical_trends,
                on="market_id",
                how="left"
            )
        else:
            geopolitical_table = geopolitical_latest.copy()
            geopolitical_table["probability_change"] = None
            geopolitical_table["trend"] = "Unavailable"

        # Format displayed values
        geopolitical_table["Probability"] = (
            geopolitical_table["probability"].map(
                lambda x: f"{x:.1f}%"
            )
        )

        geopolitical_table["Change vs Last Week"] = (
            geopolitical_table["probability_change"].map(
                lambda x: f"{x:+.1f} pp"
                if pd.notna(x) else "N/A"
            )
        )

        geopolitical_table["Volume"] = (
            geopolitical_table["volume"].map(format_volume)
        )

        geopolitical_table = geopolitical_table.rename(
            columns={"market_name": "Market Name"}
        )

        st.dataframe(
            geopolitical_table[
                [
                    "Market Name",
                    "Probability",
                    "Change vs Last Week",
                    "trend",
                    "Volume"
                ]
            ].rename(columns={"trend": "Trend"}),
            width="stretch",
            hide_index=True
        )

    else:
        st.info("No geopolitical markets available.")




# ============================================================
# DEBUG / DATA INFO
# ============================================================

##with st.expander("Data information"):

    ##st.write(
       ## f"Rows after filtering: {len(filtered_df):,}"
    ##)

    ##st.write(
       ## f"Unique markets: "
        ##f"{filtered_df['market_id'].nunique():,}"
    ##)

    ##st.write(
        ##f"Latest date: {latest_date}"
    ##)