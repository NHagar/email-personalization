from pathlib import Path

import duckdb
import openai
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

with open("src/prompts/infer_interests.txt", "r") as f:
    prompt_history = f.read()

with open("src/prompts/item_ranking.txt", "r") as f:
    prompt_ranking = f.read()

with open("src/prompts/framing.txt", "r") as f:
    prompt_framing = f.read()


llm = openai.OpenAI()

con = duckdb.connect(database=':memory:')

history = st.radio("Reading history", ["Full", "Filtered"])
newsletter = st.radio("Newsletter", sorted(list(Path('./data/emails').rglob('*.csv'))))

if history == "Full":
    with open("data/reading_history.txt", "r") as f:
        history = f.read()
else:
    with open("data/reading_history_filtered.txt", "r") as f:
        history = f.read()

newsletter_items = con.execute(f"SELECT *, 'HEADLINE: ' || headline || '\nDESCRIPTION: ' || description AS formatted FROM '{newsletter}' WHERE headline != 'SKIP'").fetch_df()
original_heading = con.execute(f"SELECT '# ' || newsletter_headline || '\n\n' || '## ' || newsletter_sub_hed AS heading FROM '{newsletter}' ").fetch_df().iloc[0, 0]

with st.expander("See reading history"):
    st.code(history)

st.dataframe(newsletter_items)

st.markdown(f"# Original heading:")
st.markdown(original_heading.replace("\\n", "\n\n"))


personalization_input_format = f"""USER READING HISTORY: {history}"""

generate_history = st.button("Generate history annotation")

if generate_history:
    personalization_resp = llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": prompt_history
            },
            {
                "role": "user",
                "content": personalization_input_format
            }
        ],
        stream=True
    )

    with st.container(border=True):
        history_annotation = st.write_stream(personalization_resp)

        with open("./data/history_annotation.txt", "w") as f:
            f.write(history_annotation)


generate_reasoning = st.button("Generate newsletter item reasoning")

if generate_reasoning:
    with open("./data/history_annotation.txt", "r") as f:
        user_notes = f.read()

    formatted_input = f"""USER NOTES: {user_notes}\n\nCANDIDATE ITEMS: {'\n'.join(newsletter_items.formatted.tolist())}"""

    ranking_resp = llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": prompt_ranking
            },
            {
                "role": "user",
                "content": formatted_input
            }
        ],
        stream=True,
        stop="3."
    )

    notes = st.write_stream(ranking_resp)

    formatted_input = f"""USER NOTES: {user_notes}\n\nSTORIES: {notes}"""

    framing_resp = llm.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": prompt_framing
            },
            {
                "role": "user",
                "content": formatted_input
            }
        ],
        stream=True
    )

    st.write_stream(framing_resp)
