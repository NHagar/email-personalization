import random

import duckdb
import streamlit as st
import streamlit_survey as ss
from headline_generation import HeadlineGenerator, newsletter_paths

con = duckdb.connect("database.db")

with open("consent_form.md", "r") as f:
    consent_screen = f.read()


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
if "headline_preferences" not in st.session_state:
    st.session_state.headline_preferences = {}
if "consent_given" not in st.session_state:
    st.session_state.consent_given = False
if "survey_completed" not in st.session_state:
    st.session_state.survey_completed = False


def on_submit():
    st.session_state.part1_completed = True
    st.rerun()


if not st.session_state.consent_given:
    st.title("Consent to Participate in Research")
    st.markdown(consent_screen)
    signature = st.text_input("Electronic Signature:")
    date = st.date_input("Today's Date:")
    if st.button("I Agree"):
        if signature and date:
            st.session_state.consent_given = True
            st.rerun()
        else:
            st.error("Please provide both signature and date to proceed.")
    st.stop()


pages = survey.pages(4, on_submit=on_submit)

if st.session_state.consent_given and not st.session_state.survey_completed:
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
            progress_text = "Setting up part 2..."
            progress_bar = st.progress(0.0, "Setting up part 2...")

            hg = HeadlineGenerator(
                [k for k, v in st.session_state.selections.items() if v]
            )
            for i, p in enumerate(newsletter_paths[:5]):
                hg.load_newsletter(p)
                original = hg.original_heading
                generated = hg.generate_heading()
                pairs.append(
                    (
                        {"text": original, "source": "Original"},
                        {"text": generated, "source": "Generated"},
                    )
                )
                progress_bar.progress(
                    (i + 1) / len(newsletter_paths[:5]), "Setting up part 2..."
                )
            st.session_state.generated_headlines = pairs

        else:
            pairs = st.session_state.generated_headlines

        for index, pair in enumerate(pairs):
            options = [
                (pair[0]["text"], pair[0]["source"]),
                (pair[1]["text"], pair[1]["source"]),
            ]

            random.shuffle(options)

            text_to_source = {text: source for text, source in options}
            option_texts = [text for text, _ in options]

            st.write("Select the better headline:")

            cols = st.columns(2)
            for i, (text, source) in enumerate(options):
                with cols[i]:
                    st.markdown(f"**Option {i+1}**")
                    st.markdown(text)

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

            # Save to database
            con.execute(
                "CREATE TABLE IF NOT EXISTS survey_results (user_id STRING, user_history ARRAY, user_preferences ARRAY)"
            )
            con.execute(
                f"INSERT INTO survey_results VALUES ('{st.query_params["user_id"]}', '{user_history}', '{user_preferences}')"
            )

            st.session_state.survey_completed = True
            st.rerun()

if st.session_state.survey_completed:
    st.title("Debrief")
    st.write("""
    Thank you for participating in our study on headline preferences.

    The purpose of this study was to compare user preferences between AI-generated and human-written headlines.

    In Part 2 of this survey, you were asked to select between two headlines: One written by a human for the New York Times Evening Briefing newsletter, and one written by GPT-4o. The LLM-generated headline was personalized, based on the headlines you selected in Part 1.

    Your responses will help us understand how AI-generated content compares to human-written content in terms of user engagement and preference.

    If you have questions, concerns, or complaints, you can contact the Principal Investigator Nicholas Diakopoulos (nad@northwestern.edu), and co-investigators Nick Hagar (nicholas.hagar@northwestern.edu) and Jeremy Gilbert (jeremy.gilbert@northwestern.edu)..

    Thank you again for your participation!
    """)
    if st.button("Finish"):
        st.balloons()
        st.stop()
