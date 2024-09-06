import json
import os
from pathlib import Path

import pandas as pd
import requests

from dotenv import load_dotenv
load_dotenv()

nyt_api_key = os.getenv("NYTIMES_API_KEY")

endpoint = "https://api.nytimes.com/svc/archive/v1/2024/{month}.json?api-key={api_key}"

for i in range(5, 8):
    endpoint_filled = endpoint.format(month=i, api_key=nyt_api_key)
    response = requests.get(endpoint_filled)
    data = response.json()
    # save data to a file
    with open(f"./data/nyt_archive_2024_{i}.json", "w") as f:
        json.dump(data, f)
    print(f"Saved data for month {i}")

# get all nyt archive data
paths = list(Path("./data").glob("nyt_archive_2024_*.json"))

all_dfs = []
for path in paths:
    with open(path, "r") as f:
        data = json.load(f)

    parsed_items = []
    for item in data["response"]["docs"]:
        headline = item["headline"]["main"]
        abstract = item["abstract"]
        document_type = item["document_type"]
        desk = item["news_desk"]
        pub_date = item["pub_date"]
        parsed_items.append({
            "headline": headline,
            "abstract": abstract,
            "document_type": document_type,
            "news_desk": desk,
            "pub_date": pub_date
        })

    idf = pd.DataFrame(parsed_items)
    idf = idf[(idf.document_type == "article") & (idf.news_desk.notna()) & (idf.news_desk!="Obits")]
    all_dfs.append(idf)

pd.concat(all_dfs).to_parquet("./data/nyt_archive_all.parquet", index=False)
