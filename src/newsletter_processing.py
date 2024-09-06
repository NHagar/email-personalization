import json
from pathlib import Path

from bs4 import BeautifulSoup
import html2text
from openai import OpenAI
import pandas as pd
from pydantic import BaseModel

from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

# convert html to markdown
print("Converting HTML to Markdown")
files = list(Path("./data/emails").rglob("*.html"))

for file in tqdm(files):
    with open(file, "r") as html:
        soup = BeautifulSoup(html.read(), "html.parser")

    body = str(soup.body)

    text = html2text.html2text(body)

    with open(file.with_suffix(".md"), "w") as md:
        md.write(text)

# extract newsletter items from markdown
print("Extracting newsletter items")

llm = OpenAI()
with open("src/prompts/extraction.txt", "r") as f:
    prompt_extract = f.read()

with open("src/prompts/metadata.txt", "r") as f:
    prompt_metadata = f.read()

class NewsletterItem(BaseModel):
    headline: str
    url: str
    description: str

class NewsletterMetadata(BaseModel):
    headline: str
    sub_hed: str
    publication_date: str

files = list(Path("./data/emails").rglob("*.md"))

for file in tqdm(files):
    with open(file, "r") as f:
        content = f.read()

    # extract metadata
    resp = llm.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt_metadata},
            {"role": "user", "content": content}
        ],
        response_format=NewsletterMetadata
    )

    metadata = json.loads(resp.choices[0].message.content)

    # extract newsletter items
    items_structured = []
    chunks = content.split("* * *")
    for chunk in chunks:
        resp = llm.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": prompt_extract},
                {"role": "user", "content": chunk}
            ],
            response_format=NewsletterItem
        )
        items_structured.append(json.loads(resp.choices[0].message.content))

    items_df = pd.DataFrame(items_structured)
    items_df["publication_date"] = metadata["publication_date"]
    items_df["newsletter_headline"] = metadata["headline"]
    items_df["newsletter_sub_hed"] = metadata["sub_hed"]

    # save to csv
    items_df.to_csv(file.with_suffix(".csv"), index=False)
