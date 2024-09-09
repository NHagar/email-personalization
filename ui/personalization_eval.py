from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

llm = OpenAI()

def get_persona_preference(persona_name, choice_1, choice_2):
    with open(f"./src/prompts/personas/{persona_name}.txt", "r") as f:
        persona = f.read()

    with open(f"./data/memories/{persona_name}.txt", "r") as f:
        memory = f.read()

    with open("./src/prompts/persona_preference.txt", "r") as f:
        prompt_preference = f.read()


    user_input = f"PERSONA:\n{persona}\nREADING HISTORY:\n{memory}\n\nHEADLINE CHOICE 1: {choice_1}\nHEADLINE CHOICE 2: {choice_2}"

    resp = llm.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt_preference},
            {"role": "user", "content": user_input}
        ]
    )

    return resp.choices[0].message.content
