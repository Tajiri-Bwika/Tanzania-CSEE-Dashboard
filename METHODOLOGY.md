# 2032 Policy Planning Methodology

## Purpose

The 2032 Policy Planning Simulator examines how alternative enrollment-growth
assumptions could change examination demand and intervention priorities. It is
a scenario-planning tool, not a prediction of future results or government
policy.

## Data Sources

The offline engine uses only validated project evidence:

- historical school candidate counts from 2016-2025;
- latest available school and regional candidate counts;
- saved school and regional risk scores; and
- saved school and regional priority scores.

The scenario files are stored separately from observed datasets and model
training inputs.

## Scenarios

| Scenario | Name | Growth assumption |
| --- | --- | ---: |
| A | Conservative Growth | +10% |
| B | Moderate Growth | +25% |
| C | High Growth | +40% |

One scenario is active at a time in the Streamlit page.

## Baseline Candidates

For each school, the baseline is its latest observed number of candidates who
sat the examination:

```text
current_candidates = latest observed sat candidates
```

The regional baseline is the sum of the latest school-level baseline records
within each region.

## Projected Candidates

```text
projected_candidates =
    current_candidates * (1 + scenario_growth_rate)
```

These values are synthetic scenario estimates for 2032.

## Demand Pressure Index

Historical demand is represented by the mean annual candidate count available
for each school or region:

```text
demand_pressure_ratio =
    projected_candidates / historical_average_candidates
```

The ratio is placed on a fixed 0-100 scale:

```text
demand_pressure_index =
    clip((demand_pressure_ratio / 2.0) * 100, 0, 100)
```

This fixed scale keeps all three scenarios comparable:

- demand equal to the historical average scores 50;
- demand at twice the historical average scores 100; and
- higher values are capped at 100.

Categories:

| Score | Category |
| ---: | --- |
| 0-30 | Low |
| >30-60 | Moderate |
| >60-80 | High |
| >80-100 | Critical |

## Future Priority

The scenario-based priority score combines existing evidence with demand:

```text
future_priority_score =
    (0.40 * risk_score)
    + (0.40 * priority_score)
    + (0.20 * demand_pressure_index)
```

Schools and regions are ranked from highest to lowest score.

```text
rank_change = current_priority_rank - future_priority_rank
```

A positive value means the entity rises to a higher intervention priority
under the selected scenario.

## Outputs

The offline process creates:

- `decision_artifacts/2032_policy_summary.csv`
- `decision_artifacts/2032_region_impacts.csv`
- `decision_artifacts/2032_school_impacts.csv`
- `decision_artifacts/2032_priority_shift.csv`

Every row includes:

```text
data_origin=synthetic
scenario_type=hypothetical_policy_scenario
```

## Assumptions

- Each scenario applies one national growth factor to school baselines.
- Historical annual averages provide the comparison reference.
- Current risk and priority scores remain fixed within a scenario.
- The calculations describe examination demand and planning priority, not
  causal effects.
- Rankings are relative to the other entities in the same scenario.

## Limitations

- Uniform national growth does not represent local demographic variation.
- Schools with shorter histories have less stable historical averages.
- The module does not infer operational requirements from data that the
  project does not contain.
- Scenario scores should guide investigation and staged planning, not automatic
  allocation decisions.
- Outputs are not official NECTA results or confirmed policy outcomes.

## Decision-Support Rationale

The simulator connects candidate growth with existing performance challenges.
This helps decision makers identify where examination demand and intervention
priority may overlap, compare alternative assumptions, and prepare targeted
follow-up questions before a planning cycle.

## Academic Contribution

"A Scenario-Based Educational Policy Planning Framework for Anticipating
Future Examination Demand and Intervention Priorities Using Historical NECTA
Performance Data."
