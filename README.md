# UDS Project

This repository contains the full workflow for a project on generative AI exposure, unemployment, and wages using CPS ASEC data. The main question is whether workers in industries with higher AI exposure experienced different labor market outcomes after the arrival of GenAI tools, and whether those patterns were more pronounced for younger workers.

The final stakeholder-facing memo, the technical memo notebook, the analytical notebook, and the data-construction workflow are all included here.

## Where The Main Work Lives

The final workflow is centered on four files:

- `data_merging.ipynb`
  Builds the analytical dataset by merging CPS ASEC data with the AIIE / AIOE exposure files and the Census crosswalks.
- `models/causal_analysis.ipynb`
  Contains the main descriptive analysis, event-study checks, difference-in-differences models, robustness checks, and age heterogeneity analysis.
- `reports/data_science_memo.ipynb`
  Contains the stakeholder-facing memo plus the technical appendix.
- `notebook_helpers.py`
  Shared helper functions used across notebooks.


## Repository Structure

- `data/`
  Raw and derived data files used in the project.
- `models/`
  Analysis notebooks and helper scripts related to model estimation and figure generation.
- `reports/`
  Final report artifacts, exported memo files, the memo notebook, the stakeholder report, and copied figure assets.
- `reports/causal_analysis_figures/`
  Saved figures produced by the causal analysis workflow.
- `reports/figures/`
  Copied figures used in the stakeholder memo.

## Data Files

Key input and derived files in `data/`:

- `cps_00001.csv`
  Main CPS ASEC extract used for analysis.
- `AIOE_DataAppendix.xlsx`
  Source for AI occupation and industry exposure measures.
- `2022-Census-Industry-Code-List-with-Crosswalk.xlsx`
- `2017-industry-code-list-with-crosswalk.xlsx`
- `2018-occupation-code-list-and-crosswalk.xlsx`
  Crosswalks used to align Census industry and occupation coding across years.
- `data_with_aiie.csv`
  Final merged analytical dataset used in the modeling notebooks.

## Reproducibility

### 1. Set up the environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Rebuild the analytical dataset

If the raw CPS data or crosswalk files change, rerun:

- `data_merging.ipynb`

This notebook writes:

- `data/data_with_aiie.csv`

If `data/data_with_aiie.csv` is already up to date, this step can be skipped.

### 3. Rerun the analysis notebook

Run:

- `models/causal_analysis.ipynb`

This notebook contains:

- sample restrictions and variable construction
- descriptive plots
- event-study / parallel-trends diagnostics
- unemployment and wage DiD models
- robustness checks excluding 2020
- age heterogeneity tests

### 4. Regenerate saved figures

The report materials use saved figure files rather than only notebook-rendered plots.

To regenerate them, either:

- rerun the relevant figure cells in `models/causal_analysis.ipynb`, or
- run:

```bash
./.venv/bin/python models/regenerate_causal_figures.py
```

This writes figures into:

- `reports/causal_analysis_figures/`

### 5. Rerun the memo notebook

Run:

- `reports/data_science_memo.ipynb`

This notebook contains the final stakeholder memo plus a technical appendix. It references the saved figures in `reports/causal_analysis_figures/`.

### 6. Export the memo notebook

The notebook includes export cells at the bottom. From inside the notebook directory, they create:

- `reports/data_science_memo_submission.html`
- `reports/no_code_data_science_memo_submission.html`


It also copies the figure assets into:

- `reports/figures/`

## Main Outputs

Key final outputs in `reports/`:
- `data_science_memo_stakeholder.pdf`
  Stakeholder-oriented memo without the technical appendix, this is what we submitted.
- `data_science_memo.ipynb`
  Main memo notebook with stakeholder memo and technical appendix.
- `data_science_memo_submission.html`
  Exported version of the memo notebook.
- `data_science_memo.pdf`
- `data_science_memo_submission.pdf`
  PDF report outputs.


## Notes

- The final memo notebook is in `reports/`, not `models/`.
- The analysis figures used in the memo are stored in `reports/causal_analysis_figures/`.
- `notebook_helpers.py` is the shared source of helper functions. The notebooks are designed to import from it rather than redefining the same functions in multiple places.
- The stakeholder memo and the technical appendix serve different audiences:
  - `reports/data_science_memo_stakeholder.pdf` is the concise, non-technical memo for submission.
  - `reports/data_science_memo.ipynb` includes the more detailed appendix and reproducibility material.
