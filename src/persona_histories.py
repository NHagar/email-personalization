# 4 prompt components:
    # 1. Instructions
    # 2. Persona
    # 3. Reading history (if available)
    # 4. Candidate stories

# %%
import datetime

import duckdb
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

llm = OpenAI()

# %%
con = duckdb.connect(":memory:")

start_date = datetime.date(2024, 5, 1)
end_date = datetime.date(2024, 7, 31)
date_list = [(start_date + datetime.timedelta(days=x)).strftime('%Y-%m-%d') for x in range((end_date - start_date).days + 1)]

for i in range(len(date_list)):
    curr = date_list[i]
    nex = date_list[i+1] if i+1 < len(date_list) else "2024-08-01"
    headlines = con.execute(f"SELECT headline FROM '../data/nyt_archive_all.parquet' WHERE pub_date >= '{curr}' AND pub_date < '{next}' ").fetchdf().headline.tolist()
