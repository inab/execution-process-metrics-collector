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
        Optional,
        Sequence,
    )

import pandas as pd
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt


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

    cpu_details_filename = series_dir / CPU_DETAILS_FILENAME
    if not cpu_details_filename.is_file():
        logger.error(f"Path {cpu_details_filename.as_posix()} is not a filename")
        raise Exception()

    with cpu_details_filename.open(mode="r", encoding="utf-8") as cF:
        cpu_details = json.load(cF)

    num_cpu_cores = int(cpu_details[0]["cpu cores"])

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
    for node_id in roots:
        # Now, time to process all the associated statistics
        the_node_row = pids[pids["node"] == node_id]
        metrics_list = [the_node_row.full_stats.array[0]]
        for child_id in nx.descendants(pids_tree, node_id):
            metrics_list.append(pids[pids["node"] == child_id].full_stats.array[0])
        metrics = pd.concat(metrics_list)

        grouped = metrics.groupby(["core_num"])
        samples_core = grouped["CPU"].sum().sum()
        seconds_core = samples_core * sampling_period_seconds
        w_s = tdp_in_w / num_cpu_cores * seconds_core
        w_h = w_s / 3600

        command_label = the_node_row.command.array[0]
        # command_line = the_node_row.full_command.array[0]
        # print(f"{command_label} {node_id} {seconds_core} {w_s} {w_h} {command_line}")
        print(
            f"{the_node_row.index.values[0]} {command_label.replace('\n', ' ')} unique process id => {node_id} seconds core => {seconds_core} Watts second => {w_s} Watts hour => {w_h}"
        )

        # print(f"Hola => {node_id} {nx.descendants(pids_tree, node_id)} {len(metrics)}")

    # Part of this code came from https://networkx.org/documentation/latest/auto_examples/graph/plot_morse_trie.html#sphx-glr-auto-examples-graph-plot-morse-trie-py
    for i, layer in enumerate(nx.topological_generations(pids_tree)):
        for n in layer:
            pids_tree.nodes[n]["layer"] = i
    # pos = nx.multipartite_layout(pids_tree, subset_key="layer", align="horizontal")
    pos = nx.multipartite_layout(pids_tree, subset_key="layer", align="vertical")
    # Flip the layout so the root node is on top
    for k in pos:
        pos[k][-1] *= -1

    # pos = nx.spiral_layout(pids_tree, resolution=0.5, equidistant=True)

    # A4 in inches
    # fig = plt.figure(figsize=(11.7,8.3))
    # A3 in inches
    fig = plt.figure(figsize=(16.6, 11.7), dpi=300, tight_layout=True)
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

    outputs_dir.mkdir(parents=True, exist_ok=True)

    # Call graph
    matplotlib.use("pdf")
    fig.savefig(outputs_dir / "graph.pdf")

    matplotlib.use("agg")
    fig.savefig(outputs_dir / "graph.png")


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
