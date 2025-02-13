import random

import duckdb
import streamlit as st
import streamlit_survey as ss
from headline_generation import HeadlineGenerator, newsletter_paths

# Add explainer box at the start
st.info("""
### Personalized Newsletter Headlines: An AI Demo
This demo shows how AI can tailor newsletter headlines to individual readers, using the New York Times Evening Briefing as a case study. Here's how it works: First, you select which New York Times stories you'd like to read, creating a simulated reading history. GPT-4o then analyzes your preferences, identifies relevant stories from each newsletter, and generates a personalized headline that highlights the content you're most likely to care about. In user testing with actual New York Times readers, 62% preferred these AI-generated headlines to the original ones.

Want to learn more? Check out our blog post for the full research findings.
""")

con = duckdb.connect("database.db")

query = "SELECT * FROM './data/nyt_sampled.parquet';"


@st.cache_data
def fetch_headlines():
    data = con.execute(query).fetchdf().headline.tolist()
    random.shuffle(data)

    return data


def render_headlines(survey, headlines, selections):
    st.write(
        "#### Please select the New York Times headlines, published between May and July 2024, that you would be interested in reading."
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
        progress_text = "Generating headlines..."
        progress_bar = st.progress(0.0, progress_text)

        hg = HeadlineGenerator([k for k, v in st.session_state.selections.items() if v])
        hg.infer_interests()
        for i, p in enumerate(newsletter_paths[:5]):
            hg.load_newsletter(p)
            original = hg.original_heading
            generated = hg.generate_heading()
            pair = (
                {"text": original, "source": "Original"},
                {"text": generated, "source": "Generated"},
            )
            pairs.append(pair)
            progress_bar.progress((i + 1) / len(newsletter_paths[:5]), progress_text)
        st.session_state.generated_headlines = pairs
        st.session_state.user_annotations = hg.user_annotations
        st.rerun()
    else:
        pairs = st.session_state.generated_headlines

    st.write(
        "#### Now, compare how the Evening Briefing headlines could be personalized based on your interests.\n\n"
        "For each story below, you'll see:\n"
        "- The original Evening Briefing headline on the left\n"
        "- An AI-generated version on the right, tailored to highlight aspects that match your reading preferences\n\n"
    )

    # Add dropdown for user annotations
    if st.session_state.user_annotations:
        with st.expander("View LLM analysis of your selected stories"):
            st.markdown(st.session_state.user_annotations)

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
