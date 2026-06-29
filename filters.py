"""Reusable, validated filters for dashboard school and subject records."""

ALL_REGIONS_OPTION = "All"


class FilterValidationError(ValueError):
    """Raised when a requested filter cannot be applied to the supplied data."""


def validate_filter_columns(df, required_columns, filter_name):
    """Validate only the columns required by the requested filter operation."""
    missing_columns = sorted(set(required_columns) - set(df.columns))
    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise FilterValidationError(
            f"Cannot apply {filter_name}; missing required columns: {missing_text}"
        )


def region_filter_options(all_regions):
    """Return compact region options with a single All selection."""
    return [ALL_REGIONS_OPTION] + list(all_regions)


def collapsed_region_selection(selected_regions, all_regions, previous_regions=None):
    """Collapse zero or every selected region to the user-friendly All token."""
    selected_regions = list(selected_regions or [])
    previous_regions = list(previous_regions or [])
    region_set = set(all_regions)
    selected_actual_regions = [region for region in selected_regions if region in region_set]

    if not selected_regions or set(selected_actual_regions) == region_set:
        return [ALL_REGIONS_OPTION]

    if ALL_REGIONS_OPTION in selected_regions:
        if ALL_REGIONS_OPTION not in previous_regions:
            return [ALL_REGIONS_OPTION]
        return selected_actual_regions or [ALL_REGIONS_OPTION]

    return selected_actual_regions


def sync_region_multiselect_state(session_state, key, all_regions):
    """Normalize a Streamlit multiselect without displaying all 31 labels."""
    previous_key = f"{key}_previous"
    normalized_regions = collapsed_region_selection(
        session_state.get(key, []),
        all_regions,
        session_state.get(previous_key, []),
    )
    session_state[key] = normalized_regions
    session_state[previous_key] = normalized_regions


def selected_region_values(selected_regions, all_regions):
    """Expand the All token to concrete region values for DataFrame filtering."""
    selected_regions = collapsed_region_selection(selected_regions, all_regions)
    if selected_regions == [ALL_REGIONS_OPTION]:
        return list(all_regions)
    return selected_regions


def filter_school_data(df, regions=None, years=None, school=None, exact_school=False):
    """Filter school rows by region, year/range, and optional school name."""
    filtered = df
    required_columns = set()
    if regions:
        required_columns.add("region")
    if years is not None:
        required_columns.add("year")
    if school:
        required_columns.add("school_name")
    validate_filter_columns(df, required_columns, "school filters")

    if regions:
        filtered = filtered[filtered["region"].isin(regions)]

    if years is not None and "year" in filtered.columns:
        if isinstance(years, tuple):
            filtered = filtered[
                (filtered["year"] >= years[0]) &
                (filtered["year"] <= years[1])
            ]
        else:
            filtered = filtered[filtered["year"] == years]

    if school:
        if exact_school:
            filtered = filtered[filtered["school_name"] == school]
        else:
            filtered = filtered[
                filtered["school_name"].str.contains(school, case=False, na=False, regex=False)
            ]

    return filtered


def filter_subject_data(df, regions=None, years=None, school=None, subject=None, exact_school=False):
    """Filter subject rows by region, year/range, school, and subject."""
    filtered = df
    required_columns = set()
    if regions:
        required_columns.add("region")
    if years is not None:
        required_columns.add("year")
    if school:
        required_columns.add("school_name")
    if subject and subject != "All Subjects":
        required_columns.add("subject_name")
    validate_filter_columns(df, required_columns, "subject filters")

    if regions:
        filtered = filtered[filtered["region"].isin(regions)]

    if years is not None and "year" in filtered.columns:
        if isinstance(years, tuple):
            filtered = filtered[
                (filtered["year"] >= years[0]) &
                (filtered["year"] <= years[1])
            ]
        else:
            filtered = filtered[filtered["year"] == years]

    if school:
        if exact_school:
            filtered = filtered[filtered["school_name"] == school]
        else:
            filtered = filtered[
                filtered["school_name"].str.contains(school, case=False, na=False, regex=False)
            ]

    if subject and subject != "All Subjects":
        filtered = filtered[filtered["subject_name"] == subject]

    return filtered


def resolve_school_name(search_text, all_schools):
    """Resolve a case-insensitive exact or partial school search."""
    if not search_text or not str(search_text).strip():
        return None

    exact_matches = [s for s in all_schools if s.lower() == search_text.strip().lower()]
    if exact_matches:
        return exact_matches[0]

    partial_matches = [s for s in all_schools if search_text.strip().lower() in s.lower()]
    if partial_matches:
        return partial_matches[0]

    return None

