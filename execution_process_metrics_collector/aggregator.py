#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: GPL-3.0-or-later
# execution-process-metrics-collector, a process tree metrics gatherer.
# Copyright (C) 2025 Barcelona Supercomputing Center, José M. Fernández
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import datetime
import json
import logging
import os.path
import pathlib
import sys

from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from typing import (
        MutableSequence,
        Optional,
        Sequence,
    )

import pandas as pd
import networkx as nx
import matplotlib
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt

from adjustText import adjust_text  # type: ignore[import-untyped]


from .collector import (
    REFERENCE_PID_FILENAME,
    SAMPLING_PERIOD_FILENAME,
    PIDS_FILENAME,
    CPU_DETAILS_FILENAME,
    COMMAND_JSON_FILENAME_TEMPLATE,
    METRICS_CSV_FILENAME_TEMPLATE,
)

logger = logging.getLogger(__name__)

GROUPED_BY_COLOR = "#ff6e00"
OTHER_COLOR = "#f5e050"


def process_command(command: "Sequence[str]") -> "str":
    basename_command = os.path.basename(command[0])
    retlabel = basename_command
    if basename_command == "python":
        for i_token, token in enumerate(command[1:], 1):
            if not token.startswith("-"):
                retlabel += "\n" + os.path.basename(token)
                if retlabel == "cwltool":
                    retlabel += " " + command[i_token + 1]
                break
    elif basename_command == "java":
        for token in command[1:]:
            if not token.startswith("-"):
                retlabel += "\n" + os.path.basename(token)
                break
    elif basename_command == "docker":
        for token in command[1:]:
            if token == "stats":
                retlabel = "docker stats"
                break
            elif not token.startswith("-") and token != "run":
                retlabel = "docker run\n" + token
                break

    return retlabel


def draw_tree(
    pids: "pd.DataFrame",
    pids_tree: "nx.DiGraph[str]",
    outputs_dir: "pathlib.Path",
    group_by_process_name: "Optional[str]",
    width: "float" = 16.6,
    height: "float" = 11.7,
    dpi: "int" = 300,
    font_size: "float" = 10,
) -> "None":
    rc_context = {
        "font.size": font_size * 1.7,  # controls default text sizes
        "axes.titlesize": font_size * 1.5,  # fontsize of the axes title
        "axes.labelsize": font_size * 1.5,  # fontsize of the x and y labels
        "xtick.labelsize": font_size * 1.2,  # fontsize of the tick labels
        "ytick.labelsize": font_size * 1.2,  # fontsize of the tick labels
        "legend.fontsize": font_size,  # legend fontsize
        "figure.titlesize": font_size * 2,  # fontsize of the figure title
    }

    with plt.rc_context(rc_context):
        # Part of this code came from https://networkx.org/documentation/latest/auto_examples/graph/plot_morse_trie.html#sphx-glr-auto-examples-graph-plot-morse-trie-py
        for i, layer in enumerate(nx.topological_generations(pids_tree)):
            for n in layer:
                pids_tree.nodes[n]["layer"] = i
        # pos = nx.multipartite_layout(pids_tree, subset_key="layer", align="horizontal")
        pos = nx.multipartite_layout(pids_tree, subset_key="layer", align="vertical")
        # Flip the layout so the root node is on top
        for k in pos:
            pos[k][-1] *= -1

        # A4 in inches
        # fig = plt.figure(figsize=(11.7,8.3))
        # A3 in inches
        fig = plt.figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        plt.suptitle("Tasks call graph (tree disposition)")
        plt.title("Generated on " + datetime.datetime.now().astimezone().isoformat())
        ax = plt.gca()
        ax.margins(0)
        plt.axis("off")

        if group_by_process_name is not None:
            node_color = list(
                map(
                    lambda command: GROUPED_BY_COLOR
                    if command.startswith(group_by_process_name)
                    else OTHER_COLOR,
                    pids["command"],
                )
            )
        else:
            node_color = None
        nx.draw_networkx(
            pids_tree,
            pos=pos,
            ax=ax,
            with_labels=True,
            labels=dict(zip(pids["node"], pids["command_label"])),
            node_color=node_color,
            # node_size=30,
            font_size=8,
        )

        # Call graph
        matplotlib.use("pdf")
        fig.savefig(outputs_dir / "graph.pdf")

        matplotlib.use("svg")
        fig.savefig(outputs_dir / "graph.svg")

        matplotlib.use("agg")
        fig.savefig(outputs_dir / "graph.png")


def draw_spiral(
    pids: "pd.DataFrame",
    pids_tree: "nx.DiGraph[str]",
    outputs_dir: "pathlib.Path",
    group_by_process_name: "Optional[str]",
    width: "float" = 16.6,
    height: "float" = 11.7,
    dpi: "int" = 300,
    font_size: "float" = 10,
) -> "None":
    rc_context = {
        "font.size": font_size * 1.7,  # controls default text sizes
        "axes.titlesize": font_size * 1.5,  # fontsize of the axes title
        "axes.labelsize": font_size * 1.5,  # fontsize of the x and y labels
        "xtick.labelsize": font_size * 1.2,  # fontsize of the tick labels
        "ytick.labelsize": font_size * 1.2,  # fontsize of the tick labels
        "legend.fontsize": font_size,  # legend fontsize
        "figure.titlesize": font_size * 2,  # fontsize of the figure title
    }

    with plt.rc_context(rc_context):
        pos = nx.spiral_layout(pids_tree, resolution=0.5, equidistant=True)

        # A4 in inches
        # fig = plt.figure(figsize=(11.7,8.3))
        # A3 in inches
        fig = plt.figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        plt.suptitle("Tasks call graph (spiral disposition)")
        plt.title("Generated on " + datetime.datetime.now().astimezone().isoformat())
        ax = plt.gca()
        ax.margins(0)
        plt.axis("off")

        if group_by_process_name is not None:
            node_color = list(
                map(
                    lambda command: GROUPED_BY_COLOR
                    if command.startswith(group_by_process_name)
                    else OTHER_COLOR,
                    pids["command"],
                )
            )
        else:
            node_color = None
        nx.draw_networkx(
            pids_tree,
            pos=pos,
            ax=ax,
            with_labels=True,
            labels=dict(zip(pids["node"], pids["command_label"])),
            node_color=node_color,
            # node_size=30,
            # font_size=8,
        )

        # Call graph
        matplotlib.use("pdf")
        fig.savefig(outputs_dir / "spiral-graph.pdf")

        matplotlib.use("svg")
        fig.savefig(outputs_dir / "spiral-graph.svg")

        matplotlib.use("agg")
        fig.savefig(outputs_dir / "spiral-graph.png")


def timedelta_full_formatter(td: "pd.Timedelta") -> "str":
    return str(td)


def timedelta_noday_formatter(td: "pd.Timedelta") -> "str":
    if td.components.days > 0:
        return timedelta_full_formatter(td)

    if td.components.milliseconds > 0:
        return "{0:02d}:{1:02d}:{2:02d}.{3:03d}".format(
            td.components.hours,
            td.components.minutes,
            td.components.seconds,
            td.components.milliseconds,
        )
    else:
        return "{0:02d}:{1:02d}:{2:02d}".format(
            td.components.hours, td.components.minutes, td.components.seconds
        )


def draw_consumptions_chart(
    node_consumptions: "pd.DataFrame",
    outputs_dir: "pathlib.Path",
    width: "float" = 16.6,
    height: "float" = 11.7,
    dpi: "int" = 300,
    font_size: "float" = 10,
) -> "None":
    # A4 in inches
    # fig = plt.figure(figsize=(11.7,8.3))
    # A3 in inches
    # fig = plt.figure(figsize=(16.6, 11.7), dpi=300, tight_layout=True)

    rc_context = {
        "font.size": font_size * 1.7,  # controls default text sizes
        "axes.titlesize": font_size * 1.5,  # fontsize of the axes title
        "axes.labelsize": font_size * 1.5,  # fontsize of the x and y labels
        "xtick.labelsize": font_size * 1.2,  # fontsize of the tick labels
        "ytick.labelsize": font_size * 1.2,  # fontsize of the tick labels
        "legend.fontsize": font_size,  # legend fontsize
        "figure.titlesize": font_size * 2,  # fontsize of the figure title
    }

    with plt.rc_context(rc_context):
        fig = plt.figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        ax = plt.gca()

        # print(node_consumptions.head())

        title = f"""\
Consumptions and duration
Generated on {datetime.datetime.now().astimezone().isoformat()}\
"""
        axes = node_consumptions.plot.barh(
            x="task",
            y=["joules", "duration"],
            title=title,
            subplots=True,
            sharex=False,
            sharey=True,
            layout=(1, 2),
            ax=ax,
        )  # type: ignore[call-overload]
        # node_consumptions.plot.barh(x="task", y="joules", ax=ax)

        axes[0][1].yaxis.set_major_formatter(
            lambda x, pos: node_consumptions["task"].iloc[x].replace("/", "/\n")
        )
        axes[0][1].xaxis.set_major_formatter(
            lambda x, pos: timedelta_noday_formatter(pd.Timedelta(x))
        )

        labels1 = []
        for i_task, task, joules in zip(
            range(len(node_consumptions)),
            node_consumptions["task"],
            node_consumptions["joules"],
        ):
            label = axes[0][0].text(
                joules, i_task, joules, va="center_baseline", color="black"
            )
            label.set_path_effects(
                [PathEffects.withStroke(linewidth=2, foreground="white")]
            )
            labels1.append(label)
        adjust_text(
            labels1,
            ax=axes[0][0],
            only_move={"text": "x", "static": "x", "explode": "x", "pull": "x"},
        )

        labels2 = []
        for i_task, task, duration in zip(
            range(len(node_consumptions)),
            node_consumptions["task"],
            node_consumptions["duration"],
        ):
            label = axes[0][1].text(
                duration.value,
                i_task,
                timedelta_noday_formatter(duration),
                va="center_baseline",
                color="black",
            )
            label.set_path_effects(
                [PathEffects.withStroke(linewidth=2, foreground="white")]
            )
            labels2.append(label)

        adjust_text(
            labels2,
            ax=axes[0][1],
            only_move={"text": "x", "static": "x", "explode": "x", "pull": "x"},
        )

        # Call graph
        matplotlib.use("pdf")
        fig.savefig(outputs_dir / "consumptions.pdf")

        matplotlib.use("svg")
        fig.savefig(outputs_dir / "consumptions.svg")

        matplotlib.use("agg")
        fig.savefig(outputs_dir / "consumptions.png")


def draw_lollipop_chart(
    node_consumptions: "pd.DataFrame",
    outputs_dir: "pathlib.Path",
    width: "float" = 16.6,
    height: "float" = 11.7,
    dpi: "int" = 300,
    font_size: "float" = 10,
    first_sample_color: "str" = "skyblue",
    last_sample_color: "str" = "lightgreen",
    duration_color: "str" = "grey",
) -> "None":
    rc_context = {
        "font.size": font_size * 1.7,  # controls default text sizes
        "axes.titlesize": font_size * 1.5,  # fontsize of the axes title
        "axes.labelsize": font_size * 1.5,  # fontsize of the x and y labels
        "xtick.labelsize": font_size * 1.2,  # fontsize of the tick labels
        "ytick.labelsize": font_size * 1.2,  # fontsize of the tick labels
        "legend.fontsize": font_size,  # legend fontsize
        "figure.titlesize": font_size * 2,  # fontsize of the figure title
    }

    with plt.rc_context(rc_context):
        fig = plt.figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        ax = plt.gca()

        # Heavily inspired on https://python-graph-gallery.com/184-lollipop-plot-with-2-groups/

        # Reorder the dataframe by the first recorded sample
        ordered_node_consumptions = node_consumptions.sort_values(by="first_sample")
        first_first = ordered_node_consumptions["first_sample"].iloc[0]
        ordered_node_consumptions["first_rel"] = (
            ordered_node_consumptions["first_sample"] - first_first
        ).values.astype("float64")
        ordered_node_consumptions["last_rel"] = (
            ordered_node_consumptions["last_sample"] - first_first
        ).values.astype("float64")
        candle_range = range(0, len(ordered_node_consumptions.index))

        # The horizontal plot is made using the hline function
        ordered_node_consumptions.plot(
            kind="scatter",
            x="first_rel",
            y="task",
            color=first_sample_color,
            alpha=1,
            label="Started",
            ax=ax,
        )
        ordered_node_consumptions.plot(
            kind="scatter",
            x="last_rel",
            y="task",
            color=last_sample_color,
            alpha=1,
            label="Ended",
            ax=ax,
        )

        ax.hlines(
            y=candle_range,
            xmin=ordered_node_consumptions["first_rel"],
            xmax=ordered_node_consumptions["last_rel"],
            color=duration_color,
            alpha=0.4,
            zorder=-1,
        )

        ax.xaxis.set_major_formatter(
            lambda x, pos: timedelta_noday_formatter(pd.Timedelta(x))
        )

        labels = []
        for i_task, first_rel, last_rel, duration in zip(
            range(len(ordered_node_consumptions)),
            ordered_node_consumptions["first_rel"],
            ordered_node_consumptions["last_rel"],
            ordered_node_consumptions["duration"],
        ):
            first_rel_td = pd.Timedelta(first_rel)
            label = ax.text(
                (first_rel_td + duration / 2).value,
                i_task,
                timedelta_noday_formatter(duration),
                ha="center",
                color=duration_color,
                fontsize=font_size,
            )
            labels.append(label)

            label = ax.text(
                first_rel,
                i_task,
                timedelta_noday_formatter(first_rel_td),
                ha="left",
                color=first_sample_color,
                fontsize=font_size,
            )
            labels.append(label)

            label = ax.text(
                last_rel,
                i_task,
                timedelta_noday_formatter(pd.Timedelta(last_rel)),
                ha="right",
                color=last_sample_color,
                fontsize=font_size,
            )
            labels.append(label)

        adjust_text(
            labels,
            ax=ax,
            expand=(1.1, 1.5),
            # arrowprops=dict(arrowstyle=f'->, head_width={font_size}, head_length={font_size}', color='red'),
            arrowprops=dict(arrowstyle="->", color=duration_color),
        )

        # ax.scatter(ordered_node_consumptions['first_sample'], candle_range, color='skyblue', alpha=1, label='Started')
        # ax.scatter(ordered_node_consumptions['last_sample'], candle_range, color='lightgreen', alpha=1 , label='Finished')
        # ax.legend()
        #
        ## Add title and axis names
        # ax.yticks(my_range, ordered_node_consumptions['task'])
        # ax.title("Tasks groups timeline", loc='left')
        # ax.xlabel('Value of the variables')
        # ax.ylabel('Tasks')

        # Call graph
        matplotlib.use("pdf")
        fig.savefig(outputs_dir / "timeline.pdf")

        matplotlib.use("svg")
        fig.savefig(outputs_dir / "timeline.svg")

        matplotlib.use("agg")
        fig.savefig(outputs_dir / "timeline.png")


def metrics_aggregator(
    series_dir: "pathlib.Path",
    outputs_dir: "pathlib.Path",
    tdp_in_w: "float",
    group_by_process_name: "Optional[str]" = None,
) -> "None":
    if not series_dir.is_dir():
        logger.error(f"Path {series_dir.as_posix()} is not a directory")
        raise Exception()

    reference_pid_filename = series_dir / REFERENCE_PID_FILENAME
    if not reference_pid_filename.is_file():
        logger.error(f"Path {reference_pid_filename.as_posix()} is not a filename")
        raise Exception()

    with reference_pid_filename.open(mode="r", encoding="utf-8") as rF:
        reference_pid = float(rF.readline())

    sampling_period_filename = series_dir / SAMPLING_PERIOD_FILENAME
    if not sampling_period_filename.is_file():
        logger.error(f"Path {sampling_period_filename.as_posix()} is not a filename")
        raise Exception()

    with sampling_period_filename.open(mode="r", encoding="utf-8") as sF:
        sampling_period_seconds = float(sF.readline())
        sampling_period_seconds_td = pd.Timedelta(sampling_period_seconds, "s")

    cpu_details_filename = series_dir / CPU_DETAILS_FILENAME
    if not cpu_details_filename.is_file():
        logger.error(f"Path {cpu_details_filename.as_posix()} is not a filename")
        raise Exception()

    with cpu_details_filename.open(mode="r", encoding="utf-8") as cF:
        cpu_details = json.load(cF)

    # TODO, compute this per CPU
    num_cpu_cores = int(cpu_details[0]["cpu cores"])
    num_cpu_processors = len(cpu_details[0]["processors"])
    factor_cores_processors = float(num_cpu_cores) / float(num_cpu_processors)  # noqa: F841

    logger.info(
        f"Processing directory {series_dir.as_posix()} about pid {reference_pid}"
    )

    pids_filename = series_dir / PIDS_FILENAME
    if not pids_filename.is_file():
        logger.error(f"Path {pids_filename.as_posix()} is not a filename")
        raise Exception()

    # Reading all the pids
    pids = pd.read_table(
        pids_filename,
        na_values=["-"],
        dtype={"PID": "Int32", "PPID": "Int32"},
        parse_dates=["Time"],
    )
    # Generating the needed columns to generate a tree structure
    pids["node"] = pids.apply(
        lambda row: str(row.create_time) + "_" + str(row.PID), axis=1
    )
    pids["parent"] = pids.apply(
        lambda row: str(row.ppid_create_time) + "_" + str(row.PPID)
        if not pd.isna(row.PPID)
        else None,
        axis=1,
    )

    # Now, let's read the command lines
    main_commands = []
    command_labels = []
    full_command = []
    full_stats = []
    subtree_root = []
    for index, row in pids.iterrows():
        command_json_filename = series_dir / COMMAND_JSON_FILENAME_TEMPLATE.format(
            row.PID, row.create_time
        )
        with command_json_filename.open(mode="r", encoding="utf-8") as cH:
            command_json = json.load(cH)
            assert isinstance(command_json, list)
            full_command.append(command_json)
            command = process_command(command_json)
            main_commands.append(command)
            command_labels.append(command + "\n" + str(index))
            subtree_root.append(
                command.startswith(group_by_process_name)
                if group_by_process_name is not None
                else row.PID == reference_pid
            )

        metrics_csv_filename = series_dir / METRICS_CSV_FILENAME_TEMPLATE.format(
            row.PID, row.create_time
        )
        metrics = pd.read_csv(metrics_csv_filename, parse_dates=["Time"])

        # Focus on groups based on the core where it was working
        # grouped = metrics.groupby(["core_num"])
        # print(metrics.head())
        full_stats.append(metrics)

    pids["command"] = main_commands
    pids["command_label"] = command_labels
    pids["full_command"] = full_command
    pids["full_stats"] = full_stats
    pids["subtree_root"] = subtree_root

    # Compute the graph
    pids_tree = nx.from_pandas_edgelist(
        pids[pids["parent"].notna()], "parent", "node", create_using=nx.DiGraph
    )
    # Find the roots
    roots = pids[pids["subtree_root"]]["node"]

    node_row_ids: "list[int]" = []
    node_ids: "MutableSequence[str]" = []
    node_labels: "MutableSequence[str]" = []
    # node_rows: "MutableSequence[pd.Row]" = []
    node_consumptions_in_Wh: "MutableSequence[float]" = []
    node_consumptions_in_joules: "MutableSequence[float]" = []
    node_duration: "MutableSequence[pd.Timedelta]" = []
    node_duration_in_s: "MutableSequence[float]" = []
    node_first: "MutableSequence[pd.Timestamp]" = []
    node_last: "MutableSequence[pd.Timestamp]" = []

    # The watts per core
    w_per_core_per_hour = tdp_in_w / float(num_cpu_cores)
    w_per_core_per_second = w_per_core_per_hour / 3600.0

    logger.debug(f"W_c_h => {w_per_core_per_hour} , W_c_s => {w_per_core_per_second}")

    for node_id in roots:
        # Now, time to process all the associated statistics
        the_node_row = pids[pids["node"] == node_id]
        metrics_list = [the_node_row.full_stats.array[0]]
        for child_id in nx.descendants(pids_tree, node_id):
            metrics_list.append(pids[pids["node"] == child_id].full_stats.array[0])
        metrics = pd.concat(metrics_list)

        first_sample = metrics["Time"].min()
        node_first.append(first_sample)

        last_sample = metrics["Time"].max() + sampling_period_seconds_td
        node_last.append(last_sample)

        duration = last_sample - first_sample
        node_duration.append(duration)
        duration_seconds = duration.seconds
        node_duration_in_s.append(duration_seconds)

        # This is to normalize imputation of the sum of core usages in that sample
        metrics["core_usage"] = (
            metrics["CPU"]
            * metrics["core_num"].astype(float)
            / (metrics["processor_num"].astype(float) * 100)
        )

        # Number of seconds the implied cores were used
        total_core_usage_seconds = metrics["core_usage"].sum() * sampling_period_seconds

        # All the joules implied in the computation
        w_s = joules = total_core_usage_seconds * w_per_core_per_second
        # The watts hour
        w_h = joules / 3600

        # grouped = metrics.groupby(["core_num"])
        # samples_core = grouped["CPU"].sum().sum()
        # seconds_core = samples_core * sampling_period_seconds
        # w_s = w_per_core * seconds_core
        # w_h = w_s / 3600

        node_row_id = the_node_row.index.values[0]
        command_label = the_node_row.command.array[0]

        logger.debug(f"{node_row_id} => {total_core_usage_seconds} <= {node_id}")

        # command_line = the_node_row.full_command.array[0]
        # print(f"{command_label} {node_id} {seconds_core} {w_s} {w_h} {command_line}")
        # print(
        #    f"{node_row_id} {command_label.replace('\n', ' ')} unique process id => {node_id} seconds core => {seconds_core} Watts second => {w_s} Watts hour => {w_h}"
        # )
        node_row_ids.append(node_row_id)
        node_ids.append(node_id)
        node_label = command_label.replace("\n", " ")
        if group_by_process_name is not None:
            if node_label.startswith(group_by_process_name + " "):
                node_label = node_label[len(group_by_process_name) + 1 :]
        node_labels.append(str(node_row_id) + " " + node_label)
        # node_rows.append(the_node_row)
        node_consumptions_in_Wh.append(w_h)
        node_consumptions_in_joules.append(w_s)

        # print(f"Hola => {node_id} {nx.descendants(pids_tree, node_id)} {len(metrics)}")

    outputs_dir.mkdir(parents=True, exist_ok=True)
    node_consumptions = pd.DataFrame(
        data={
            "id": node_ids,
            "task": node_labels,
            #    "row": node_rows,
            "W_h": node_consumptions_in_Wh,
            "joules": node_consumptions_in_joules,
            "first_sample": node_first,
            "last_sample": node_last,
            "duration": node_duration,
            "duration_in_s": node_duration_in_s,
        },
        index=node_row_ids,
    )

    with pd.option_context(
        "display.max_rows",
        None,
        "display.max_columns",
        None,
        "display.expand_frame_repr",
        False,
    ):  # more options can be specified also
        print(node_consumptions)

    outputs_dir.mkdir(parents=True, exist_ok=True)

    draw_consumptions_chart(
        node_consumptions,
        outputs_dir,
        # width=33.2,
        # height=11.7,
        # dpi=600,
        # font_size=10,
    )

    draw_lollipop_chart(
        node_consumptions,
        outputs_dir,
    )

    draw_tree(pids, pids_tree, outputs_dir, group_by_process_name)
    draw_spiral(pids, pids_tree, outputs_dir, group_by_process_name)


def main() -> "None":
    if len(sys.argv) >= 4:
        group_by_process_name = sys.argv[4] if len(sys.argv) >= 5 else None
        metrics_aggregator(
            pathlib.Path(sys.argv[1]),
            pathlib.Path(sys.argv[2]),
            tdp_in_w=float(sys.argv[3]),
            group_by_process_name=group_by_process_name,
        )
    else:
        print(
            f"Usage: {sys.argv[0]} {{series_dir}} {{outputs_dir}} {{TDP in W}} [group_by_program_name]",
            file=sys.stderr,
        )
        sys.exit(1)
