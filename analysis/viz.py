import ast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

df = pd.read_csv("./data/responses_full.csv")
df["history"] = df["history"].apply(ast.literal_eval)
df["choices"] = df["choices"].apply(ast.literal_eval)
df = df.drop_duplicates(subset=["user_id"])
df["selection_count"] = df["history"].apply(len)


def process_choices(choices):
    chosen_headlines = []
    for _, v in choices.items():
        selected = v["selected"]
        options = v["options"]
        for hed, source in options.items():
            if hed == selected:
                chosen_headlines.append(source)

    return chosen_headlines


df["preference"] = df["choices"].apply(process_choices)

df["proportion_generated"] = df.preference.apply(
    lambda x: sum([1 for y in x if y == "Generated"]) / len(x)
)

# Convert proportions to counts
selection_counts = (df["proportion_generated"] * 5).astype(int)

# Set the style for a clean, modern look
# plt.style.use("seaborn")
sns.set_palette("husl")

# Generate sample data based on the paper's findings
n_participants = len(selection_counts)

# Create figure with specified size
plt.figure(figsize=(12, 6))

# Set larger font sizes globally
plt.rcParams.update({"font.size": 14})

# Create the bar plot
sns.countplot(x=selection_counts, order=range(6))

# Customize the plot
plt.title(
    "Distribution of LLM-Generated Headline Selections",
    fontsize=18,
    pad=20,
)
plt.xlabel("Number of LLM Headlines Selected (out of 5)", fontsize=16)
plt.ylabel("Number of Participants", fontsize=16)

# Format x-axis with proper labels
plt.xticks(range(6), [f"{i} of 5" for i in range(6)], fontsize=14)
plt.yticks(fontsize=14)

# Add a text box with summary statistics
stats_text = (
    f"n = {n_participants}\n"
    f"Mean: {np.mean(selection_counts):.1f} of 5\n"
    f"Median: {np.median(selection_counts):.1f} of 5\n"
    f"Std Dev: {np.std(selection_counts):.1f}"
)
plt.text(
    0.95,
    0.95,
    stats_text,
    transform=plt.gca().transAxes,
    verticalalignment="top",
    horizontalalignment="right",
    bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    fontsize=14,
)

# Adjust layout and display
plt.tight_layout()
plt.show()

# Optional: Save the figure
plt.savefig("llm_preferences.png", dpi=300, bbox_inches="tight")
