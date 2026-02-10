#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: GPL-3.0-or-later
# treecript, a process tree metrics gatherer.
# Copyright (C) 2026 Barcelona Supercomputing Center, José M. Fernández
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

import copy
import logging
import pathlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        Any,
        Final,
        Mapping,
        MutableMapping,
        MutableSequence,
        Sequence,
        Set,
        Tuple,
    )

    from typing_extensions import (
        TypeAlias,
    )

    CPUInfo: TypeAlias = MutableMapping[str, Any]

import pandas as pd

CPU_DETAILS_FILENAME: "Final[str]" = "cpu_details.json"
CORE_AFFINITY_FILENAME: "Final[str]" = "core_affinity.json"
REFERENCE_PID_FILENAME: "Final[str]" = "reference_pid.txt"
SAMPLING_PERIOD_FILENAME: "Final[str]" = "sampling-period-seconds.txt"
PIDS_FILENAME: "Final[str]" = "pids.txt"
AGGREGATION_METRICS_FILENAME: "Final[str]" = "agg_metrics.tsv"

METRICS_CSV_FILENAME_TEMPLATE: "Final[str]" = "metrics-{0}_{1}.csv"
COMMAND_TXT_FILENAME_TEMPLATE: "Final[str]" = "command-{0}_{1}.txt"
COMMAND_JSON_FILENAME_TEMPLATE: "Final[str]" = "command-{0}_{1}.json"

logger = logging.getLogger(__name__)


def parse_cpuinfo(
    cpuinfo_filename: "str" = "/proc/cpuinfo",
) -> "Tuple[Mapping[str, CPUInfo], Mapping[str, Tuple[str, str]]]":
    kvsplitter = re.compile(r"\s*:\s*")

    entries = []
    curr_entry: "CPUInfo" = dict()
    cpu_hash: "MutableMapping[str, CPUInfo]" = {}
    processor2corecpu: "MutableMapping[str, Tuple[str, str]]" = {}
    with open(cpuinfo_filename, mode="r", encoding="latin1") as cH:
        for line in cH:
            line = line.rstrip("\n")
            tokens = kvsplitter.split(line)
            if len(tokens) < 2:
                entries.append(curr_entry)
                physical_id = curr_entry.get("physical id")
                assert isinstance(physical_id, str)
                processor = curr_entry.get("processor")
                assert isinstance(processor, str)
                if physical_id in cpu_hash:
                    curr_cpu = cpu_hash[physical_id]
                else:
                    curr_cpu = copy.copy(curr_entry)
                    curr_cpu["processors"] = []
                    cpu_hash[physical_id] = curr_cpu
                curr_cpu["processors"].append(processor)
                core_id = curr_entry.get("core id")
                assert isinstance(core_id, str)
                processor2corecpu[processor] = (physical_id, core_id)
                curr_entry = dict()
            else:
                curr_entry[tokens[0]] = tokens if len(tokens) > 2 else tokens[1]
    if curr_entry:
        entries.append(curr_entry)
        physical_id = curr_entry.get("physical id")
        assert isinstance(physical_id, str)
        processor = curr_entry.get("processor")
        assert isinstance(processor, str)
        if physical_id in cpu_hash:
            curr_cpu = cpu_hash[physical_id]
        else:
            curr_cpu = copy.copy(curr_entry)
            curr_cpu["processors"] = []
        curr_cpu["processors"].append(processor)
        core_id = curr_entry.get("core id")
        assert isinstance(core_id, str)
        processor2corecpu[processor] = (physical_id, core_id)

    return cpu_hash, processor2corecpu


def _tdp_finder_from_model_name(
    model_name: "str",
    key_column: "str",
    cpus_df: "pd.DataFrame",
    processors_file: "pathlib.Path",
) -> "Tuple[str, str, float]":
    if key_column not in cpus_df:
        logger.error(
            f"Unable to find a valid processor identification column in file {processors_file.as_posix()}"
        )
        raise Exception()

    filtered_cpus = cpus_df[cpus_df[key_column].apply(lambda pn: str(pn) in model_name)]

    if len(filtered_cpus) == 0:
        logger.error(
            f"Unable to match a valid processor row for {model_name} in file {processors_file.as_posix()}"
        )
        raise Exception()

    matches = []
    for column_name, column in filtered_cpus.items():
        if not column.hasnans:
            putative_tdp_str = column.values[0]
            if isinstance(putative_tdp_str, str):
                matched = re.search(
                    r"^(?:[0-9]+(?:\.[0-9]+])?-)?([0-9]+(?:\.[0-9]+])?) W",
                    putative_tdp_str,
                )
                if matched:
                    matches.append((str(column_name), matched.group(1)))

    if len(matches) == 0:
        logger.error(
            f"Unable to find processor package consumption values for {model_name} in file {processors_file.as_posix()}"
        )
        raise Exception()

    # Now, sort by consumption
    matches.sort(key=lambda t: t[1], reverse=True)

    return (model_name, matches[0][0], float(matches[0][1]))


def tdp_finder_from_model_name(
    model_name: "str", processors_file: "pathlib.Path"
) -> "Tuple[str, str, float]":
    # low_memory is needed to avoid a warning in some CSV files with mixed data
    cpus = pd.read_csv(processors_file, low_memory=False)

    for key_column in ("ProcessorNumber", "Processor Number"):
        if key_column in cpus.columns:
            break
    else:
        logger.error(
            f"Unable to find a valid processor identification column in file {processors_file.as_posix()}"
        )
        raise Exception()

    return _tdp_finder_from_model_name(model_name, key_column, cpus, processors_file)


def tdp_finder_from_cpuinfo(
    cpu_details: "Sequence[CPUInfo]", processors_file: "pathlib.Path"
) -> "Sequence[Tuple[str, str, float]]":
    # low_memory is needed to avoid a warning in some CSV files with mixed data
    cpus = pd.read_csv(processors_file, low_memory=False)

    for key_column in ("ProcessorNumber", "Processor Number"):
        if key_column in cpus.columns:
            break
    else:
        logger.error(
            f"Unable to find a valid processor identification column in file {processors_file.as_posix()}"
        )
        raise Exception()

    seen_model_names: "Set[str]" = set()
    found_tdp: "MutableSequence[Tuple[str, str, float]]" = []
    for cpu_details_cpu in cpu_details:
        model_name = cpu_details_cpu["model name"]
        if model_name not in seen_model_names:
            seen_model_names.add(model_name)

            found_tdp.append(
                _tdp_finder_from_model_name(
                    model_name, key_column, cpus, processors_file
                )
            )

    return found_tdp
