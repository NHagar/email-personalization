from pathlib import Path

import duckdb
import streamlit as st

con = duckdb.connect(database=':memory:')

history = st.radio("Reading history", ["Full", "Filtered"])

newsletter = st.radio("Newsletter", sorted(list(Path('./data').rglob('*.csv'))))

if history == "Full":
    with open("data/reading_history.txt", "r") as f:
        history = f.read()
else:
    with open("data/reading_history_filtered.txt", "r") as f:
        history = f.read()

newsletter_items = con.execute(f"SELECT * FROM '{newsletter}' WHERE headline != 'SKIP'").fetch_df()


with st.expander("See reading history"):
    st.code(history)

st.dataframe(newsletter_items)

