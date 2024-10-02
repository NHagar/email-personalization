import random

import duckdb
import streamlit as st
import streamlit_survey as ss

con = duckdb.connect(":memory:")


@st.cache_data
def fetch_headlines(curr, nex, sample_size=100):
    data = (
        con.execute(
            f"WITH raw AS (SELECT headline FROM './data/nyt_archive_all.parquet' WHERE pub_date >= '{curr}' AND pub_date < '{nex}') SELECT * FROM raw USING SAMPLE {sample_size} "
        )
        .fetchdf()
        .headline.tolist()
    )
    data = random.sample(data, min(100, len(data)))

    return data


def render_headlines(survey, headlines, selections):
    for i, item in enumerate(headlines):
        if survey.checkbox(item, key=i, value=selections.get(item, False)):
            selections[item] = True
        else:
            selections[item] = False


headlines = fetch_headlines("2024-07-01", "2024-08-01")

headlines_per_page = len(headlines) // 4

survey = ss.StreamlitSurvey()

if "selections" not in st.session_state:
    st.session_state.selections = {}

pages = survey.pages(
    4, on_submit=lambda: st.success("Your responses have been recorded. Thank you!")
)

with pages:
    if pages.current == 0:
        headlines_subset = headlines[:headlines_per_page]
        render_headlines(survey, headlines_subset, st.session_state.selections)
    elif pages.current == 1:
        headlines_subset = headlines[headlines_per_page : 2 * headlines_per_page]
        render_headlines(survey, headlines_subset, st.session_state.selections)
    elif pages.current == 2:
        headlines_subset = headlines[2 * headlines_per_page : 3 * headlines_per_page]
        render_headlines(survey, headlines_subset, st.session_state.selections)
    elif pages.current == 3:
        headlines_subset = headlines[3 * headlines_per_page :]
        render_headlines(survey, headlines_subset, st.session_state.selections)


st.write("Selected items:")
st.write([k for k, v in st.session_state.selections.items() if v])
