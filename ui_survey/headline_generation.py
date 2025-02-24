import json
from datetime import datetime
from pathlib import Path

import duckdb
from openai import OpenAI
from pydantic import BaseModel
from streamlit import secrets

llm = OpenAI(api_key=secrets["OPENAI_API_KEY"])
con = duckdb.connect(database=":memory:")

with open("./prompts/infer_interests.txt", "r") as f:
    prompt_history = f.read()

with open("./prompts/item_ranking.txt", "r") as f:
    prompt_ranking = f.read()

with open("./prompts/framing.txt", "r") as f:
    prompt_framing = f.read()

data_path = Path("./data/emails")

newsletter_paths = [
    data_path
    / "Arizona and Missouri Will Vote on Abortion in November - The New York Times.csv",
    data_path / "Harris and Trump Battled for the Midwest - The New York Times.csv",
    data_path
    / "In Chicago, Obama Aims to Resurrect a Movement - The New York Times.csv",
    data_path
    / "Russia Freed Evan Gershkovich in a Major Prisoner Swap - The New York Times.csv",
    data_path / "Trump’s Pitch to Parents - The New York Times.csv",
]


class HeadlineResponse(BaseModel):
    explanation: str
    headline: str
    subhed: str


class HeadlineGenerator:
    def __init__(self, items_read) -> None:
        self.items_read = items_read
        self.prompt_history = prompt_history
        self.prompt_ranking = prompt_ranking
        self.prompt_framing = prompt_framing

        self.model = "gpt-4o"

        self.personalization_input_format = (
            f"""USER READING HISTORY: {"\n".join(self.items_read)}"""
        )

        self.user_annotations = ""

    def infer_interests(self):
        messages = [
            {"role": "system", "content": self.prompt_history},
            {"role": "user", "content": self.personalization_input_format},
        ]
        resp = llm.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        self.user_annotations = resp.choices[0].message.content

    def load_newsletter(self, newsletter_path):
        self.newsletter_items = con.execute(
            f"SELECT *, 'HEADLINE: ' || headline || '\nDESCRIPTION: ' || description AS formatted FROM '{newsletter_path}' WHERE headline != 'SKIP'"
        ).fetch_df()

        self.original_heading = (
            con.execute(
                f"SELECT '#### ' || newsletter_headline || '\n' || '**' || newsletter_sub_hed || '**' AS heading FROM '{newsletter_path}' "
            )
            .fetch_df()
            .iloc[0, 0]
        )
        self.day_of_week = datetime.strptime(
            self.newsletter_items.publication_date[0], "%b. %d, %Y"
        ).strftime("%A")

    def rank_items(self):
        format_input = f"""USER NOTES: {self.user_annotations}
            
            CANDIDATE STORIES: {"\n".join(self.newsletter_items.formatted.tolist())}"""
        messages = [
            {"role": "system", "content": self.prompt_ranking},
            {"role": "user", "content": format_input},
        ]
        resp = llm.chat.completions.create(
            model=self.model, messages=messages, stop="3."
        )

        return resp.choices[0].message.content

    def generate_heading(self):
        format_input = f"""STORIES: {self.rank_items()}
            
            DAY OF WEEK: {self.day_of_week}"""
        messages = [
            {"role": "system", "content": self.prompt_framing},
            {"role": "user", "content": format_input},
        ]
        resp = llm.beta.chat.completions.parse(
            model=self.model, messages=messages, response_format=HeadlineResponse
        )

        resp_data = json.loads(resp.choices[0].message.content)
        output = f"""#### {resp_data["headline"]}\n**{resp_data["subhed"]}**"""

        return output
