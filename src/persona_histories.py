import datetime
import os

import duckdb
from openai import OpenAI

from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

llm = OpenAI()
with open("./src/prompts/persona_history.txt", "r") as f:
    prompt_history = f.read()

con = duckdb.connect(":memory:")

def process_all_dates(persona_name):
    with open(f"./src/prompts/personas/{persona_name}.txt", "r") as f:
        persona = f.read()

    start_date = datetime.date(2024, 7, 1)
    end_date = datetime.date(2024, 7, 31)
    date_list = [(start_date + datetime.timedelta(days=x)).strftime('%Y-%m-%d') for x in range((end_date - start_date).days + 1)]

    # check if persona memory file exists
    memory_path = f"./data/memories/{persona_name}.txt"
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory = f"STORIES READ:\n{f.read()}"
    else:
        # set blank memory and create file
        memory = ""
        with open(memory_path, "w") as f:
            f.write(memory)


    for i in tqdm(range(len(date_list))):
        curr = date_list[i]
        nex = date_list[i+1] if i+1 < len(date_list) else "2024-08-01"
        headlines = "\n".join(con.execute(f"SELECT headline FROM './data/nyt_archive_all.parquet' WHERE pub_date >= '{curr}' AND pub_date < '{nex}' ").fetchdf().headline.tolist())

        user_input = f"PERSONA:\n{persona}\n{memory}\nHEADLINES:\n{headlines}"

        with open("test.txt", "w") as f:
            f.write(user_input)

        resp = llm.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_history},
                {"role": "user", "content": user_input}
            ]
        )

        selections = resp.choices[0].message.content

        # save selections to memory
        with open(memory_path, "a") as f:
            f.write(f"\n{selections}")

        memory += f"\n{selections}"

personas = ["buffeteer", "diner", "gourmet", "nibbler", "sampler", "savorer", "snacker"]

for persona in personas:
    process_all_dates(persona)
