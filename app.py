import streamlit as st
import pandas as pd

st.title("Polymarket — Measuring Collective Expectations")

st.write("An interactive dashboard exploring prediction-market expectations.")

data = {
    "date": [
        "2026-08-01",
        "2026-08-02",
        "2026-08-03",
        "2026-08-04",
        "2026-08-05",
        "2026-08-06",
        "2026-08-07"
    ],
    "probability": [
        54,
        56,
        59,
        57,
        63,
        68,
        72
    ],
    "volume": [
        120000,
        145000,
        210000,
        280000,
        350000,
        420000,
        480000
    ]
}

df = pd.DataFrame(data)