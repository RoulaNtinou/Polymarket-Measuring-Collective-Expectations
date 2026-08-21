import streamlit as st
import pandas as pd
from openai import OpenAI



client = OpenAI()



st.title("Polymarket — Measuring Collective Expectations")

st.write("An interactive dashboard exploring prediction-market expectations.")

data = {
    "market": [
        "AI regulation",
        "AI regulation",
        "AI regulation",
        "AI regulation",
        "AI regulation",
        "AI regulation",
        "AI regulation",
        "Interest rates",
        "Interest rates",
        "Interest rates",
        "Interest rates",
        "Interest rates",
        "Interest rates",
        "Interest rates",
        "Global temperature",
        "Global temperature",
        "Global temperature",
        "Global temperature",
        "Global temperature",
        "Global temperature",
        "Global temperature"
    ],
    
    "date": [
        "2026-08-01",
        "2026-08-02",
        "2026-08-03",
        "2026-08-04",
        "2026-08-05",
        "2026-08-06",
        "2026-08-07",
        
        "2026-08-01",
        "2026-08-02",
        "2026-08-03",
        "2026-08-04",
        "2026-08-05",
        "2026-08-06",
        "2026-08-07",
        
        "2026-08-01",
        "2026-08-02",
        "2026-08-03",
        "2026-08-04",
        "2026-08-05",
        "2026-08-06",
        "2026-08-07"
    ],
    
    "probability": [
        54, 56, 59, 57, 63, 68, 72,
        42, 43, 45, 44, 48, 51, 55,
        31, 32, 30, 34, 37, 36, 40
    ],
    
    "volume": [
        120000, 145000, 210000, 280000, 350000, 420000, 480000,
        90000, 110000, 130000, 150000, 190000, 230000, 260000,
        75000, 85000, 95000, 125000, 160000, 190000, 220000
    ]
}




df = pd.DataFrame(data)


df["date"] = pd.to_datetime(df["date"]).dt.date
df["display_date"] = pd.to_datetime(df["date"]).dt.strftime("%b %d")

st.subheader("Market data")

st.dataframe(df)

market = st.sidebar.selectbox(
    "Select market",
    df["market"].unique()
)

st.sidebar.subheader("Filters")

date_range = st.sidebar.date_input(
    "Select date range",
    value=(df["date"].min(), df["date"].max()),
    key="date_range"
)

if len(date_range) == 2:
    start_date, end_date = date_range

    filtered_df = df[
        (df["market"] == market) &
        (df["date"] >= start_date) &
        (df["date"] <= end_date)
    ]
else:
    filtered_df = df[df["market"] == market]

current_probability = filtered_df["probability"].iloc[-1]

total_volume = filtered_df["volume"].iloc[-1]

probability_change = (
    filtered_df["probability"].iloc[-1]
    - filtered_df["probability"].iloc[0]
)

summary = {
    "market": market,
    "start_date": str(filtered_df["date"].iloc[0]),
    "end_date": str(filtered_df["date"].iloc[-1]),
    "starting_probability": filtered_df["probability"].iloc[0],
    "ending_probability": current_probability,
    "probability_change": probability_change,
    "starting_volume": filtered_df["volume"].iloc[0],
    "ending_volume": total_volume,
    "observations": len(filtered_df)
}

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Market Probability", f"{current_probability}%")

with col2:
    st.metric("Current Trading Volume", f"${total_volume:,.0f}")

with col3:
    st.metric("Probability Change", f"{probability_change:+} pp")

    

    

st.subheader("Probability over time")

st.line_chart(
    filtered_df,
    x="display_date",
    y="probability"
)

st.subheader("Trading volume over time")

st.line_chart(
    filtered_df,
    x="display_date",
    y="volume"
)


if st.button("Explain this view"):

    prompt = f"""
    You are a data analyst providing a short executive briefing.

    Analyze the following prediction-market data:

    Market: {summary["market"]}
    Period: {summary["start_date"]} to {summary["end_date"]}

    Starting probability: {summary["starting_probability"]}%
    Ending probability: {summary["ending_probability"]}%
    Probability change: {summary["probability_change"]} percentage points

    Starting trading volume: ${summary["starting_volume"]:,.0f}
    Ending trading volume: ${summary["ending_volume"]:,.0f}

    Number of observations: {summary["observations"]}

    Write a concise executive briefing in plain English.
    Mention the main change in market expectations and trading activity.
    Do not claim causation.
    Keep it to 3–5 sentences.
    """

    try:
        with st.spinner("Generating executive briefing..."):

            response = client.responses.create(
                model="gpt-5-mini",
                input=prompt
            )

            st.subheader("Executive briefing")
            st.write(response.output_text)

    except Exception as e:
        st.error("The AI briefing could not be generated. Please try again.")

