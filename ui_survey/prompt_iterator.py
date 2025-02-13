import duckdb
import streamlit as st

con = duckdb.connect("database.db")

query = "SELECT * FROM './data/nyt_sampled.parquet';"


@st.cache_data
def fetch_headlines():
    data = con.execute(query).fetchdf().headline.tolist()

    return data


headlines = fetch_headlines()

headlines_selected = st.multiselect(
    "Select headlines for reading history",
    headlines,
)
