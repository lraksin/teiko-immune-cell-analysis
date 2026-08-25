import sqlite3
from pathlib import Path

import matplotlib
import pandas as pd
from scipy import stats

from load_data import DB_PATH, POPULATIONS, load_data


matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"

RESPONDER_FREQUENCIES_SQL = """
SELECT
    s.sample_id AS sample,
    s.response,
    f.population,
    f.percentage
FROM sample_frequencies f
JOIN samples s ON f.sample = s.sample_id
JOIN subjects sub
    ON s.project_id = sub.project_id AND s.subject_id = sub.subject_id
WHERE sub.indication = 'melanoma'
  AND s.treatment = 'miraclib'
  AND s.sample_type = 'PBMC'
  AND s.response IN ('yes', 'no')
ORDER BY f.population, s.response, s.sample_id;
"""

BASELINE_CTE = """
WITH baseline AS (
    SELECT
        s.project_id AS project,
        s.subject_id AS subject,
        sub.indication,
        sub.age,
        sub.gender,
        s.sample_id AS sample,
        s.treatment,
        s.response,
        s.sample_type,
        s.time_from_treatment_start
    FROM samples s
    JOIN subjects sub
        ON s.project_id = sub.project_id AND s.subject_id = sub.subject_id
    WHERE sub.indication = 'melanoma'
      AND s.treatment = 'miraclib'
      AND s.sample_type = 'PBMC'
      AND s.time_from_treatment_start = 0
)
"""


def get_responder_frequencies(connection: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(RESPONDER_FREQUENCIES_SQL, connection)


def statistical_results(frequencies: pd.DataFrame) -> pd.DataFrame:
    results = []
    for population in POPULATIONS:
        population_data = frequencies[frequencies["population"] == population]
        responders = population_data.loc[
            population_data["response"] == "yes", "percentage"
        ]
        nonresponders = population_data.loc[
            population_data["response"] == "no", "percentage"
        ]
        statistic, p_value = stats.mannwhitneyu(
            responders, nonresponders, alternative="two-sided"
        )
        responder_median = responders.median()
        nonresponder_median = nonresponders.median()
        results.append(
            {
                "population": population,
                "responders_n": len(responders),
                "nonresponders_n": len(nonresponders),
                "responder_median": responder_median,
                "nonresponder_median": nonresponder_median,
                "median_difference": responder_median - nonresponder_median,
                "rank_biserial": 2 * statistic / (len(responders) * len(nonresponders)) - 1,
                "p_value": p_value,
            }
        )

    result = pd.DataFrame(results)
    result["adjusted_p_value"] = stats.false_discovery_control(
        result["p_value"].to_numpy(), method="bh"
    )
    result["significant"] = result["p_value"] < 0.05
    result["significant_after_bh"] = result["adjusted_p_value"] < 0.05
    return result


def save_boxplots(frequencies: pd.DataFrame) -> None:
    figure, axes = plt.subplots(1, len(POPULATIONS), figsize=(16, 4), sharey=True)
    for axis, population in zip(axes, POPULATIONS):
        data = frequencies[frequencies["population"] == population]
        axis.boxplot(
            [
                data.loc[data["response"] == "no", "percentage"],
                data.loc[data["response"] == "yes", "percentage"],
            ]
        )
        axis.set_xticks([1, 2], ["No", "Yes"])
        axis.set_title(population)
        axis.set_xlabel("Response")
    axes[0].set_ylabel("Relative frequency per sample (%)")
    figure.suptitle("Melanoma PBMC response to miraclib")
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / "responder_boxplots.png", dpi=160)
    plt.close(figure)


def run_pipeline() -> None:
    load_data()
    OUTPUT_DIR.mkdir(exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        summary = pd.read_sql_query(
            """
            SELECT sample, total_count, population, count, percentage
            FROM sample_frequencies
            ORDER BY sample, population
            """,
            connection,
        )
        frequencies = get_responder_frequencies(connection)
        baseline = pd.read_sql_query(
            BASELINE_CTE + "SELECT * FROM baseline ORDER BY project, subject, sample",
            connection,
        )
        samples_by_project = pd.read_sql_query(
            BASELINE_CTE
            + """
            SELECT project, COUNT(*) AS samples
            FROM baseline
            GROUP BY project
            ORDER BY project
            """,
            connection,
        )
        subjects_by_response = pd.read_sql_query(
            BASELINE_CTE
            + """
            SELECT response, COUNT(*) AS subjects
            FROM (SELECT DISTINCT project, subject, response FROM baseline)
            GROUP BY response
            ORDER BY response
            """,
            connection,
        )
        subjects_by_gender = pd.read_sql_query(
            BASELINE_CTE
            + """
            SELECT gender, COUNT(*) AS subjects
            FROM (SELECT DISTINCT project, subject, gender FROM baseline)
            GROUP BY gender
            ORDER BY gender
            """,
            connection,
        )

    results = statistical_results(frequencies)
    summary.to_csv(OUTPUT_DIR / "sample_frequencies.csv", index=False)
    results.to_csv(OUTPUT_DIR / "responder_statistics.csv", index=False)
    baseline.to_csv(OUTPUT_DIR / "baseline_samples.csv", index=False)
    samples_by_project.to_csv(OUTPUT_DIR / "samples_by_project.csv", index=False)
    subjects_by_response.to_csv(OUTPUT_DIR / "subjects_by_response.csv", index=False)
    subjects_by_gender.to_csv(OUTPUT_DIR / "subjects_by_gender.csv", index=False)
    save_boxplots(frequencies)

    significant = results.loc[results["significant"], "population"].tolist()
    adjusted_significant = results.loc[
        results["significant_after_bh"], "population"
    ].tolist()
    print(f"Wrote {len(summary):,} frequency rows to outputs/")
    print("Populations with p < 0.05:", ", ".join(significant) or "none")
    print(
        "Significant after BH correction:",
        ", ".join(adjusted_significant) or "none",
    )
    print(f"Baseline samples: {len(baseline):,}")


if __name__ == "__main__":
    run_pipeline()
