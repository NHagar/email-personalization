from pathlib import Path

import streamlit as st

history = st.radio("Reading history", ["Full", "Filtered"])

newsletter = st.radio("Newsletter", sorted(list(Path('./data').rglob('*.md'))))

if history == "Full":
    with open("data/reading_history.txt", "r") as f:
        history = f.read()
else:
    with open("data/reading_history_filtered.txt", "r") as f:
        history = f.read()

