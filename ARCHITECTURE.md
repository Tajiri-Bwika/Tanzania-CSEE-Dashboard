# CSEE Dashboard Architecture

## Application Boundary

`app.py` is the single Streamlit entry point. It loads validated national
datasets, builds shared filter options, renders the responsive top navigation,
and routes to five page modules:

- `pages/dashboard.py`
- `pages/school.py`
- `pages/subject.py`
- `pages/rankings.py`
- `pages/policy_planning.py`

All pages reuse `styles.py`, shared chart helpers, existing cards, tables,
spacing, responsive behavior, and English/Kiswahili controls.

## Data And Artifact Layers

### Observed Data

`data_loader.py` validates and normalizes the combined 2016-2025 school and
subject CSV files. Existing GPA and candidate values are not rewritten.

### Model Artifacts

`model_artifacts.py` loads precomputed evaluation, prediction, and forecast
files from `model_artifacts/`. Training runs only after an explicit user
action.

### Decision Artifacts

The priority, risk, and intervention engines run offline through
`build_decision_artifacts.py`. `decision_artifacts.py` validates and caches the
saved files used by Dashboard, School, and Rankings.

### 2032 Policy Artifacts

`policy_planning_2032.py` contains the scenario calculations.
`build_policy_artifacts.py` is the only normal generation entry point.
It writes four synthetic CSV files to `decision_artifacts/`.

`policy_artifacts.py` validates the files and enforces:

- `data_origin=synthetic`
- `scenario_type=hypothetical_policy_scenario`

`pages/policy_planning.py` imports only the loader. It does not import or run
the simulation engine, model training, or other heavy processing.

## Dependency Flow

```text
Validated school CSV
        |
        +--> Offline priority/risk artifacts
        |             |
        |             v
        +------> policy_planning_2032.py
                      |
                      v
             build_policy_artifacts.py
                      |
                      v
        Four synthetic 2032 CSV artifacts
                      |
                      v
              policy_artifacts.py
                      |
                      v
            pages/policy_planning.py
```

## Runtime Design

Normal Streamlit rendering performs:

1. validated CSV loading;
2. cached artifact loading;
3. lightweight filtering and presentation;
4. Plotly chart and table construction.

Scenario generation remains offline so page navigation stays responsive and
the observed datasets remain separate from hypothetical outputs.

## Error Boundaries

Each artifact loader supports:

- safe mode, returning `None` for a user-facing unavailable state; and
- strict mode, raising a domain-specific error for tests and diagnostics.

Missing or malformed scenario files therefore do not trigger partial
simulation or modify production data.
