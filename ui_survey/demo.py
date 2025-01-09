import random

import duckdb
import streamlit as st
import streamlit_survey as ss
from headline_generation import HeadlineGenerator, newsletter_paths

con = duckdb.connect("database.db")

query = "SELECT * FROM './data/nyt_sampled.parquet';"


@st.cache_data
def fetch_headlines():
    data = con.execute(query).fetchdf().headline.tolist()
    random.shuffle(data)

    return data


def render_headlines(survey, headlines, selections):
    st.write(
        "## Please select the New York Times headlines, published between May and July 2024, that you would be interested in reading.\nYou can select as many or as few as are of interest to you."
    )
    for i, item in enumerate(headlines):
        if survey.checkbox(item, key=i, value=selections.get(item, False)):
            selections[item] = True
        else:
            selections[item] = False


headlines = fetch_headlines()

headlines_per_page = len(headlines) // 4

survey = ss.StreamlitSurvey()

if "selections" not in st.session_state:
    st.session_state.selections = {}
if "part1_completed" not in st.session_state:
    st.session_state.part1_completed = False
if "generated_headlines" not in st.session_state:
    st.session_state.generated_headlines = None
if "headline_preferences" not in st.session_state:
    st.session_state.headline_preferences = {}


def on_submit():
    st.session_state.part1_completed = True
    st.rerun()


pages = survey.pages(4, on_submit=on_submit, progress_bar=True)

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
        st.write("### Please wait for part 2 of the survey to load...")
        progress_text = "Setting up part 2..."
        progress_bar = st.progress(0.0, "Setting up part 2...")

        hg = HeadlineGenerator([k for k, v in st.session_state.selections.items() if v])
        for i, p in enumerate(newsletter_paths[:5]):
            hg.load_newsletter(p)
            original = hg.original_heading
            generated = hg.generate_heading()
            pair = (
                {"text": original, "source": "Original"},
                {"text": generated, "source": "Generated"},
            )
            pairs.append(pair)
            progress_bar.progress(
                (i + 1) / len(newsletter_paths[:5]), "Setting up part 2..."
            )
        st.session_state.generated_headlines = pairs
        st.session_state.user_annotations = hg.user_annotations
        st.rerun()
    else:
        pairs = st.session_state.generated_headlines

    st.write(
        "### Below are headlines from the New York Times Evening Briefing newsletter, published in August 2024. For each pair, select the headline that you would be more likely to click on and read. Consider both the main headline and the additional context below it."
    )

    for index, options in enumerate(pairs):
        cols = st.columns([4, 1, 4])  # 3 columns with ratio 4:1:4
        with cols[0]:
            st.caption(":blue[Original]")
            st.markdown(options[0]["text"])
        with cols[1]:
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            st.markdown("### →")  # Arrow centered vertically
        with cols[2]:
            st.caption(":red[LLM generated]")
            st.markdown(options[1]["text"])

        st.write("---")
