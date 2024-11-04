import json
import random
from datetime import datetime

import duckdb
import gspread
import streamlit as st
import streamlit_survey as ss
from google.oauth2 import service_account
from headline_generation import HeadlineGenerator, newsletter_paths

con = duckdb.connect("database.db")

with open("./ui_survey/consent_form.md", "r") as f:
    consent_screen = f.read()

query = """WITH proportions AS (
  SELECT
    news_desk,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM './data/nyt_archive_all.parquet') AS proportion
  FROM './data/nyt_archive_all.parquet'
  GROUP BY news_desk
),
samples AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY news_desk
      ORDER BY RANDOM()
    ) as rn,
    CEIL(proportion) as rows_to_sample
  FROM './data/nyt_archive_all.parquet'
  JOIN proportions USING (news_desk)
  WHERE LENGTH(headline) > 5
)
SELECT headline
FROM samples
WHERE rn <= rows_to_sample
LIMIT 100;"""


def initialize_google_sheets():
    """Initialize and return Google Sheets client."""
    # Create a connection object
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    return gspread.authorize(credentials)


def get_or_create_sheet(
    gc, spreadsheet_name="Survey Responses", worksheet_name="responses"
):
    """Get existing or create new spreadsheet and worksheet."""
    try:
        # First try to open by the spreadsheet ID if provided in secrets
        if "spreadsheet_id" in st.secrets:
            spreadsheet = gc.open_by_key(st.secrets["spreadsheet_id"])
        else:
            # Try to open by name
            spreadsheet = gc.open(spreadsheet_name)
    except (gspread.SpreadsheetNotFound, KeyError):
        # Create new spreadsheet
        spreadsheet = gc.create(spreadsheet_name)

        # Share with your account (replace with your email)
        spreadsheet.share(st.secrets["share_email"], perm_type="user", role="editor")

    # Get or create worksheet
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(worksheet_name, 1000, 20)
        # Add headers to the worksheet
        headers = ["timestamp", "user_id", "history", "choices"]
        worksheet.append_row(headers)

    return worksheet


def save_response(worksheet, response_data):
    """Save response to Google Sheets."""
    worksheet.append_row(
        [
            str(datetime.now()),
            response_data["user_id"],
            response_data["history"],
            response_data["choices"],
        ]
    )


@st.cache_data
def fetch_headlines():
    data = con.execute(query).fetchdf().headline.tolist()
    random.shuffle(data)

    return data


def render_headlines(survey, headlines, selections):
    st.write(
        "## Please select the headlines you would be interested in reading.\nYou can select as many or as few as are of interest to you."
    )
    for i, item in enumerate(headlines):
        if survey.checkbox(item, key=i, value=selections.get(item, False)):
            selections[item] = True
        else:
            selections[item] = False


headlines = fetch_headlines()

headlines_per_page = len(headlines) // 4

survey = ss.StreamlitSurvey()

if "selections" not in st.session_state:
    st.session_state.selections = {}
if "part1_completed" not in st.session_state:
    st.session_state.part1_completed = False
if "generated_headlines" not in st.session_state:
    st.session_state.generated_headlines = None
if "headline_preferences" not in st.session_state:
    st.session_state.headline_preferences = {}
if "consent_given" not in st.session_state:
    st.session_state.consent_given = False
if "survey_completed" not in st.session_state:
    st.session_state.survey_completed = False


def on_submit():
    st.session_state.part1_completed = True
    st.rerun()


if not st.session_state.consent_given:
    st.title("Consent to Participate in Research")
    st.markdown(consent_screen)
    signature = st.text_input("Electronic Signature:")
    date = st.date_input("Today's Date:")
    if st.button("I Agree"):
        if signature and date:
            st.session_state.consent_given = True
            st.rerun()
        else:
            st.error("Please provide both signature and date to proceed.")
    st.stop()


pages = survey.pages(4, on_submit=on_submit)

if st.session_state.consent_given and not st.session_state.survey_completed:
    if not st.session_state.part1_completed:
        with pages:
            if pages.current == 0:
                headlines_subset = headlines[:headlines_per_page]
                render_headlines(survey, headlines_subset, st.session_state.selections)
            elif pages.current == 1:
                headlines_subset = headlines[
                    headlines_per_page : 2 * headlines_per_page
                ]
                render_headlines(survey, headlines_subset, st.session_state.selections)
            elif pages.current == 2:
                headlines_subset = headlines[
                    2 * headlines_per_page : 3 * headlines_per_page
                ]
                render_headlines(survey, headlines_subset, st.session_state.selections)
            elif pages.current == 3:
                headlines_subset = headlines[3 * headlines_per_page :]
                render_headlines(survey, headlines_subset, st.session_state.selections)
    else:
        if st.session_state.generated_headlines is None:
            pairs = []
            shuffled_pairs = []
            progress_text = "Setting up part 2..."
            progress_bar = st.progress(0.0, "Setting up part 2...")

            hg = HeadlineGenerator(
                [k for k, v in st.session_state.selections.items() if v]
            )
            for i, p in enumerate(newsletter_paths[:5]):
                hg.load_newsletter(p)
                original = hg.original_heading
                generated = hg.generate_heading()
                pair = (
                    {"text": original, "source": "Original"},
                    {"text": generated, "source": "Generated"},
                )
                options = list(pair)
                random.shuffle(options)
                shuffled_pairs.append(options)
                pairs.append(pair)
                progress_bar.progress(
                    (i + 1) / len(newsletter_paths[:5]), "Setting up part 2..."
                )
            st.session_state.generated_headlines = pairs
            st.session_state.shuffled_headlines = shuffled_pairs

        else:
            pairs = st.session_state.generated_headlines
            shuffled_pairs = st.session_state.shuffled_headlines

        st.write(
            "### For each pair, select the headline that you would be more likely to click on and read. Consider both the main headline and the additional context below it."
        )

        for index, options in enumerate(shuffled_pairs):
            text_to_source = {opt["text"]: opt["source"] for opt in options}
            option_texts = [opt["text"] for opt in options]

            cols = st.columns(2)
            for i, opt in enumerate(options):
                with cols[i]:
                    st.markdown(f"**Option {i+1}**")
                    st.markdown(opt["text"])

            radio_key = f"radio_{index}"

            selected = st.radio(
                "Your choice:",
                option_texts,
                key=radio_key,
                format_func=lambda x: f"Option {option_texts.index(x) + 1}",
                label_visibility="collapsed",
            )

            st.session_state.headline_preferences[radio_key] = {
                "selected": selected,
                "options": text_to_source,
            }

            st.write("---")

        if st.button("Submit"):
            user_history = [k for k, v in st.session_state.selections.items() if v]
            user_preferences = st.session_state.headline_preferences

            results = {
                "user_id": st.query_params["user_id"],
                "history": json.dumps(user_history),
                "choices": json.dumps(user_preferences),
            }

            # Initialize Google Sheets
            gc = initialize_google_sheets()
            worksheet = get_or_create_sheet(gc)
            save_response(worksheet, results)

            st.session_state.survey_completed = True
            st.rerun()

if st.session_state.survey_completed:
    st.title("Debrief")
    st.write("""
    Thank you for participating in our study on headline preferences.

    The purpose of this study was to compare user preferences between AI-generated and human-written headlines.

    In Part 2 of this survey, you were asked to select between two headlines: One written by a human for the New York Times Evening Briefing newsletter, and one written by GPT-4o. The LLM-generated headline was personalized, based on the headlines you selected in Part 1.

    Your responses will help us understand how AI-generated content compares to human-written content in terms of user engagement and preference.

    If you have questions, concerns, or complaints, you can contact the Principal Investigator Nicholas Diakopoulos (nad@northwestern.edu), and co-investigators Nick Hagar (nicholas.hagar@northwestern.edu) and Jeremy Gilbert (jeremy.gilbert@northwestern.edu)..

    Thank you again for your participation!
    """)
    if st.button("Finish"):
        st.balloons()
        st.stop()
