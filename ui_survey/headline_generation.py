from pathlib import Path

import duckdb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

llm = OpenAI()
con = duckdb.connect(database=":memory:")

with open("src/prompts/infer_interests.txt", "r") as f:
    prompt_history = f.read()

with open("src/prompts/item_ranking.txt", "r") as f:
    prompt_ranking = f.read()

with open("src/prompts/framing.txt", "r") as f:
    prompt_framing = f.read()

newsletter_paths = list(Path("./data/emails").rglob("*.csv"))


def get_original_heading(newsletter_path):
    return (
        con.execute(
            f"SELECT '# ' || newsletter_headline || '\n\n' || '## ' || newsletter_sub_hed AS heading FROM '{newsletter_path}' "
        )
        .fetch_df()
        .iloc[0, 0]
    )


def get_newsletter_items(newsletter_path):
    return con.execute(
        f"SELECT *, 'HEADLINE: ' || headline || '\nDESCRIPTION: ' || description AS formatted FROM '{newsletter_path}' WHERE headline != 'SKIP'"
    ).fetch_df()


def generate_heading(newsletter_path, items_read):
    items = get_newsletter_items(newsletter_path)
    personalization_input_format = f"""USER READING HISTORY: {"\n".join(items_read)}"""

    messages = [
        {"role": "system", "content": prompt_history},
        {"role": "user", "content": personalization_input_format},
    ]

    resp = llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

    messages.append({"role": "assistant", "content": resp.choices[0].message.content})

    items_input = f"""CANDIDATE ITEMS: {"\n".join(items.formatted.tolist())}"""

    messages.append({"role": "user", "content": items_input})

    # replace first item with new system prompt
    messages[0]["content"] = prompt_ranking

    resp = llm.chat.completions.create(
        model="gpt-4o-mini", messages=messages, stop="3."
    )

    messages.append({"role": "assistant", "content": resp.choices[0].message.content})

    format_input = f"""STORIES: {resp.choices[0].message.content}"""

    messages.append({"role": "user", "content": format_input})

    # replace first item with new system prompt
    messages[0]["content"] = prompt_framing

    resp = llm.chat.completions.create(model="gpt-4o-mini", messages=messages)

    return resp.choices[0].message.content
