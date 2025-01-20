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


# Set the style for a clean, modern look
# plt.style.use("seaborn")
sns.set_palette("husl")

# Generate sample data based on the paper's findings
proportion_generated = df["proportion_generated"]
n_participants = len(proportion_generated)

# Create figure with specified size
plt.figure(figsize=(12, 6))

# Set larger font sizes globally
plt.rcParams.update({"font.size": 14})

# Create the main distribution plot
sns.histplot(
    proportion_generated,
)

# Customize the plot
plt.title(
    "Distribution of Reader Preferences for LLM-Generated Headlines",
    fontsize=18,
    pad=20,
)
plt.xlabel("Proportion of LLM Headlines Selected", fontsize=16)
plt.ylabel("Participants", fontsize=16)

# Set x-axis limit to cap at 100%
plt.xlim(0, 1.0)

# Format x-axis with decile ticks
decile_ticks = np.arange(0, 1.1, 0.1)
plt.xticks(decile_ticks, fontsize=14)
plt.yticks(fontsize=14)
plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: "{:.0%}".format(x)))

# Add legend with larger font
plt.legend(loc="upper left", fontsize=14)

# Add a text box with summary statistics
stats_text = (
    f"n = {n_participants}\n"
    f"Mean: {np.mean(proportion_generated):.1%}\n"
    f"Median: {np.median(proportion_generated):.1%}\n"
    f"Std Dev: {np.std(proportion_generated):.1%}"
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
