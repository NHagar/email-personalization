import duckdb
import streamlit as st
from headline_generation import HeadlineGenerator, newsletter_paths

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

generator = HeadlineGenerator(headlines_selected)
generator.model = "gpt-4o-mini"

prompt_summary = st.text_area(
    "User interest summary prompt", value=generator.prompt_history, height=250
)

prompt_ranking = st.text_area(
    "Headline ranking prompt",
    value=generator.prompt_ranking,
    height=250,
)

prompt_headline_writing = st.text_area(
    "Headline writing prompt",
    value=generator.prompt_framing,
    height=250,
)

newsletter_selected = st.selectbox(
    "Select newsletter edition",
    newsletter_paths,
)

generator.load_newsletter(newsletter_selected)

st.write("Newsletter items:")
st.write(generator.newsletter_items)

steps = st.pills(
    "Select the steps to run",
    ["Infer interests", "Rank items", "Write headlines"],
    selection_mode="multi",
)

if st.button("Generate outputs"):
    if "Infer interests" in steps:
        generator.prompt_history = prompt_summary

        generator.infer_interests()
        st.write("User interests inferred:")
        st.write(generator.user_annotations)
    if "Rank items" in steps:
        generator.prompt_ranking = prompt_ranking

        ranked_items = generator.rank_items()
        st.write("Items ranked:")
        st.write(ranked_items)
    if "Write headlines" in steps:
        generator.prompt_framing = prompt_headline_writing

        generated_heading = generator.generate_heading()
        st.write("Headlines written:")
        st.write(generated_heading)
