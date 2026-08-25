import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DB_PATH = ROOT / "cell_counts.db"
POPULATIONS = ("b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte")

SCHEMA = """
PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS sample_frequencies;
DROP TABLE IF EXISTS cell_counts;
DROP TABLE IF EXISTS samples;
DROP TABLE IF EXISTS populations;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS projects;

CREATE TABLE projects (
    project_id TEXT PRIMARY KEY
);

CREATE TABLE subjects (
    project_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    indication TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    PRIMARY KEY (project_id, subject_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE samples (
    sample_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    treatment TEXT NOT NULL,
    response TEXT,
    sample_type TEXT NOT NULL,
    time_from_treatment_start INTEGER NOT NULL,
    FOREIGN KEY (project_id, subject_id)
        REFERENCES subjects(project_id, subject_id)
);

CREATE TABLE populations (
    population TEXT PRIMARY KEY
);

CREATE TABLE cell_counts (
    sample_id TEXT NOT NULL,
    population TEXT NOT NULL,
    count INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (sample_id, population),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (population) REFERENCES populations(population)
);

CREATE INDEX idx_subjects_indication ON subjects(indication);
CREATE INDEX idx_samples_cohort
    ON samples(treatment, sample_type, time_from_treatment_start, response);
CREATE INDEX idx_cell_counts_population ON cell_counts(population);

CREATE VIEW sample_frequencies AS
SELECT
    sample_id AS sample,
    SUM(count) OVER (PARTITION BY sample_id) AS total_count,
    population,
    count,
    100.0 * count / SUM(count) OVER (PARTITION BY sample_id) AS percentage
FROM cell_counts;
"""


def load_data() -> None:
    projects = set()
    subjects = {}
    samples = []
    counts = []

    with CSV_PATH.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            project_id = row["project"]
            subject_id = row["subject"]
            sample_id = row["sample"]

            projects.add(project_id)
            subjects[(project_id, subject_id)] = (
                project_id,
                subject_id,
                row["condition"],
                int(row["age"]),
                row["sex"],
            )
            samples.append(
                (
                    sample_id,
                    project_id,
                    subject_id,
                    row["treatment"],
                    row["response"] or None,
                    row["sample_type"],
                    int(row["time_from_treatment_start"]),
                )
            )
            counts.extend(
                (sample_id, population, int(row[population]))
                for population in POPULATIONS
            )

    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(SCHEMA)
        connection.executemany(
            "INSERT INTO projects VALUES (?)",
            [(project_id,) for project_id in sorted(projects)],
        )
        connection.executemany(
            "INSERT INTO subjects VALUES (?, ?, ?, ?, ?)",
            subjects.values(),
        )
        connection.executemany(
            "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?)",
            samples,
        )
        connection.executemany(
            "INSERT INTO populations VALUES (?)",
            [(population,) for population in POPULATIONS],
        )
        connection.executemany(
            "INSERT INTO cell_counts VALUES (?, ?, ?)",
            counts,
        )

    print(f"Loaded {len(samples):,} samples into {DB_PATH.name}")


if __name__ == "__main__":
    load_data()
