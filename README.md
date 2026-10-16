# Polymarket — Measuring Collective Expectations

An interactive data analytics dashboard for exploring election prediction markets, tracking implied probabilities, and monitoring how collective expectations evolve over time.

## Overview

This project uses data from the Polymarket prediction-market platform to explore expectations surrounding elections and geopolitical events. It combines API data collection, historical data analysis, and interactive visualizations in a Streamlit application.

The goal is to make prediction-market information easier to explore, compare, and interpret by turning market data into meaningful indicators and time-based insights.

## Key Features

- **Election market analysis:** Explore US presidential elections, US midterm elections, global elections, and geopolitical events.
- **Implied probabilities:** Examine market-implied probabilities for candidates and potential outcomes.
- **Historical trends:** Track changes in market probabilities over time.
- **Market activity:** Explore trading volume and other available market indicators.
- **Interactive filters:** Navigate markets by election category, subtype, candidate, US state, and date where applicable.
- **Automated data collection:** Retrieve market data through the Polymarket API and maintain historical observations for analysis.
- **Data visualizations:** Compare candidates, inspect market leaders, and explore changes in collective expectations through tables, charts, and summary indicators.

## Technology Stack

- **Python** — data processing and analysis
- **Pandas** — data manipulation and historical data preparation
- **Streamlit** — interactive dashboard and user interface
- **OpenAI API** — AI-powered explanations and summaries, where configured
- **Polymarket API** — prediction-market data source
- **Git and GitHub** — version control and project management

## How It Works

1. **Data collection:** Retrieve election-related market information from the Polymarket API.
2. **Data preparation:** Organize market information, probabilities, trading volumes, and market categories.
3. **Historical tracking:** Store observations over time to support trend analysis.
4. **Analysis:** Compare current market probabilities with historical observations and identify leading candidates or outcomes.
5. **Visualization:** Present the results through an interactive dashboard with filters, charts, and summary tables.

## Getting Started

### Prerequisites

- Python 3.10 or a compatible version supported by the project's dependencies
- Git
- Access to the Polymarket API
- The Python packages listed in `requirements.txt`, once the dependency file is finalized

### Run the Dashboard

Clone the repository:

```bash
git clone https://github.com/RoulaNtinou/Polymarket-Measuring-Collective-Expectations.git
cd Polymarket-Measuring-Collective-Expectations
```

Create and activate a virtual environment if desired, then install the dependencies:

```bash
pip install -r requirements.txt
```

Start the Streamlit application:

```bash
streamlit run app.py
```

The application should open in your browser. If it does not, use the local URL displayed in the terminal.

**Note:** The instructions above assume that `requirements.txt` exists and that the repository includes the necessary application files and historical data. We will verify these before considering the setup instructions final.

## Project Structure

- `app.py` — Streamlit dashboard and interactive views
- `polymarket_elections.py` — election-market data processing and analytical functions
- `election_market_history.csv` — historical market observations
- `update_election_history.py` — script for retrieving and updating election-market history
- `requirements.txt` — Python dependencies

## Analytical Considerations

Prediction-market probabilities represent market-implied expectations, not guaranteed outcomes or objective measures of the probability of an event. They may change as new information becomes available and can be influenced by liquidity, trading activity, market structure, and participant behavior.

Historical changes should therefore be interpreted in the context of the relevant market and its available data.

## Future Improvements

Potential areas for further development include:

- Expanding historical trend comparisons and date-based analysis
- Improving cross-election and cross-market comparisons
- Adding additional data-quality checks and monitoring
- Enhancing dashboard usability and documentation
- Exploring relationships between market-implied probabilities and real-world events

## Author

**Roula Ntinou**

Data analytics and data science portfolio project.

GitHub: [RoulaNtinou](https://github.com/RoulaNtinou)

---

*This project is intended for educational and analytical purposes. It is not financial, investment, or electoral advice.*