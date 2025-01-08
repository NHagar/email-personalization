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
if "survey_completed" not in st.session_state:
    st.session_state.survey_completed = False


def on_submit():
    st.session_state.part1_completed = True
    st.rerun()


pages = survey.pages(4, on_submit=on_submit, progress_bar=True)

if not st.session_state.survey_completed:
    if not st.session_state.part1_completed:
        with pages:
            if pages.current == 0:
                headlines_subset = headlines[:headlines_per_page]
                render_headlines(survey, headlines_subset, st.session_state.selections)
            elif pages.current == 1:
                headlines_subset = headlines[
                    headlines_per_page : 2 * headlines_per_page
                ]
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
            shuffled_pairs = []
            st.write("### Please wait for part 2 of the survey to load...")
            progress_text = "Setting up part 2..."
            progress_bar = st.progress(0.0, "Setting up part 2...")

            hg = HeadlineGenerator(
                [k for k, v in st.session_state.selections.items() if v]
            )
            for i, p in enumerate(newsletter_paths[:5]):
                hg.load_newsletter(p)
                original = hg.original_heading
                generated = hg.generate_heading()
                pair = (
                    {"text": original, "source": "Original"},
                    {"text": generated, "source": "Generated"},
                )
                options = list(pair)
                random.shuffle(options)
                shuffled_pairs.append(options)
                pairs.append(pair)
                progress_bar.progress(
                    (i + 1) / len(newsletter_paths[:5]), "Setting up part 2..."
                )
            st.session_state.generated_headlines = pairs
            st.session_state.shuffled_headlines = shuffled_pairs
            st.session_state.user_annotations = hg.user_annotations
            st.rerun()
        else:
            pairs = st.session_state.generated_headlines
            shuffled_pairs = st.session_state.shuffled_headlines

        st.write(
            "### Below are headlines from the New York Times Evening Briefing newsletter, published in August 2024. For each pair, select the headline that you would be more likely to click on and read. Consider both the main headline and the additional context below it."
        )

        for index, options in enumerate(shuffled_pairs):
            text_to_source = {opt["text"]: opt["source"] for opt in options}
            option_texts = [opt["text"] for opt in options]

            cols = st.columns(2)
            for i, opt in enumerate(options):
                with cols[i]:
                    st.markdown(f"**Option {i+1}**")
                    st.markdown(opt["text"])

            radio_key = f"radio_{index}"

            selected = st.radio(
                "Your choice:",
                option_texts,
                key=radio_key,
                format_func=lambda x: f"Option {option_texts.index(x) + 1}",
                label_visibility="collapsed",
            )

            st.session_state.headline_preferences[radio_key] = {
                "selected": selected,
                "options": text_to_source,
            }

            st.write("---")

        if st.button("Submit"):
            user_history = [k for k, v in st.session_state.selections.items() if v]
            user_preferences = st.session_state.headline_preferences
