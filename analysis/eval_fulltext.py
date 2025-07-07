#!/usr/bin/env python3
"""
Expanded evaluation script for headline generation workflow.
Processes 30 user annotations across all 5 newsletters and calculates accuracy rates.
"""

import json
import random
import string
from pathlib import Path
from typing import Dict, List, Tuple

import duckdb
import pandas as pd
from openai import OpenAI
from pydantic import BaseModel
from tqdm import tqdm


class RankingResponse(BaseModel):
    rank1_id: str
    rank1_headline: str
    rank1_explanation: str
    rank2_id: str
    rank2_headline: str
    rank2_explanation: str


class HeadlineResponse(BaseModel):
    explanation: str
    headline: str
    subhed: str


class AccuracyEval(BaseModel):
    accuracy_rating: str
    reasoning: str
    issue_category: str


class EvaluationResult:
    def __init__(self):
        self.results = []
        self.total_evaluations = 0
        self.pass_count = 0
        self.per_user_stats = {}

    def add_result(
        self,
        user_idx: int,
        newsletter_name: str,
        item_id: str,
        accuracy_rating: str,
        reasoning: str,
        issue_category: str,
    ):
        self.results.append(
            {
                "user_idx": user_idx,
                "newsletter": newsletter_name,
                "item_id": item_id,
                "accuracy_rating": accuracy_rating,
                "reasoning": reasoning,
                "issue_category": issue_category,
            }
        )

        self.total_evaluations += 1
        if accuracy_rating == "Pass":
            self.pass_count += 1

        # Track per-user stats
        if user_idx not in self.per_user_stats:
            self.per_user_stats[user_idx] = {"total": 0, "pass": 0}
        self.per_user_stats[user_idx]["total"] += 1
        if accuracy_rating == "Pass":
            self.per_user_stats[user_idx]["pass"] += 1

    def get_overall_accuracy(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.pass_count / self.total_evaluations

    def get_per_user_accuracy(self) -> Dict[int, float]:
        per_user_accuracy = {}
        for user_idx, stats in self.per_user_stats.items():
            if stats["total"] > 0:
                per_user_accuracy[user_idx] = stats["pass"] / stats["total"]
            else:
                per_user_accuracy[user_idx] = 0.0
        return per_user_accuracy


def load_prompts() -> Tuple[str, str, str]:
    """Load prompts from files."""
    with open("./prompts/item_ranking.txt", "r") as f:
        prompt_rank = f.read()

    with open("./prompts/framing.txt", "r") as f:
        prompt_write = f.read()

    with open("./prompts/evals/accuracy.md", "r") as f:
        prompt_accuracy = f.read()

    return prompt_rank, prompt_write, prompt_accuracy


def sample_user_annotations(
    con: duckdb.DuckDBPyConnection, n_samples: int = 30
) -> List[str]:
    """Sample n user annotations from responses."""
    responses = con.execute(
        "SELECT user_annotations FROM './data/responses_full.csv' WHERE user_annotations != 'not collected' AND user_annotations IS NOT NULL"
    ).fetchdf()

    if len(responses) < n_samples:
        print(
            f"Warning: Only {len(responses)} annotations available, using all of them"
        )
        return responses.user_annotations.tolist()

    return random.sample(responses.user_annotations.tolist(), n_samples)


def get_newsletter_paths() -> List[Path]:
    """Get paths to all newsletter files."""
    data_path = Path("./data/emails")
    return [
        data_path
        / "Arizona and Missouri Will Vote on Abortion in November - The New York Times.csv",
        data_path / "Harris and Trump Battled for the Midwest - The New York Times.csv",
        data_path
        / "In Chicago, Obama Aims to Resurrect a Movement - The New York Times.csv",
        data_path
        / "Russia Freed Evan Gershkovich in a Major Prisoner Swap - The New York Times.csv",
        data_path / "Trump's Pitch to Parents - The New York Times.csv",
    ]


def process_newsletter(
    con: duckdb.DuckDBPyConnection, newsletter_path: Path
) -> Tuple[pd.DataFrame, str]:
    """Process a single newsletter to get stories and day of week."""
    stories = con.execute(
        f"SELECT 'HEADLINE: ' || headline || '\n\nDESCRIPTION: ' || description AS newsletter_item, url FROM '{newsletter_path}' WHERE headline != 'SKIP' "
    ).fetchdf()

    # Add alphabetical letter ID for each item
    stories["item_id"] = [string.ascii_uppercase[i] for i in range(len(stories))]
    stories["newsletter_item"] = stories.apply(
        lambda row: f"{row['newsletter_item']}\n\nID: {row['item_id']}", axis=1
    )

    day_of_week = pd.to_datetime(
        con.execute(f"SELECT publication_date FROM '{newsletter_path}' LIMIT 1")
        .fetchdf()
        .publication_date.iloc[0]
    ).day_name()

    return stories, day_of_week


def rank_stories(
    client: OpenAI, user_annotation: str, stories: pd.DataFrame, prompt_rank: str
) -> dict:
    """Rank stories based on user annotation."""
    format_input = f"""USER NOTES: {user_annotation}

CANDIDATE STORIES: {"\n".join(stories.newsletter_item.tolist())}"""

    messages = [
        {"role": "system", "content": prompt_rank},
        {"role": "user", "content": format_input},
    ]

    resp = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=messages,  # type: ignore
        response_format=RankingResponse,
        temperature=0.7,
    )

    content = resp.choices[0].message.content
    if content is None:
        raise ValueError("No content received from ranking API")
    return json.loads(content)


def generate_headlines(
    client: OpenAI,
    stories: pd.DataFrame,
    rankings: dict,
    day_of_week: str,
    prompt_write: str,
) -> dict:
    """Generate headlines for ranked stories."""
    items_for_rewrite = stories[
        stories.item_id.isin([rankings["rank1_id"], rankings["rank2_id"]])
    ].newsletter_item.tolist()

    format_input = f"""STORIES: {"\n".join(items_for_rewrite)}
DAY OF WEEK: {day_of_week}
"""

    messages = [
        {"role": "system", "content": prompt_write},
        {"role": "user", "content": format_input},
    ]

    resp = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=messages,  # type: ignore
        temperature=0.7,
        response_format=HeadlineResponse,
    )

    content = resp.choices[0].message.content
    if content is None:
        raise ValueError("No content received from headline generation API")
    return json.loads(content)


def map_id_to_fulltext(
    item_id: str, stories: pd.DataFrame, fulltext: pd.DataFrame
) -> str:
    """Map item ID to fulltext."""
    url = stories[stories.item_id == item_id].url.iloc[0]
    return fulltext[fulltext.url == url].text.iloc[0]


def evaluate_accuracy(
    client: OpenAI, generated_headline: str, item_fulltext: str, prompt_accuracy: str
) -> AccuracyEval:
    """Evaluate accuracy of generated headline against fulltext."""
    eval_input = f"""GENERATED HEADLINE: {generated_headline}

FULL ARTICLE TEXT: {item_fulltext}"""

    eval_result = client.responses.parse(
        model="gpt-4.1-2025-04-14",
        instructions=prompt_accuracy,
        input=eval_input,
        text_format=AccuracyEval,
    )

    if eval_result.output_parsed is None:
        raise ValueError("No parsed output received from accuracy evaluation API")
    return eval_result.output_parsed


def main():
    """Main evaluation function."""
    # Setup
    random.seed(42)  # For reproducibility
    con = duckdb.connect(database=":memory:")
    client = OpenAI()

    # Load data and prompts
    prompt_rank, prompt_write, prompt_accuracy = load_prompts()
    fulltext = pd.read_csv("./data/nyt_fulltext.csv", usecols=["url", "text"])
    newsletter_paths = get_newsletter_paths()

    # Sample user annotations
    user_annotations = sample_user_annotations(con, 30)
    print(f"Sampled {len(user_annotations)} user annotations")

    # Initialize results tracker
    results = EvaluationResult()

    # Process each user annotation with each newsletter
    total_combinations = len(user_annotations) * len(newsletter_paths)
    
    with tqdm(total=total_combinations, desc="Processing combinations") as pbar:
        for user_idx, user_annotation in enumerate(user_annotations):
            for newsletter_path in newsletter_paths:
                newsletter_name = newsletter_path.stem
                pbar.set_description(f"User {user_idx + 1}/{len(user_annotations)} - {newsletter_name}")

                try:
                    # Process newsletter
                    stories, day_of_week = process_newsletter(con, newsletter_path)

                    # Rank stories
                    rankings = rank_stories(client, user_annotation, stories, prompt_rank)

                    # Generate headlines
                    headlines = generate_headlines(
                        client, stories, rankings, day_of_week, prompt_write
                    )

                    # Evaluate both ranked items
                    for item_id in [rankings["rank1_id"], rankings["rank2_id"]]:
                        item_fulltext = map_id_to_fulltext(item_id, stories, fulltext)

                        # Match the correct generated content to the ranked item
                        if item_id == rankings["rank1_id"]:
                            generated_content = headlines["headline"]
                        else:  # item_id == rankings["rank2_id"]
                            generated_content = headlines["subhed"]

                        accuracy_eval = evaluate_accuracy(
                            client, generated_content, item_fulltext, prompt_accuracy
                        )

                        results.add_result(
                            user_idx=user_idx,
                            newsletter_name=newsletter_name,
                            item_id=item_id,
                            accuracy_rating=accuracy_eval.accuracy_rating,
                            reasoning=accuracy_eval.reasoning,
                            issue_category=accuracy_eval.issue_category,
                        )

                except Exception as e:
                    tqdm.write(f"Error processing User {user_idx + 1} - {newsletter_name}: {e}")
                    continue
                finally:
                    pbar.update(1)

    # Calculate and display results
    print(f"\n{'='*50}")
    print("EVALUATION RESULTS")
    print(f"{'='*50}")

    overall_accuracy = results.get_overall_accuracy()
    print(
        f"Overall Accuracy: {overall_accuracy:.2%} ({results.pass_count}/{results.total_evaluations})"
    )

    per_user_accuracy = results.get_per_user_accuracy()
    print("\nPer-User Accuracy:")
    for user_idx in sorted(per_user_accuracy.keys()):
        accuracy = per_user_accuracy[user_idx]
        total = results.per_user_stats[user_idx]["total"]
        passed = results.per_user_stats[user_idx]["pass"]
        print(f"  User {user_idx}: {accuracy:.2%} ({passed}/{total})")

    # Save detailed results
    results_df = pd.DataFrame(results.results)
    results_df.to_csv("./data/evaluation_results.csv", index=False)
    print("\nDetailed results saved to ./data/evaluation_results.csv")

    # Summary statistics
    print("\nSummary Statistics:")
    print(f"  Total evaluations: {results.total_evaluations}")
    print(f"  Pass count: {results.pass_count}")
    print(f"  Fail count: {results.total_evaluations - results.pass_count}")
    print(
        f"  Average per-user accuracy: {sum(per_user_accuracy.values()) / len(per_user_accuracy):.2%}"
    )


if __name__ == "__main__":
    main()
