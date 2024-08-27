from pathlib import Path

import duckdb
import openai
import streamlit as st

from dotenv import load_dotenv

load_dotenv()


llm = openai.OpenAI()

con = duckdb.connect(database=':memory:')

with open("src/prompts/personalization.txt", "r") as f:
    prompt_personalization = f.read()

history = st.radio("Reading history", ["Full", "Filtered"])

newsletter = st.radio("Newsletter", sorted(list(Path('./data').rglob('nyt*.csv'))))

if history == "Full":
    with open("data/reading_history.txt", "r") as f:
        history = f.read()
else:
    with open("data/reading_history_filtered.txt", "r") as f:
        history = f.read()

newsletter_items = con.execute(f"SELECT *, 'HEADLINE: ' || headline || '\nDESCRIPTION: ' || description AS formatted FROM '{newsletter}' WHERE headline != 'SKIP'").fetch_df()

original_heading = con.execute(f"SELECT heading FROM 'data/emails/original_headings.csv' WHERE fpath = '{newsletter}';").fetch_df().iloc[0, 0]

with st.expander("See reading history"):
    st.code(history)

st.dataframe(newsletter_items)

st.markdown(f"# Original heading:")
st.markdown(original_heading.replace("\\n", "\n\n"))

personalization_input_format = f"""USER READING HISTORY: {history}

NEWSLETTER ITEMS: {'\n'.join(newsletter_items.formatted.tolist())}
"""

generate = st.button("Generate Personalization")

if generate:
    personalization_resp = llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": prompt_personalization
            },
            {
                "role": "user",
                "content": personalization_input_format
            }
        ],
        stream=True
    )

    with st.container(border=True):
        st.write_stream(personalization_resp)