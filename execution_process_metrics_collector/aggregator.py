#!/usr/bin/env python

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
    PIDS_FILENAME,
    COMMAND_JSON_FILENAME_TEMPLATE,
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
        reference_pid = int(rF.readline())

    logger.info(
        f"Processing directory {series_dir.as_posix()} about pid {reference_pid}"
    )

    pids_filename = series_dir / PIDS_FILENAME
    if not pids_filename.is_file():
        logger.error(f"Path {pids_filename.as_posix()} is not a filename")
        raise Exception()

    # Reading all the pids
    pids = pd.read_table(
        pids_filename, na_values=["-"], dtype={"PID": "Int32", "PPID": "Int32"}
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
    main_command = []
    for index, row in pids.iterrows():
        command_json_filename = series_dir / COMMAND_JSON_FILENAME_TEMPLATE.format(
            row.PID, row.create_time
        )
        with command_json_filename.open(mode="r", encoding="utf-8") as cH:
            command_json = json.load(cH)
            assert isinstance(command_json, list)
            main_command.append(process_command(command_json))

    pids["command"] = main_command

    pids_tree = nx.from_pandas_edgelist(
        pids[pids["parent"].notna()], "parent", "node", create_using=nx.DiGraph
    )

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
        labels=dict(zip(pids["node"], pids["command"])),
        node_color=node_color,
        # node_size=30,
        font_size=8,
    )

    outputs_dir.mkdir(parents=True, exist_ok=True)

    matplotlib.use("pdf")
    fig.savefig(outputs_dir / "graph.pdf")

    matplotlib.use("agg")
    fig.savefig(outputs_dir / "graph.png")


def main() -> "None":
    if len(sys.argv) >= 3:
        group_by_process_name = sys.argv[3] if len(sys.argv) >= 4 else None
        metrics_aggregator(
            pathlib.Path(sys.argv[1]),
            pathlib.Path(sys.argv[2]),
            group_by_process_name=group_by_process_name,
        )
    else:
        print(
            f"Usage: {sys.argv[0]} {{series_dir}} {{outputs_dir}} [group_by_program_name]",
            file=sys.stderr,
        )
        sys.exit(1)
