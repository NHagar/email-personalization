import json
import os

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
