from pathlib import Path
import re

import pandas as pd


def parse_naics_patterns(raw):
    if pd.isna(raw):
        return []
    s = str(raw)
    s = re.sub(r"(?i)part of|pt\.?", "", s)
    s = re.sub(r"(?i)exc\..*", "", s)
    patterns = []
    for chunk in s.split(","):
        match = re.match(r"\s*(\d+)", chunk)
        if match:
            patterns.append(match.group(1))
    return patterns


def ind_to_aiie(patterns, aiie_lookup, aiie_keys_longest_first):
    narrow = [
        aiie_lookup[k]
        for p in patterns
        for k in aiie_keys_longest_first
        if k.startswith(p)
    ]
    if narrow:
        return sum(narrow) / len(narrow)
    for p in patterns:
        for k in aiie_keys_longest_first:
            if p.startswith(k):
                return aiie_lookup[k]
    return None


def to_canonical_ind(x, ind_2012_to_2017, ind_2017_to_2022):
    x = ind_2012_to_2017.get(x, x)
    x = ind_2017_to_2022.get(x, x)
    return x


def parse_soc_pattern(raw):
    if pd.isna(raw):
        return ""
    match = re.match(r"^([\d\-]+)", str(raw).strip())
    return match.group(1) if match else ""


def occ_to_aioe(pattern, aioe_lookup, aioe_keys_longest_first):
    if not pattern:
        return None
    narrow = [aioe_lookup[k] for k in aioe_keys_longest_first if k.startswith(pattern)]
    if narrow:
        return sum(narrow) / len(narrow)
    if pattern.endswith("0"):
        broad = pattern[:-1]
        group = [aioe_lookup[k] for k in aioe_keys_longest_first if k.startswith(broad)]
        if group:
            return sum(group) / len(group)
    for k in aioe_keys_longest_first:
        if pattern.startswith(k):
            return aioe_lookup[k]
    return None


def weighted_mean(series, weights):
    import numpy as np

    mask = series.notna() & weights.notna()
    if mask.sum() == 0:
        return np.nan
    return np.average(series[mask], weights=weights[mask])


def weighted_mean_se(series, weights):
    import numpy as np

    mask = series.notna() & weights.notna()
    if mask.sum() == 0:
        return np.nan, np.nan

    values = series[mask].to_numpy(dtype=float)
    w = weights[mask].to_numpy(dtype=float)
    mean = np.average(values, weights=w)

    if len(values) == 1:
        return mean, 0.0

    eff_n = (w.sum() ** 2) / np.square(w).sum()
    weighted_var = np.average((values - mean) ** 2, weights=w)
    se = np.sqrt(weighted_var / eff_n) if eff_n > 0 else np.nan
    return mean, se


def summarize_sample(frame, outcome_cols):
    rows = []
    for col in outcome_cols:
        rows.append(
            {
                "variable": col,
                "mean": frame[col].mean(),
                "std": frame[col].std(),
                "min": frame[col].min(),
                "max": frame[col].max(),
                "missing": frame[col].isna().sum(),
            }
        )
    return pd.DataFrame(rows)


def yearly_group_stats(frame, value_col, weight_col="ASECWT"):
    rows = []
    subset = frame[frame["exposure_group"].isin(["Low exposure", "High exposure"])].copy()
    for (year, group), group_df in subset.groupby(["YEAR", "exposure_group"], observed=True):
        mean, se = weighted_mean_se(group_df[value_col], group_df[weight_col])
        rows.append(
            {
                "YEAR": year,
                "exposure_group": group,
                "mean": mean,
                "se": se,
                "ci_low": mean - 1.96 * se,
                "ci_high": mean + 1.96 * se,
            }
        )
    return pd.DataFrame(rows).sort_values(["exposure_group", "YEAR"]).reset_index(drop=True)


def smooth_segment(x, y):
    import numpy as np
    from statsmodels.nonparametric.smoothers_lowess import lowess

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) <= 2:
        return x, y
    frac = 1.0 if len(x) <= 4 else 0.8
    smoothed = lowess(y, x, frac=frac, return_sorted=True)
    return smoothed[:, 0], smoothed[:, 1]


def save_figure(fig, filename, out_dir=None):
    if out_dir is None:
        out_dir = Path(__file__).resolve().parent / "reports" / "causal_analysis_figures"
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / filename
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Saved {out_path}")


def plot_trends(frame, value_col, title, ylabel, post_start):
    import matplotlib.pyplot as plt

    plot_df = yearly_group_stats(frame, value_col)
    colors = {"Low exposure": "#1f77b4", "High exposure": "#d62728"}
    linestyles = {"Pre": "-", "Post": "--"}

    fig, ax = plt.subplots(figsize=(9, 5))
    for group in ["Low exposure", "High exposure"]:
        group_df = plot_df[plot_df["exposure_group"] == group].sort_values("YEAR")
        ax.errorbar(
            group_df["YEAR"],
            group_df["mean"],
            yerr=1.96 * group_df["se"],
            fmt="o",
            capsize=3,
            color=colors[group],
            alpha=0.8,
        )

        for period_name, period_mask in {
            "Pre": group_df["YEAR"] < post_start,
            "Post": group_df["YEAR"] >= post_start,
        }.items():
            segment = group_df.loc[period_mask]
            if segment.empty:
                continue
            xs, ys = smooth_segment(segment["YEAR"], segment["mean"])
            _, lower = smooth_segment(segment["YEAR"], segment["ci_low"])
            _, upper = smooth_segment(segment["YEAR"], segment["ci_high"])
            ax.plot(
                xs,
                ys,
                color=colors[group],
                linestyle=linestyles[period_name],
                linewidth=2.4,
                label=f"{group} ({period_name})",
            )
            ax.fill_between(xs, lower, upper, color=colors[group], alpha=0.12)

    ax.axvline(post_start - 0.5, color="black", linestyle=":", linewidth=1.2)
    ax.set_title(title)
    ax.set_xlabel("Survey year")
    ax.set_ylabel(ylabel)
    ax.legend(ncol=2, frameon=True)
    return fig, ax, plot_df


def run_wls(formula, frame, cluster_col="IND_2022", weight_col="ASECWT"):
    import statsmodels.formula.api as smf

    model = smf.wls(formula=formula, data=frame, weights=frame[weight_col])
    return model.fit(cov_type="cluster", cov_kwds={"groups": frame[cluster_col]})


def coef_table(result, keep=None):
    table = pd.DataFrame(
        {
            "coef": result.params,
            "std_err": result.bse,
            "ci_low": result.params - 1.96 * result.bse,
            "ci_high": result.params + 1.96 * result.bse,
            "p_value": result.pvalues,
        }
    )
    if keep is not None:
        mask = table.index.to_series().str.contains(keep, regex=True)
        table = table[mask]
    return table


def wald_difference_test(result, positive_term, negative_term, comparison_label):
    import numpy as np

    param_names = list(result.params.index)
    restriction = np.zeros((1, len(param_names)))
    restriction[0, param_names.index(positive_term)] = 1
    restriction[0, param_names.index(negative_term)] = -1
    test = result.wald_test(restriction, scalar=True)
    diff = float(result.params[positive_term] - result.params[negative_term])
    cov = result.cov_params().to_numpy()
    diff_var = float((restriction @ cov @ restriction.T).item())
    diff_se = np.sqrt(diff_var)
    return pd.DataFrame(
        {
            "comparison": [comparison_label],
            "difference": [diff],
            "std_err": [diff_se],
            "ci_low": [diff - 1.96 * diff_se],
            "ci_high": [diff + 1.96 * diff_se],
            "wald_stat": [float(test.statistic)],
            "p_value": [float(test.pvalue)],
        }
    )


def fit_event_study(frame, outcome, reference_year=2022):
    formula = (
        f"{outcome} ~ C(YEAR, Treatment(reference={reference_year}))*AIIE + "
        "AGE + C(IND_2022) + C(EDUC)"
    )
    return run_wls(formula, frame)


def extract_event_study_table(result, reference_year=2022):
    rows = []
    prefix = f"C(YEAR, Treatment(reference={reference_year}))"
    for name, coef in result.params.items():
        if not name.startswith(prefix) or ":AIIE" not in name:
            continue
        year = int(name.split("[T.")[1].split("]")[0])
        se = result.bse[name]
        rows.append(
            {
                "term": name,
                "year": year,
                "coef": coef,
                "std_err": se,
                "ci_low": coef - 1.96 * se,
                "ci_high": coef + 1.96 * se,
                "p_value": result.pvalues[name],
            }
        )
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def joint_zero_test(result, terms):
    import numpy as np

    if len(terms) == 0:
        return pd.DataFrame({"n_terms": [0], "wald_stat": [np.nan], "p_value": [np.nan]})
    param_names = list(result.params.index)
    restriction = np.zeros((len(terms), len(param_names)))
    for i, term in enumerate(terms):
        restriction[i, param_names.index(term)] = 1
    test = result.wald_test(restriction, scalar=True)
    return pd.DataFrame(
        {
            "n_terms": [len(terms)],
            "wald_stat": [float(test.statistic)],
            "p_value": [float(test.pvalue)],
        }
    )


def plot_event_study_on_axis(table, ax, title, post_start):
    ax.errorbar(
        table["year"],
        table["coef"],
        yerr=1.96 * table["std_err"],
        fmt="o-",
        capsize=4,
    )
    ax.axhline(0, color="black", linewidth=1)
    ax.axvline(post_start - 0.5, color="gray", linestyle="--", alpha=0.8)
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel("Coefficient on year × AIIE")


def plot_event_study(table, title, post_start):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5))
    plot_event_study_on_axis(table, ax, title, post_start)
    return fig, ax
