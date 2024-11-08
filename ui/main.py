import random
from pathlib import Path

import duckdb
import openai
import pandas as pd
import streamlit as st

from personalization_eval import get_persona_preference

from dotenv import load_dotenv

load_dotenv()


llm = openai.OpenAI()

con = duckdb.connect(database=':memory:')

with open("src/prompts/personalization.txt", "r") as f:
    prompt_personalization = f.read()

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
        personalized = st.write_stream(personalization_resp)

        generated_headline = personalized.split("==!BEGIN OUTPUT!==\n")[-1].replace("\n==!END OUTPUT!==", "")

        # get list of personas
        personas = sorted(list(Path('./src/prompts/personas').rglob('*.txt')))
        # extract just the name of the persona
        personas = [p.stem for p in personas]

        test = personas[0]

        choices = [original_heading, generated_headline]
        # randomize choices
        random.shuffle(choices)

        pref = get_persona_preference(test, choices[0], choices[1])

        df = pd.DataFrame({"persona": [test], "choice_1": [choices[0]], "choice_2": [choices[1]], "preference": [pref]})

        st.dataframe(df)
