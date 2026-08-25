# Immune Cell Analysis

This project loads 11,500 samples into SQLite, creates the requested analysis files, and shows the results in a Streamlit dashboard.

## Main finding

CD4 T-cell frequency differed between responders and non-responders before correcting for the five comparisons. Its raw p-value was 0.013, below the 0.05 cutoff. After accounting for all five comparisons, no cell population met that cutoff. I treat this as an early pattern, not proof that CD4 T-cell frequency predicts response.

## Run in GitHub Codespaces

```bash
make setup
make pipeline
make dashboard
```

Open the forwarded port shown by Codespaces. The local dashboard link is [http://localhost:8501](http://localhost:8501).

`make pipeline` creates `cell_counts.db` in the repository root and writes all analysis files to `outputs/`. You can also run `python load_data.py` by itself to rebuild the database.

## Outputs

- `outputs/sample_frequencies.csv`: one row per sample and cell population with the count, sample total, and percentage
- `outputs/responder_statistics.csv`: results from the Mann–Whitney U test, which compares the two response groups, plus a correction for testing five populations at once
- `outputs/responder_boxplots.png`: responder versus non-responder boxplots
- `outputs/baseline_samples.csv`: melanoma PBMC miraclib samples at day 0
- `outputs/samples_by_project.csv`
- `outputs/subjects_by_response.csv`
- `outputs/subjects_by_gender.csv`

The response analysis compares individual PBMC samples from responders and non-responders. PBMC means peripheral blood mononuclear cell, a type of blood sample. Each available sample is one observation, so a subject can appear at more than one timepoint. The analysis looks for a link with response. It does not prove that cell frequency can predict response.

## Database schema

- `projects`: one row per project
- `subjects`: one row per subject within a project, with indication, age, and gender
- `samples`: one row per sample, with treatment, response, sample type, and timepoint
- `populations`: the available immune cell populations
- `cell_counts`: one row per sample and population
- `sample_frequencies`: a view that calculates total counts and relative frequencies

I keep project, subject, and sample data in separate tables. This avoids repeating subject details and supports samples collected from the same subject over time. Each cell count has its own row, so a new cell population can be added without changing the table columns. The database uses indexes, which help the analysis filters run faster. SQLite is enough for hundreds of projects and thousands of samples. A server database such as PostgreSQL would be a better choice for much larger data or many people using the dashboard at once.

## Code structure

- `load_data.py` creates the schema and loads `cell-count.csv` using the Python standard library.
- `pipeline.py` rebuilds the database and generates every required table and plot.
- `dashboard.py` provides the interactive Streamlit dashboard.

I kept loading, analysis, and the dashboard in separate files so each file has one clear job. A larger program structure would add complexity without helping this dataset.
