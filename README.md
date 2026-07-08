# NECTA CSEE All Country Performance Dashboard

## Project Overview

The NECTA CSEE All Country Performance Dashboard is a Streamlit
decision-support system for exploring Tanzania Certificate of Secondary
Education Examination results. It combines national, regional, school, and
subject analysis with rankings, risk signals, short-term forecasts, and a
hypothetical 2032 examination-demand planning simulator.

The system is designed for both technical and non-technical users:

- Parents can understand school and subject performance.
- Teachers and headmasters can identify academic strengths and intervention
  priorities.
- School owners can compare institutional results and momentum.
- Policymakers can monitor regional gaps, candidate outcomes, and risk.
- Researchers can inspect methodology, model evidence, and limitations.

## Problem Statement

CSEE results are published across many schools, subjects, regions, and years.
Raw result files make it difficult to answer practical questions quickly:

- Is national performance improving or declining?
- Which regions, schools, and subjects require support?
- Is a selected school improving relative to its region?
- Which changes are persistent rather than one-year fluctuations?
- What direction might performance take if recent patterns continue?

This project converts the historical records into a consistent analytical
workspace while preserving the original production values.

## Objectives

1. Combine and validate national CSEE school and subject records.
2. Present understandable national, regional, school, and subject indicators.
3. Calculate candidate-weighted pass rates and consistent NECTA GPA summaries.
4. Identify strong performance, weak performance, risk, improvement, and
   decline.
5. Compare forecasting approaches using a held-out examination year.
6. Communicate findings through responsive charts, tables, and plain-language
   interpretations.
7. Provide reproducible tests and change evidence for final-year evaluation.
8. Compare configurable 2032 examination-demand scenarios without presenting
   them as predictions or confirmed policy outcomes.

## Data Scope

- Examination: NECTA CSEE
- Geography: all 31 named Tanzania CSEE regions
- Period: 2016-2025
- School dataset: 51,236 rows
- Subject dataset: 522,265 rows
- Main files:
  - `school_combined_2016_2025_national.csv`
  - `subject_combined_2016_2025_national.csv`

The school dataset contains 38 `UNKNOWN` region rows: 8 in 2016, 5 in 2017,
13 in 2018, and 12 in 2019. The subject dataset contains no `UNKNOWN` region
rows. The values originate from the scraper fallback when a region could not
be extracted.

These rows remain in production data for auditability but are excluded from
public regional filters and charts. They are not deleted or assigned without
an authoritative source.

## Methodology

### Data Loading And Validation

`data_loader.py` reads the two national CSV files using explicit text data
types, validates required columns, converts numeric fields safely, and
normalizes region labels. Missing, empty, malformed, wrongly encoded, or
schema-incomplete files produce controlled dashboard messages.

### Calculations

- Lower NECTA GPA indicates stronger performance.
- Existing GPA values are analyzed as supplied and are never rewritten.
- School and subject pass rates use aggregate passed and sat candidate counts.
  Candidate weighting prevents small schools from influencing regional or
  national results as strongly as large schools.
- Rankings use GPA first and pass rate as supporting evidence.
- Improvement logic reverses GPA change because a falling GPA is positive.
- Division 0, attendance, momentum, and regional gaps provide additional
  decision-support context.

### Analysis And Storytelling

Major charts are followed by concise interpretations that explain:

- trend direction;
- latest performance;
- comparison spread;
- risk or intervention significance; and
- an appropriate planning response.

English and Kiswahili interpretation controls are available in the top
navigation.

## Dashboard Features

### Dashboard

Answers national and regional questions:

- What is the current performance level?
- Is performance improving or declining?
- Which regions and schools need attention?
- What do the next two years suggest?

The executive-summary comparison remains countrywide when a region is selected.
Regional filters affect the detailed charts rather than changing the national
reference point.

### School

Provides school search, latest profile, historical GPA and pass-rate trends,
subject strengths and weaknesses, regional benchmarking, school comparison,
division outcomes, and two-year planning forecasts.

### Subject

Identifies strong and weak subjects, candidate outcomes, historical change,
year-over-year movement, and subject forecasts for national or school-level
filters.

### Rankings

Shows top, bottom, improving, and declining school and subject groups. Ranking
views are intended to support investigation, not to replace contextual school
evaluation.

### 2032 Policy Planning

Provides Conservative (+10%), Moderate (+25%), and High (+40%) candidate-growth
scenarios. The page compares projected examination demand, normalized demand
pressure, and changes to school and regional intervention priority.

All future values on this page are synthetic hypothetical scenario estimates.
They remain separate from observed data and model training inputs.

## Forecasting Approach

The model workflow compares:

- Baseline Linear Regression
- Random Forest
- XGBoost
- LSTM, when PyTorch and sufficient sequences are available

Models are evaluated on the latest holdout year using MAE, RMSE, R2, and MAPE.
The primary selection rule is lowest RMSE, with MAE and MAPE checks and a
simpler-model preference when RMSE is within 3% of the best result.

Current selected models:

- GPA: Baseline Linear Regression, RMSE 0.2662
- Pass Rate: Random Forest, RMSE 7.1871

Saved artifacts are loaded from `model_artifacts/`. Training runs only after
the user explicitly selects `Refresh ML models`.

Forecast charts use:

- solid lines for actual results;
- dotted or dashed lines for forecasts; and
- the same color for each actual/forecast series.

Forecasts are planning estimates based on historical patterns. They are not
official NECTA predictions and should not replace academic judgment.

## Key Findings

The following reproducible observations come from the current saved data and
artifacts:

- In 2025, 555,562 candidates sat and 526,577 passed, giving a
  candidate-weighted pass rate of approximately 94.78%.
- The mean school GPA for valid 2025 school records was approximately 3.41.
- Arusha had the strongest 2025 regional mean GPA at approximately 3.11.
- Kusini Pemba had the weakest 2025 regional mean GPA at approximately 3.83.
- Food and Human Nutrition was the strongest 2025 subject by mean subject GPA
  at approximately 1.75, with a 99.96% weighted pass rate.
- Basic Mathematics was the weakest 2025 subject by mean subject GPA at
  approximately 4.40, with a 26.42% weighted pass rate.
- The saved all-region GPA outlook averages approximately 3.40 in 2026 and
  3.33 in 2027. Because lower GPA is stronger, this suggests gradual
  improvement if recent patterns continue.
- The saved all-region pass-rate outlook remains broadly stable at
  approximately 94.63% in 2026 and 94.69% in 2027.

These findings are descriptive and model-based evidence, not causal claims.

## Folder Structure

```text
Analysis&Dashboard/
|-- app.py                         # Main Streamlit entry point
|-- data_loader.py                 # CSV loading, validation, normalization
|-- filters.py                     # Region, year, school, subject filters
|-- metrics.py                     # KPIs, weighted rates, rankings
|-- charts.py                      # Shared Plotly transformations and layout
|-- insights.py                    # Narrative and policy insight logic
|-- styles.py                      # Responsive CSS and UI components
|-- model_artifacts.py             # Validated saved-artifact loading
|-- ml_models.py                   # Training, comparison, forecasting, output
|-- analysis.py                    # Offline analytical CSV generation
|-- priority_engine.py             # School and regional intervention priority
|-- risk_engine.py                 # Composite school and regional risk
|-- intervention_engine.py         # Assumption-labelled recommendations
|-- build_decision_artifacts.py    # Explicit offline artifact generation
|-- decision_artifacts.py          # Validated decision-artifact loading
|-- decision_ui.py                 # Native decision cards and tables
|-- policy_config.py               # Scenario definitions and artifact names
|-- policy_planning_2032.py        # Offline scenario calculation engine
|-- build_policy_artifacts.py      # Explicit policy artifact generation
|-- policy_artifacts.py            # Validated synthetic artifact loading
|-- ARCHITECTURE.md                # Runtime and artifact architecture
|-- METHODOLOGY.md                 # Scenario methodology and limitations
|-- pages/
|   |-- dashboard.py              # National and regional overview
|   |-- school.py                 # School performance workspace
|   |-- subject.py                # Subject performance workspace
|   |-- rankings.py               # Performance and momentum rankings
|   `-- policy_planning.py        # 2032 scenario-planning page
|-- model_artifacts/               # Metrics, metadata, predictions, forecasts
|-- decision_artifacts/            # Priority, risk, recommendation, manifest
|-- model_visualizations/          # Saved model evaluation figures
|-- tests/run_dashboard_tests.py   # Automated test runner
|-- .streamlit/config.toml         # Streamlit configuration
|-- requirements.txt               # Python dependencies
|-- testing_documentation.txt      # test evidence

## Installation

The verified environment uses Python 3.13.11. 

```powershell
pip install -r requirements.txt
```

## Running The Dashboard

```powershell
streamlit run app.py
```

`app.py` is the only production dashboard entry point.

## Offline Decision Artifacts

Priority, risk, and intervention outputs are generated explicitly outside the
normal Streamlit import path:

```powershell
 build_decision_artifacts.py
```

The builder reads the validated national CSVs and writes versioned outputs to
`decision_artifacts/`. Dashboard pages only load these saved files. They do not
train models, calculate SHAP values, or generate simulations during imports.

The Priority Index combines current severity (50%), recent decline (30%), and
peer recoverability (20%). The Risk Score combines pass-rate decline (40%),
subject failure (30%), and trend instability (30%).

Intervention improvement ranges are labelled as assumption-based planning
scenario estimates. They are not measured, causal, guaranteed, or official
outcomes. Real-derived recommendation rows use `data_origin=observed-derived`.
Any future simulated outcomes must remain in separate artifacts and use
`data_origin=synthetic`.

## Offline 2032 Policy Artifacts

Generate the three scenarios explicitly:

```powershell
 build_policy_artifacts.py
```

The process writes four files to `decision_artifacts/`:

- `2032_policy_summary.csv`
- `2032_region_impacts.csv`
- `2032_school_impacts.csv`
- `2032_priority_shift.csv`

Projected candidates equal the latest observed candidate baseline multiplied by
the selected growth factor. Demand pressure compares projected candidates with
the historical annual average on a fixed 0-100 scale. Future priority combines
risk (40%), current priority (40%), and demand pressure (20%).

The Streamlit page only loads these validated files. It does not generate
scenarios during page imports. See `METHODOLOGY.md` and `ARCHITECTURE.md` for
the complete research and software design.

## Running Tests

```powershell
tests\run_dashboard_tests.py
```

The runner covers Functional, Integration, User Interface, Error Handling, and
Performance testing. User Acceptance Testing is intentionally excluded.
Results are written to `testing_documentation.txt`.

## Limitations
- Pass-rate model performance is weaker than GPA model performance and should be interpreted cautiously.
- Intervention ranges are planning assumptions and require stakeholder or experimental validation before operational use.
- The 2032 simulator applies national growth assumptions and does not represent confirmed local enrollment trajectories.
- Scenario outputs support investigation and planning; they are not official results or automatic allocation decisions.

## Future Improvements
- Add causal or explanatory research for regional and subject performance gaps.
- Add accessible downloadable reports for school and policy users.
- Add localized scenario growth assumptions when authoritative demographic evidence becomes available.