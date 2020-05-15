"""Module for plotting of the graphs."""
from pathlib import Path
from typing import Dict, List

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.pyplot import figure

absolute_report_directory_path = str(Path(__file__).parent.parent.absolute())


def plot_line_chart(
    time_values: List,
    metric_values: Dict,
    x_label: str,
    y_label: str,
    title: str,
    path: str,
    plugin_logs: List,
):
    """Plot line chart to file."""
    fig = figure(num=None, figsize=(12, 6), dpi=80, facecolor="w", edgecolor="k")
    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]

    maximum_value = np.amax([np.amax(values) for values in metric_values.values()])

    plt.title(f"{title}")
    plt.ticklabel_format(style="plain")
    plt.ylim(bottom=0.0, top=maximum_value * 1.1)

    for (metric_name, values), index in zip(
        metric_values.items(), range(len(metric_values.keys()))
    ):
        plt.plot_date(
            time_values,
            values,
            "-b",
            color=colors[index % len(colors)],
            label=f"{metric_name}",
        )

    ######### Plugin Logs ###### # noqa

    log_color = "lime"
    text_color = "limegreen"

    logs_timestamps = [plugin_log["timestamp"] for plugin_log in plugin_logs]

    plt.plot_date(
        logs_timestamps, np.zeros(len(logs_timestamps)), marker=10, color=log_color
    )

    for plugin_log in plugin_logs:
        plt.annotate(
            str(plugin_log["id"]),
            xy=(mdates.date2num(plugin_log["timestamp"]), 0.02 * maximum_value),
            color=text_color,
        )
        plt.axvline(
            plugin_log["timestamp"],
            color=log_color,
            linestyle="--",
            linewidth=1,
            alpha=0.7,
        )

    #######################

    plt.ylabel(f"{y_label}")
    plt.xlabel(f"{x_label}")
    plt.legend(loc="upper right")

    ####### Statistics ######## # noqa
    rows = [
        ["%.3f" % func(values) for metric, values in metric_values.items()]
        for func in (np.amax, np.mean, np.amin)
    ]
    row_labels = ["MAX", "AVG", "MIN"]
    plt.table(
        cellText=rows,
        rowLabels=row_labels,
        cellLoc="center",
        colLabels=list(metric_values.keys()),
        loc="bottom",
        bbox=[0, -0.29, 1, 0.17],
    )
    plt.subplots_adjust(left=0.2, bottom=0.2)
    ##########################

    plt.savefig(f"{absolute_report_directory_path}/report/{path}{title}.png", dpi=300)
    plt.close(fig)


def plot_bar_chart(
    labels: List,
    metric_values: List,
    x_label: str,
    y_label: str,
    title: str,
    path: str,
    plugin_logs: List,
):
    """Plot line chart to file."""
    max_value = np.amax(metric_values)
    fig = figure(num=None, figsize=(12, 6), dpi=80, facecolor="w", edgecolor="k")
    plt.title(f"{title}")
    plt.ticklabel_format(style="plain")
    plt.xticks(rotation=45, ha="right")
    plt.subplots_adjust(bottom=0.15)
    plt.ylim(bottom=0.0, top=max_value * 1.3)
    plt.bar(labels, metric_values, label=f"{title}")
    for index, value in enumerate(metric_values):
        plt.text(index - 0.25, value + max_value * 0.02, ("%.1f" % value), rotation=45)
    plt.ylabel(f"{y_label}")
    plt.xlabel(f"{x_label}")
    plt.legend()

    plt.savefig(f"{absolute_report_directory_path}/report/{path}{title}.png", dpi=300)
    plt.close(fig)


def plot_plugin_log_table(plugin_logs: List):
    """Plot plugin log table."""
    fig, ax = plt.subplots()

    ax.axis("off")
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    rows = [
        (
            plugin_log["id"],
            plugin_log["timestamp"],
            plugin_log["reporter"],
            plugin_log["level"],
            plugin_log["message"],
        )
        for plugin_log in plugin_logs
    ]
    if len(plugin_logs) > 0:
        colcolor = "turquoise"
        collabel = ("ID", "Timestamp", "Reporter", "Level", "Message")
        table = ax.table(
            cellText=rows,
            colWidths=[0.05, 0.2, 0.1, 0.1, 0.5],
            colColours=[colcolor, colcolor, colcolor, colcolor, colcolor],
            colLabels=collabel,
            loc="center",
            colLoc="center",
        )
        table.scale(1.0, 1.5)

        titel_color = "white"
        column_alignments = ["center", "center", "center", "center", "left"]
        cells = table.properties()["celld"]

        for i in range(5):
            cells[0, i].get_text().set_color(titel_color)
            cells[0, i].set_text_props(fontproperties=FontProperties(weight="bold"))

        for column_index, column_alignment in enumerate(column_alignments):
            for i in range(1, len(plugin_logs) + 1):
                cells[i, column_index]._loc = column_alignment

        plt.savefig(f"{absolute_report_directory_path}/report/plugin_log.png", dpi=300)
    plt.close(fig)
