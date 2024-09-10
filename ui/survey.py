from pathlib import Path
import random

import duckdb
from openai import OpenAI
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

llm = OpenAI()

with open("src/prompts/infer_interests.txt", "r") as f:
    prompt_history = f.read()

with open("src/prompts/item_ranking.txt", "r") as f:
    prompt_ranking = f.read()

with open("src/prompts/framing.txt", "r") as f:
    prompt_framing = f.read()



con = duckdb.connect(":memory:")

@st.cache_data
def fetch_headlines(curr, nex):
    data = con.execute(f"SELECT headline FROM './data/nyt_archive_all.parquet' WHERE pub_date >= '{curr}' AND pub_date < '{nex}' ").fetchdf().headline.tolist()
    data = random.sample(data, min(100, len(data)))

    return data


headlines = fetch_headlines("2024-07-01", "2024-07-06")

selected_items = {}

for i, item in enumerate(headlines):
    selected_items[item] = st.checkbox(item, key=i)

st.write("Selected items:")
for item, selected in selected_items.items():
    if selected:
        st.write(item)


newsletter = st.radio("Newsletter", sorted(list(Path('./data/emails').rglob('*.csv'))))

history = [item for item, selected in selected_items.items() if selected]
newsletter_items = con.execute(f"SELECT *, 'HEADLINE: ' || headline || '\nDESCRIPTION: ' || description AS formatted FROM '{newsletter}' WHERE headline != 'SKIP'").fetch_df()
original_heading = con.execute(f"SELECT '# ' || newsletter_headline || '\n\n' || '## ' || newsletter_sub_hed AS heading FROM '{newsletter}' ").fetch_df().iloc[0, 0]


personalization_input_format = f"""USER READING HISTORY: {history}"""

generate_personalization = st.button("Done")

if generate_personalization:
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
        ]
    )

    user_notes = personalization_resp.choices[0].message.content
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
        stop="3."
    )

    formatted_input = f"""USER NOTES: {user_notes}\n\nSTORIES: {ranking_resp.choices[0].message.content}"""

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
        ]
    )

    generated_heading = framing_resp.choices[0].message.content


    st.radio("Which headline do you prefer?", [original_heading, generated_heading])
