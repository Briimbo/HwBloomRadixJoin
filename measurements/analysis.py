"""Performs analysis for evaluating the BRJ. Generates various figures tables for evaluation chapter
"""
import os
import re

import matplotlib
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

enable_titles = True

path = os.path.dirname(os.path.abspath(__file__))
result_path = f"{path}/data"
result_path_pkl = f"{result_path}/pkl"
result_path_md = f"{result_path}/md"
plot_path = f"{path}/plots"
colors = ["r", "g", "b", "c", "m", "y", "k"]
linestyles = ["-", "--", "-.", ":"]
platforms = ["gondor", "celebrimbor", "isengard", "mittalmar", "forostar"]
cache_size_bits = (
    40 * 8 * 1024 * 1024
)  # size in bits to categorize problem sizes, approx. common cache size


perf_counters = [
    "cycles",
    "instructions",
    "cycle_activity.stalls_l1d_miss",
    "cycle_activity.stalls_l2_miss",
    "cycle_activity.stalls_l3_miss",
    "cycle_activity.stalls_mem_any",
    "dTLB-load-misses",
    "mem_inst_retired.stlb_miss_loads",
    "L1-dcache-load-misses",
    "l2_rqsts.miss",
    "LLC-load-misses",
]


def where_equals(data: pd.DataFrame, item, columns: "list[str]" = None) -> pd.Series:
    if columns == None:
        columns = [x for x in dict(item).keys()]
    mask = True
    for col in columns:
        mask &= data[col] == item[col]
    return data[mask]


def add_cache_usage(data: pd.DataFrame, cache_size_bits: int):
    data["cache-usage"] = data.apply(
        lambda row: get_required_space(row, cache_size_bits), axis=1
    )


def add_fpr(data: pd.DataFrame):
    data["fpr_emp"] = (
        (data["filtered"] - data["s-sel"] * data["s-size"])
        / ((1 - data["s-sel"]) * data["s-size"])
        * 100,
    )[0]
    data["fpr_theo"] = (
        (1 - (1 - 1 / data["bloom-size"]) ** (data["bloom-hashes"] * data["r-size"]))
        ** data["bloom-hashes"]
        * 100,
    )[0]


def add_s_r_ratio(data: pd.DataFrame):
    data["s-r-ratio"] = (data["s-size"] / data["r-size"]).astype("int")


def add_speedup(data: pd.DataFrame):
    groups = data.groupby(
        by=[
            "r-size",
            "s-size",
            "s-sel",
            "bloom-size",
            "bloom-filter",
            "bloom-hashes",
            "cpu-mapping",
        ]
    )

    for _, group in groups:
        min_threaded = group["nthreads"].idxmin()
        data.loc[group.index, "speedup"] = (
            group.loc[min_threaded]["nsec-per-tuple"] / group["nsec-per-tuple"]
        )


def set_cpu_mapping_strings(data: pd.DataFrame):
    """Prettify CPU mapping strings to be displayed in figure

    Args:
        data (pd.DataFrame): data to preprocess
    """
    data["cpu-mapping"].replace(
        ["single", "hypthr", "numa", "all"],
        ["Single", "SMT", "NUMA", "All"],
        inplace=True,
    )


def get_required_space(item, cache_size_bits: int):
    tuple_size = 8 * 8
    if item["bloom-filter"] == "no":
        return (
            "L"
            if (item["r-size"] + item["s-size"]) * tuple_size > cache_size_bits
            else "S"
        )
    if item["bloom-size"] > cache_size_bits:
        return "L"
    if (
        item["bloom-size"] + item["r-size"] * tuple_size + item["s-size"] * tuple_size
        > cache_size_bits
    ):
        return "M"

    return "S"


def bloom_filter_fpr(data: pd.DataFrame):
    """Compares the theoretical FPR to the empirical FPR.
    Ideally, both FPRs always deviate only slightly.
    First, this function computes the mean, median, standard deviation and max. abs. difference
    of the deviation between empiricial and theoretical FPR.
    The deviation is computed by |emp - theo| / theo.
    Second, this function plots a comparison between empricial and theoretical FPR for the largest data class.

    Args:
        data (pd.DataFrame): data to compute the FPR on
    """
    subset = data.drop_duplicates(
        subset=[
            "s-sel",
            "r-size",
            "s-size",
            "bloom-filter",
            "bloom-size",
            "bloom-hashes",
        ]
    )
    subset = subset[subset["bloom-filter"] != "no"]
    subset["fpr_deviation"] = (
        (subset["fpr_emp"] - subset["fpr_theo"]).abs() / subset["fpr_theo"] * 100
    )

    for bloom_filter in ["basic", "blocked"]:
        type_set = subset[subset["bloom-filter"] == bloom_filter]
        median = type_set["fpr_deviation"].median()
        mean = type_set["fpr_deviation"].mean()
        standard_deviation = type_set["fpr_deviation"].std()
        max_absolute = (type_set["fpr_emp"] - type_set["fpr_theo"]).abs().max()
        print(
            f"FPR Deviation {bloom_filter}:\t Median = {median:.4f}%\tMean = {mean:.4f}%\t\tStandard Deviation = {standard_deviation:.4f}%\tMax abs. difference = {max_absolute:.4f}%"
        )

    print(f"Max deviation {(subset['fpr_deviation'] * subset['fpr_theo']).max():.4f}")

    max_s = subset["s-size"].max()
    maxidx = subset[subset["s-size"] == max_s]["bloom-hashes"].idxmax()
    max = subset.loc[maxidx]
    plot_data: pd.Series = where_equals(
        subset,
        max,
        [
            "s-sel",
            "r-size",
            "s-size",
            "bloom-size",
        ],
    )
    plot_fpr(plot_data)


def plot_fpr(data: pd.DataFrame):
    """Plots the theoretical and empirical FPR against the number of bits set per item in the filter.

    Args:
        data (pd.DataFrame): data to plot, needs columns bloom-hashes, fpr_emp, fpr_theo
        and s-sel, r-size, s-size, bloom-size for the title
    """
    data = data.astype({"bloom-hashes": "int64"})
    data_emp: pd.DataFrame = data[["bloom-hashes", "fpr_emp"]].copy()
    data_emp["FPR"] = data_emp["fpr_emp"]
    data_emp["FPR type"] = "empirical"
    data_theo = data[["bloom-hashes", "fpr_theo"]].copy()
    data_theo["FPR"] = data_theo["fpr_theo"]
    data_theo["FPR type"] = "theoretical"

    preprocessed: pd.DataFrame = pd.concat([data_emp, data_theo], ignore_index=True)

    ax = preprocessed.pivot(
        index="bloom-hashes", columns="FPR type", values="FPR"
    ).plot(kind="bar", rot=0)

    for i, bar in enumerate(ax.patches):
        bar.set_hatch("///" if i >= data.shape[0] else "\\\\\\")
        bar.set_edgecolor("k")

    ax.get_legend().set_title(None)
    h = ax.get_legend().legend_handles
    h[0].set_edgecolor("k")
    h[0].set_hatch("\\\\\\")
    h[1].set_edgecolor("k")
    h[1].set_hatch("///")

    e = data.iloc[0]
    plt.xlabel("k")
    plt.ylabel("FPR [%]")
    set_title(
        f"Theoretical vs. Empirical FPR\nfor m = {int(e['bloom-size'])/(8*1024*1024):g} MiB, $|$R$|$ = {e['r-size']}, $|$S$|$ = {e['s-size']}, q = {e['s-sel']}"
    )


def plot_fpr_from_fort(filename: str):
    """This function prints a graph from the test results that can be
    obtained with the ./unittests 2 [...] call. Note that it requires manual preprocessing to match the expected input format, i.e.:
    - replace '+' with '|'
    - remove '%'
    - let every cell contain data, i.e., copy values to empty rows below
    For details, see the original bloom_filter_fpr_orig.txt and the modifications in bloom_filter_fpr.txt


    Args:
        filename (str): _description_
    """
    path = f"{result_path}/{filename}"

    # validate that manual preprocessing has been performed
    with open(path) as f:
        lines = f.read()
        if re.search("\+|%|(?:\|[^\S\r\n]+\|)", lines) is not None:
            print(
                "Please perform the required manual preprocessing before calling this function"
            )
            return

    tab = pd.read_table(
        filepath_or_buffer=path,
        delimiter="\s*\|\s*",
        index_col=False,
        engine="python",
        header=0,
        skiprows=[0, 2],
    ).iloc[:-1, 1:-1]
    tab["type"] = tab["bloom-filter"]

    data_theo = tab[tab["type"] == "basic"][["bloom-hashes", "fpr_theo", "type"]].copy()
    data_basic = tab[tab["type"] == "basic"][["bloom-hashes", "fpr_emp", "type"]].copy()
    data_blocked = tab[tab["type"] == "blocked"][
        ["bloom-hashes", "fpr_emp", "type"]
    ].copy()
    data_theo["type"] = "theoretical"

    for data in [data_basic, data_blocked, data_theo]:
        data["FPR"] = data.iloc[:, 1]

    data = pd.concat([data_basic, data_theo, data_blocked], ignore_index=True).astype(
        {"FPR": "float", "bloom-hashes": "int"}
    )
    data = data.pivot(index="bloom-hashes", columns="type", values="FPR")
    data.insert(1, "theoretical", data.pop("theoretical"))
    ax = data.plot(kind="bar", rot=0, width=0.6)

    for i, bar in enumerate(ax.patches):
        type = int(i / data_theo.shape[0])
        if type == 0:
            bar.set_hatch("///")
        elif type == 2:
            bar.set_hatch("\\\\\\")
        bar.set_edgecolor("k")

    ax.get_legend().set_title(None)
    h = ax.get_legend().legend_handles
    h[0].set_hatch("///")
    h[0].set_edgecolor("k")
    h[1].set_edgecolor("k")
    h[2].set_hatch("\\\\\\")
    h[2].set_edgecolor("k")

    e = tab.iloc[0]
    plt.xlabel("k")
    plt.ylabel("FPR [%]")
    set_title(
        f"Theoretical vs. Empirical FPR\nfor m = {int(e['bloom-size']) / (8*1024*1024):g} MiB, $|$R$|$ = {e['r-size']}, $|$S$|$ = {e['s-size']}, q=0"
    )


def plot_mapping_size_grid(
    title: str,
    data: pd.DataFrame,
    line_vars: list,
    line_label_template: str,
    x_var: str,
    supxlabel: str,
    y_var="nsec-per-tuple",
    supylabel="ns per tuple",
):
    """Plot the data of a file in a grid with 4 columns and 3 rows.
    There is one row per data size (S, M, L), depending on the cache size.
    There is one row per CPU mapping type (Single, SMT, NUMA, All).
    Each plot contains one line per algorithm, i.e., unfiltered, basic, blocked, each only if present.
    The y-axis shows the nanoseconds per tuple.

    Args:
        title (str): title of the figure
        data (pd.DataFrame): data to plot
        line_vars (list): list of variables for grouping data to a line
        line_label_template (str): template string to be filled with the common group data per line
        x_var (str): Name of the variable in the dataset to be put on the x axis
        supxlabel (str): super xlabel to be passed to matplotlib, represents x_var
        y_var (str, optional): Name of the variable in the dataset to be put on the y axis
        supylabel (str, optional): super ylabel to be passed to matplotlib, represents y_var
    """
    # prerocess
    set_cpu_mapping_strings(data)

    fig = plt.figure(layout="tight")
    legend = []

    mapping_groups = data.groupby(by="cpu-mapping", sort=False)
    for plt_col, (mapping, mapping_group) in enumerate(mapping_groups):
        # Single, SMT, NUMA, All
        size_groups = mapping_group[mapping_group["bloom-filter"] != "no"].groupby(
            by="cache-usage", sort=True
        )

        sharex = None

        for plt_row, (size, size_group) in enumerate(reversed(list(size_groups))):
            # one subplot per mapping/cache usage pair
            ax = plt.subplot(
                len(size_groups),
                len(mapping_groups),
                plt_col + plt_row * len(mapping_groups) + 1,
                sharex=sharex,
            )

            if pd.api.types.is_integer_dtype(data[x_var].dtype):
                ax.xaxis.set_major_locator(MaxNLocator(integer=True))

            # "table" headers
            if plt_row == 0:
                ax.set_title(mapping)
                sharex = ax
            if plt_col == 0:
                ax.set_ylabel(size, rotation=0, labelpad=10)

            # add one line per unique set of values for line_vars
            line_groups = size_group.groupby(by=line_vars, dropna=False)
            for line_idx, (line_values, line_group) in enumerate(line_groups):
                plt.plot(
                    x_var,
                    y_var,
                    data=line_group,
                    linestyle=linestyles[line_idx],
                    color="k",
                )

                # add legend data once the whole figure
                if plt_row == 0 and plt_col == 0:
                    legend += [
                        mlines.Line2D(
                            [],
                            [],
                            color="k",
                            linestyle=linestyles[line_idx],
                            label=line_label_template.format(*line_values),
                        )
                    ]

    set_title(title)
    fig.supxlabel(supxlabel)
    fig.supylabel(supylabel)
    fig.legend(handles=legend, loc="outside upper right")


def plot_threading(data: pd.DataFrame, y_var: str, y_label: str):
    """Plots the number of threads against `y_var` for different
    cache usage and cpu mapping scenarios in a grid.
    This compares the best performing BRJ against the RJ

    Args:
        data (pd.DataFrame): data to plot
        y_var (str): variable name (in data) to put on the y axis
        y_label (str): label for the y axis
    """
    fig = plt.figure(layout="constrained")
    legend = []

    mapping_groups = data.groupby(by="cpu-mapping", sort=False)

    for plt_col, (mapping, mapping_group) in enumerate(mapping_groups):
        # Single, SMT, NUMA, All
        size_groups = mapping_group[mapping_group["bloom-filter"] != "no"].groupby(
            "cache-usage", sort=True
        )

        sharex = None

        for plt_row, (size, size_group) in enumerate(reversed(list(size_groups))):
            # one subplot per mapping/cache usage pair
            ax = plt.subplot(
                len(size_groups),
                len(mapping_groups),
                plt_col + plt_row * len(mapping_groups) + 1,
                sharex=sharex,
            )

            # "table" headers
            if plt_row == 0:
                ax.set_title(mapping)
                sharex = ax
                ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
            if plt_col == 0:
                ax.set_ylabel(size, rotation=0, labelpad=5)

            # only display data for best performing filter configuration
            min_idx = size_group["nsec-per-tuple"].idxmin()

            m, k, r_size, s_size = size_group.loc[min_idx][
                ["bloom-size", "bloom-hashes", "r-size", "s-size"]
            ]

            subdata = size_group[
                (size_group["bloom-size"] == m)
                & (size_group["bloom-hashes"] == k)
                & (size_group["r-size"] == r_size)
                & (size_group["s-size"] == s_size)
            ]

            unfiltered = mapping_group[
                (mapping_group["bloom-filter"] == "no")
                & (mapping_group["r-size"] == r_size)
                & (mapping_group["s-size"] == s_size)
            ]

            # BRJ performance for different threads
            plt.plot(
                "nthreads",
                y_var,
                data=subdata,
                color="r",
            )

            # RJ baseline to beat
            plt.plot(
                "nthreads",
                y_var,
                data=unfiltered,
                color="k",
            )

            plt.ylim(bottom=0)
            plt.xlim(left=0)

            # enable xtick labels only for bottom row
            if plt_row != len(size_groups) - 1:
                plt.setp(ax.get_xticklabels(), visible=False)

    fig.supxlabel("number of threads")
    fig.supylabel(y_label)

    legend += [
        mlines.Line2D([], [], color="k", label="no filter"),
        mlines.Line2D([], [], color="r", label="best bloom filter"),
    ]

    fig.legend(handles=legend, loc="outside upper right")


def plot_fpr_grid(
    title: str,
    data: pd.DataFrame,
    line_vars: list,
    line_label_template: str,
    x_var: str,
    supxlabel: str,
    y_var="nsec-per-tuple",
    supylabel="ns per tuple",
):
    """Plots the `x_var` against the FPR as well as `y_var` for different cache usage and cpu
    mapping scenarios in a grid for an S:R ratio of 8 and the maximum number of threads each.
    This allows to get an overview of the general dependency between FPR and execution time
    but results in a dense plot

    Args:
        title (str): title of the figure
        data (pd.DataFrame): data to plot
        line_vars (list): list of variables for grouping data to a line
        line_label_template (str): template string to be filled with the common group data per line
        x_var (str): Name of the variable in the dataset to be put on the x axis
        supxlabel (str): super xlabel to be passed to matplotlib, represents x_var
        y_var (str, optional): Name of the variable in the dataset to be put on the y axis
        supylabel (str, optional): super ylabel to be passed to matplotlib, represents y_var
    """
    # preprocess
    set_cpu_mapping_strings(data)
    data = data[data["s-size"] == 8 * data["r-size"]]

    fig = plt.figure(layout="constrained")
    legend = []

    mapping_groups = data.groupby(by="cpu-mapping", sort=False)
    for plt_col, (mapping, mapping_group) in enumerate(mapping_groups):
        # Single, SMT, NUMA, All
        size_groups = mapping_group[mapping_group["bloom-filter"] != "no"].groupby(
            by="cache-usage", sort=True
        )

        sharex = None

        for plt_row, (size, size_group) in enumerate(reversed(list(size_groups))):
            size_group = size_group[
                size_group["nthreads"] == size_group["nthreads"].max()
            ]
            # one subplot per mapping/cache usage pair
            ax = plt.subplot(
                len(size_groups),
                len(mapping_groups),
                plt_col + plt_row * len(mapping_groups) + 1,
                sharex=sharex,
            )
            ax2 = ax.twinx()

            if pd.api.types.is_integer_dtype(data[x_var].dtype):
                ax.xaxis.set_major_locator(MaxNLocator(integer=True))

            # "table" headers
            if plt_row == 0:
                ax.set_title(mapping)
                sharex = ax
            if plt_col == 0:
                ax.set_ylabel(size, rotation=0, labelpad=10)

            # add one line per unique set of values for line_vars
            line_groups = size_group.groupby(by=line_vars, dropna=False)
            for line_idx, (line_values, line_group) in enumerate(line_groups):
                ax.plot(
                    x_var,
                    y_var,
                    data=line_group,
                    marker=".",
                    markersize=4,
                    color=colors[line_idx],
                )

                ax2.plot(
                    x_var,
                    "fpr_emp",
                    data=line_group,
                    color=colors[line_idx],
                    linestyle="--",
                )

                # add legend data once the whole figure
                if plt_row == 0 and plt_col == 0:
                    legend += [
                        mlines.Line2D(
                            [],
                            [],
                            marker=".",
                            color=colors[line_idx],
                            label=line_label_template.format(
                                int(line_values[0] / line_group.iloc[0]["r-size"])
                            ),
                        )
                    ]

    set_title(title)
    fig.supxlabel(supxlabel)
    fig.supylabel(supylabel)
    fig.text(
        x=0.97,
        y=0.5,
        s="FPR\n\n\n",
        size=13,
        fontweight="bold",
        rotation=270,
        ha="center",
        va="center",
    )
    fig.legend(handles=legend, loc="outside upper right")


def plot_fpr_effects(data: pd.DataFrame, **kwargs):
    """Plots k against the FPR as well as the per-tuple time for a specific scenario specified by `kwargs`
    `kwargs` should contain 's-sel', 'r-size', 's-size' and 'nthreads'

    Args:
        data (pd.DataFrame): data to plot
    """
    tmp = data.copy()
    tmp["bloom-size"] = tmp["bloom-size"] / (8 * 1024 * 1024)
    tmp = where_equals(tmp, filter)
    plot_single(
        f"FPR and Execution Time for varying k and m\n with q = {kwargs['s-sel']}, $|$R$|$ = {kwargs['r-size']} $|$S$|$ = {kwargs['s-size']}, n = {kwargs['nthreads']}",
        tmp,
        ["bloom-size"],
        "bloom-hashes",
        secondary_y_var="fpr_emp",
        secondary_y_label="FPR [%]",
        x_label="k",
        primary_line_label="m = {0:g} MiB (ns)",
        secondary_line_label="m = {0:g} MiB (FPR)",
    )


def plot_cpu_mappings(data: pd.DataFrame):
    """Plots the performance against the number of threads for different CPU mappings
    and the best performing filter configuration

    Args:
        data (pd.DataFrame): data to plot
    """
    plt.figure(layout="constrained", figsize=[6.4, 3.2])

    mapping_groups = data.groupby(by="cpu-mapping", sort=False)
    for line_idx, (mapping, mapping_group) in enumerate(mapping_groups):
        # only display data for best performing filter configuration
        min_idx = mapping_group[mapping_group["bloom-filter"] != "no"][
            "nsec-per-tuple"
        ].idxmin()

        m, k, r_size, s_size, variant = mapping_group.loc[min_idx][
            ["bloom-size", "bloom-hashes", "r-size", "s-size", "bloom-filter"]
        ]

        subdata = mapping_group[
            (mapping_group["bloom-size"] == m)
            & (mapping_group["bloom-hashes"] == k)
            & (mapping_group["r-size"] == r_size)
            & (mapping_group["s-size"] == s_size)
            & (mapping_group["bloom-filter"] == variant)
        ]

        plt.plot(
            "nthreads",
            "nsec-per-tuple",
            data=subdata,
            linestyle=linestyles[line_idx],
            label=mapping,
            color=colors[line_idx],
        )

    plt.ylim(bottom=0)
    plt.xlim(left=0)

    plt.legend()
    plt.xlabel("number of threads")
    plt.ylabel("ns per tuple")
    set_title(
        "Comparison of CPU mappings\nfor problem size L, q=0.1 and best filter configuration"
    )


def plot_single(
    title: str,
    data: pd.DataFrame,
    line_vars: list,
    x_var: str,
    y_var="nsec-per-tuple",
    secondary_y_var=None,
    x_label=None,
    y_label="ns per tuple",
    secondary_y_label=None,
    primary_line_label="",
    secondary_line_label="",
):
    """Plots a generic graph given the parameters.
    May plot a secondary y axis if the parameters for it are given

    Args:
        title (str): title of the figure
        data (pd.DataFrame): data to plot
        line_vars (list): list of variables for grouping data to a line
        x_var (str): Name of the variable in the dataset to be put on the x axis
        y_var (str, optional): Name of the variable in the dataset to be put on the primary y axis.
        secondary_y_var (_type_, optional): Name of the variable in the dataset to be put on the secondary y axis.
        x_label (_type_, optional): label for the x axis.
        y_label (str, optional): label for the primary y axis.
        secondary_y_label (_type_, optional): label for the secondary y axis.
        primary_line_label (str, optional): legend label template for the primary y variable.
        secondary_line_label (str, optional): legend label template for the secondary y variable.
    """
    lines = data.groupby(line_vars)

    plt.figure(layout="tight")
    plt.ylabel(y_label if y_label is not None else y_var)
    plt.xlabel(x_label if x_label is not None else x_var)
    set_title(title)
    ax: plt.Axes = plt.gca()
    ax2: plt.Axes = ax.twinx()
    if secondary_y_var is not None:
        ax2.set_ylabel(
            secondary_y_label if secondary_y_label is not None else secondary_y_var
        )

    for line_idx, (line_common, line_data) in enumerate(lines):
        ax.plot(
            x_var,
            y_var,
            data=line_data,
            marker=".",
            markersize=4,
            label=primary_line_label.format(*line_common),
            c=colors[line_idx],
        )

        if secondary_y_var is not None:
            ax2.plot(
                x_var,
                secondary_y_var,
                data=line_data,
                marker=".",
                markersize=4,
                label=secondary_line_label.format(*line_common),
                c=colors[line_idx],
                linestyle="--",
            )

    ax.set_ylim(bottom=0)

    h1, l1 = ax.get_legend_handles_labels()
    if secondary_y_var is not None:
        h2, l2 = ax2.get_legend_handles_labels()
        for i, (h, l) in enumerate(zip(h2, l2)):
            h1.insert(i * 2 + 1, h)
            l1.insert(i * 2 + 1, l)

    ax.legend(h1, l1, loc="lower right", borderaxespad=2)


def plot_bars(
    data: pd.DataFrame,
    supxlabel: str,
    row_vars: list,
    row_label_template: str,
    bar_var: str,
    bar_label_template: str,
    index_var: str,
):
    """Plots a grouped bar graph in a grid where each column corresponds to a cpu mapping.
    The variable for the rows are specified by the parameters.
    Only displays data for the maximum number of threads available per mapping

    Args:
        data (pd.DataFrame): data to plot
        supxlabel (str): super xlabel to be passed to matplotlib, represents x_var
        row_vars (list): Name of the variables that determine grouping for the rows
        row_label_template (str): template string to be filled with the common group data per row
        bar_var (str): Name of the variable for which to plot bars
        bar_label_template (str): template string for the legend to be filled with the value of `bar_var`
        index_var (str): Name of the variable to group bars by
    """
    # preprocess
    set_cpu_mapping_strings(data)

    fig = plt.figure(layout="constrained")
    legend = None
    sharey = None

    mapping_groups = data.groupby(by="cpu-mapping", sort=False)
    for plt_col, (mapping, mapping_group) in enumerate(mapping_groups):
        # Single, SMT, NUMA, All
        size_groups = mapping_group.groupby(by=row_vars, sort=True)

        sharex = None

        for plt_row, (size, size_group) in enumerate(reversed(list(size_groups))):
            # only display data for best performing filter configuration and maximum number of threads
            size_group = size_group[
                size_group["nthreads"] == size_group["nthreads"].max()
            ]
            idxs = size_group.groupby(by=[index_var, bar_var])[
                "nsec-per-tuple"
            ].idxmin()
            size_group = size_group.loc[idxs]

            # one subplot per mapping/cache usage pair
            ax = plt.subplot(
                len(size_groups),
                len(mapping_groups),
                plt_col + plt_row * len(mapping_groups) + 1,
                sharex=sharex,
                sharey=sharey,
            )

            if plt_row == 0 and plt_col == 0:
                sharey = ax
            if plt_row == 0:
                ax.set_title(mapping)
                sharex = ax
            if plt_col == 0:
                ax.set_ylabel(row_label_template.format(*size))

            size_group.pivot(
                index=index_var, columns=bar_var, values="nsec-per-tuple"
            ).plot(kind="bar", rot=0, ax=ax, legend=legend is None)

            if legend is None:
                legend = ax.get_legend()

            for i, bar in enumerate(ax.patches):
                bar_type = int(i / size_group[index_var].unique().shape[0])
                if bar_type == 0:
                    bar.set_hatch("///")
                elif bar_type == 2:
                    bar.set_hatch("\\\\\\")
                bar.set_edgecolor("k")

            ax.set_xlabel(None)

    # fix labels
    for ax in fig.axes:
        ax.tick_params(labelleft=True)
        for tick in ax.xaxis.majorTicks:
            tick.label1.set_verticalalignment("bottom")
            tick.set_pad(11)

    # move local legend from first plot to the figure plot and remove the local legend
    handles = legend.legend_handles
    for i, (h, hatch) in enumerate(zip(handles, ["///", None, "\\\\\\"])):
        h.set_hatch(hatch)
        h.set_edgecolor("k")
        h._label = bar_label_template.format(legend.get_texts()[i].get_text())

    fig.legend(handles=handles, loc="outside upper right")
    legend.remove()

    fig.supxlabel(supxlabel)
    fig.supylabel("ns per tuple")


def plot_knights_landing(data: pd.DataFrame):
    """Plots speedup and performance for Knights Landing B (mittalmar) platform

    Args:
        data (pd.DataFrame): data to plot
    """
    fig = plt.figure(layout="constrained", figsize=(6.8, 3.8))
    legend = []

    y_vars = [("nsec-per-tuple", "ns per tuple"), ("speedup", "speedup")]

    mapping_groups = data.groupby(by="cpu-mapping", sort=False)
    for plt_col, (mapping, mapping_group) in enumerate(mapping_groups):
        # Single, All
        sharex = None

        for plt_row, (y_var, y_label) in enumerate(y_vars):
            # one subplot per mapping/y_var pair
            ax = plt.subplot(
                len(y_vars),
                len(mapping_groups),
                plt_col + plt_row * len(mapping_groups) + 1,
                sharex=sharex,
            )

            # "table" headers
            if plt_row == 0:
                ax.set_title(mapping)
                sharex = ax
            if plt_col == 0:
                ax.set_ylabel(y_label, labelpad=5)

            # only display data for best performing filter configuration
            min_idx = mapping_group["nsec-per-tuple"].idxmin()

            m, k, r_size, s_size = mapping_group.loc[min_idx][
                ["bloom-size", "bloom-hashes", "r-size", "s-size"]
            ]

            subdata = mapping_group[
                (mapping_group["bloom-size"] == m)
                & (mapping_group["bloom-hashes"] == k)
                & (mapping_group["r-size"] == r_size)
                & (mapping_group["s-size"] == s_size)
            ]

            unfiltered = mapping_group[
                (mapping_group["bloom-filter"] == "no")
                & (mapping_group["r-size"] == r_size)
                & (mapping_group["s-size"] == s_size)
            ]

            # BRJ performance for different threads
            plt.plot(
                "nthreads",
                y_var,
                data=subdata,
                color="r",
            )

            # RJ baseline to beat
            plt.plot(
                "nthreads",
                y_var,
                data=unfiltered,
                color="k",
            )

            plt.ylim(bottom=0)
            plt.xlim(left=0)

    fig.supxlabel("number of threads")

    legend += [
        mlines.Line2D([], [], color="k", label="no filter"),
        mlines.Line2D([], [], color="r", label="best bloom filter"),
    ]

    fig.legend(handles=legend, loc="outside upper right")
    set_title("Evaluation for varying number of threads\non Knights Landing B")


def brj_superiority(data: pd.DataFrame) -> pd.DataFrame:
    """Computes the fraction of scenarios with superior BRJ performance in cases of optimal configuration per group.
    Groups are identified by unique |R|, |S|, q and CPU mapping.

    Args:
        data (pd.DataFrame): runs to analyze

    Returns:
        pd.DataFrame: dataframe containing the superiority fraction, superiority count and total count per group
    """
    groups = data.groupby(["r-size", "s-size", "s-sel", "cpu-mapping"])
    min_idxs = groups["nsec-per-tuple"].idxmin()
    mins = data.loc[min_idxs]
    superiority_count = mins[mins["bloom-filter"] != "no"].groupby("s-r-ratio").size()
    group_counts = mins.groupby("s-r-ratio").size()
    superiority_frac = superiority_count / group_counts
    all = pd.concat([superiority_frac, superiority_count, group_counts], axis=1).fillna(
        0
    )
    return all


def brj_superiority_scenarios(data: pd.DataFrame) -> pd.DataFrame:
    """Finds all scenarios with superior BRJ performance and returns the best one per group.
    Groups are identified by unique |R|, |S|, q and CPU mapping.

    Args:
        data (pd.DataFrame): runs to analyze

    Returns:
        pd.DataFrame: dataframe containing the superior scenarios
    """
    groups = data.groupby(["r-size", "s-size", "s-sel", "cpu-mapping"])
    min_idxs = groups["nsec-per-tuple"].idxmin()
    mins = data.loc[min_idxs]
    superiorities = mins[mins["bloom-filter"] != "no"]
    return superiorities


def cross_run():
    """Generates a markdown file that compares execution on the different platforms
    in a table, saved in `data/md/cross_run.md`
    """
    platforms = ["gondor", "celebrimbor", "isengard"]
    data = []
    for platform in platforms:
        tmp = read_data(f"cross_run_{platform}")
        tmp["platform"] = platform
        tmp["platform_orig"] = [
            "gondor",
            "gondor",
            "celebrimbor",
            "celebrimbor",
            "isengard",
            "isengard",
            "forostar",
            "forostar",
            "mittalmar",
            "mittalmar",
        ]
        data += [tmp]

    data = pd.concat(data)
    order = {
        "gondor": 0,
        "celebrimbor": 1,
        "isengard": 2,
        "forostar": 3,
        "mittalmar": 4,
    }
    data["platform_n"] = data["platform"].replace(order)
    data["platform_orig_n"] = data["platform_orig"].replace(order)
    grouped = data.sort_values(by=["platform_orig_n", "bloom-filter", "platform_n"])
    grouped = grouped.drop(["platform_n", "platform_orig_n"], axis=1)
    grouped[
        [
            "bloom-filter",
            "platform_orig",
            "platform",
            "nsec-per-tuple",
            "time-usecs",
            *perf_counters,
        ]
    ].to_markdown(f"{result_path_md}/cross_run.md")


def read_data(platform: str) -> pd.DataFrame:
    """read data collected on platform from `data/pkl/<platform>.pkl`

    Args:
        platform (str): platform to read data from

    Returns:
        pd.DataFrame: data of the platform
    """
    data = pd.read_pickle(f"{result_path_pkl}/{platform}.pkl")
    if platform in ["mittalmar", "forostar"]:
        data = data[data["cpu-mapping"] != "hypthr"]

    add_speedup(data)
    add_cache_usage(data, cache_size_bits)
    add_fpr(data)
    add_s_r_ratio(data)

    return data


def savefig(name: str, close=True):
    """Save produces figure to `plots/<name>.pdf` and `plots/<name>.pgf`
    and closes the figure if specified

    Args:
        name (str): output filename
        close (bool, optional): closes the figure if applicable.
    """
    plt.savefig(f"{plot_path}/{name}.pdf")
    plt.savefig(f"{plot_path}/{name}.pgf")
    if close:
        plt.close()


def set_title(title: str):
    """Sets the figure title if titles are enabled

    Args:
        title (str): title of the figure
    """
    if not enable_titles:
        return
    if len(plt.gcf().axes) > 1:
        plt.suptitle(title)
    else:
        plt.title(title)


if __name__ == "__main__":
    enable_titles = True
    matplotlib.use("pgf")
    matplotlib.rcParams.update(
        {
            "pgf.texsystem": "pdflatex",
            "text.usetex": True,
            "pgf.rcfonts": False,
            "font.size": 11,
        }
    )

    os.makedirs(plot_path, exist_ok=True)
    os.makedirs(result_path_md, exist_ok=True)

    ########################
    # generate tables (md)
    ########################
    cross_run()

    for platform in platforms:
        data: pd.DataFrame = pd.read_pickle(
            f"{result_path_pkl}/hash_functions_{platform}.pkl"
        )
        data.to_markdown(f"{result_path_md}/hash_functions_{platform}.md")

    for platform in platforms:
        data: pd.DataFrame = pd.read_pickle(
            f"{result_path_pkl}/single_vs_multi_pass_{platform}.pkl"
        )
        data.to_markdown(f"{result_path_md}/single_vs_multi_pass_{platform}.md")

    for platform in platforms:
        data = read_data(platform)
        superiorities = brj_superiority_scenarios(data)
        superiorities.to_markdown(f"{result_path_md}/superiority_{platform}.md")

    ########################
    # generate figures (md)
    ########################
    plot_fpr_from_fort("bloom_filter_fpr.txt")
    savefig("fpr_unittest")

    data = read_data("gondor")
    bloom_filter_fpr(data)
    savefig(f"fpr_integrated")

    data = read_data("basic_vs_blocked_gondor")
    plot_mapping_size_grid(
        "Comparison of blocked and basic Bloom filter performance\nin different BRJ scenarios for varying k",
        data,
        ["bloom-filter"],
        "{0}",
        "bloom-hashes",
        "k",
    )
    savefig("basic_vs_blocked")

    data = read_data("gondor")
    data = where_equals(data, {"s-sel": 0.01})
    plot_fpr_grid(
        "Comparison for different FPR depending on k and m",
        data,
        ["bloom-size"],
        "c = {0}",
        "bloom-hashes",
        "k",
    )
    savefig("fpr_effects")

    data = read_data("celebrimbor")
    data = data[data["bloom-filter"] != "no"]
    filter = {
        "s-sel": 0.01,
        "cpu-mapping": "single",
        "nthreads": 12,
    }

    for r, s in [(250000, 2000000), (16000000, 128000000), (128000000, 1024000000)]:
        filter["r-size"] = r
        filter["s-size"] = s
        plot_fpr_effects(data, **filter)
        savefig(f"fpr_effects_{s}")

    platforms = ["gondor", "celebrimbor", "isengard", "mittalmar", "forostar"]
    sups = {}
    os.makedirs(f"{plot_path}/ratios", exist_ok=True)
    os.makedirs(f"{plot_path}/selectivity", exist_ok=True)
    for platform in platforms:
        data = read_data(platform)
        data = data[data["nsec-per-tuple"].notnull()]
        sups[platform] = brj_superiority(data)[0]
        for r in data["r-size"].unique():
            plot_bars(
                data[data["r-size"] == r].copy(),
                supxlabel="S:R ratio",
                row_vars=["s-sel"],
                row_label_template="q = {0}",
                bar_var="bloom-filter",
                bar_label_template="{0}",
                index_var="s-r-ratio",
            )
            set_title(
                f"\nPerformance for different S:R ratios \nwith $|$R$|$ = {r} and the best filter configuration"
            )
            savefig(f"ratios/ratios_{platform}_{r}")

            matplotlib.rcParams.update({"font.size": 10})
            plot_bars(
                data[data["r-size"] == r].copy(),
                supxlabel="Filter type",
                row_vars=["s-r-ratio"],
                row_label_template="S:R = {0}",
                bar_var="s-sel",
                bar_label_template="q = {0}",
                index_var="bloom-filter",
            )
            set_title(
                f"\nPerformance for different selectivities\nwith $|$R$|$ = {r} and the best filter configuration"
            )
            savefig(f"selectivity/selectivity_{platform}_{r}")
            matplotlib.rcParams.update({"font.size": 11})

    pd.DataFrame.from_dict(sups).T.to_markdown(
        f"{result_path_md}/brj_superiority_s_r_ratio.md"
    )

    for platform in platforms:
        data = read_data(platform)
        set_cpu_mapping_strings(data)
        data = data[data["s-sel"] == 0.01]

        plot_threading(data, "nsec-per-tuple", "ns per tuple")
        set_title("Performance for varying number of threads\nwith q = 0.01")
        savefig(f"threading_{platform}")

        plot_threading(data, "speedup", "speedup")
        set_title("Speedup for varying number of threads\nwith q = 0.01")
        savefig(f"speedup_{platform}")

        data = data[data["cache-usage"] == "L"]
        plot_cpu_mappings(data)
        savefig(f"cpumapping_{platform}")

    data = read_data("mittalmar")
    set_cpu_mapping_strings(data)
    data = data[(data["s-sel"] == 0.01) & (data["r-size"] == 128000000)]
    plot_knights_landing(data)
    savefig("speedup_performance_mittalmar_L")
