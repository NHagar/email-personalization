# generation flow
# option ordering
# option rendering
# data persistence
# url params

import random

import duckdb
import streamlit as st
import streamlit_survey as ss
from headline_generation import generate_heading, get_original_heading, newsletter_paths

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
if "part1_completed" not in st.session_state:
    st.session_state.part1_completed = False
if "generated_headlines" not in st.session_state:
    st.session_state.generated_headlines = None


def on_submit():
    st.session_state.part1_completed = True
    st.rerun()


pages = survey.pages(4, on_submit=on_submit)

if not st.session_state.part1_completed:
    with pages:
        if pages.current == 0:
            headlines_subset = headlines[:headlines_per_page]
            render_headlines(survey, headlines_subset, st.session_state.selections)
        elif pages.current == 1:
            headlines_subset = headlines[headlines_per_page : 2 * headlines_per_page]
            render_headlines(survey, headlines_subset, st.session_state.selections)
        elif pages.current == 2:
            headlines_subset = headlines[
                2 * headlines_per_page : 3 * headlines_per_page
            ]
            render_headlines(survey, headlines_subset, st.session_state.selections)
        elif pages.current == 3:
            headlines_subset = headlines[3 * headlines_per_page :]
            render_headlines(survey, headlines_subset, st.session_state.selections)
else:
    if st.session_state.generated_headlines is None:
        pairs = []
        progress_text = "Setting up part 2..."
        progress_bar = st.progress(0.0, "Setting up part 2...")
        for i, p in enumerate(newsletter_paths):
            original = get_original_heading(p)
            generated = generate_heading(
                p, [k for k, v in st.session_state.selections.items() if v]
            )
            pairs.append(
                (
                    {"text": original, "source": "Original"},
                    {"text": generated, "source": "Generated"},
                )
            )
            progress_bar.progress(
                (i + 1) / len(newsletter_paths), "Setting up part 2..."
            )
        st.session_state.generated_headlines = pairs

    else:
        pairs = st.session_state.generated_headlines

    for pair in pairs:
        option = st.radio(
            "Select the better headline:",
            [pair[0]["text"], pair[1]["text"]],
            format_func=lambda x: x,
        )
        st.write("---")
