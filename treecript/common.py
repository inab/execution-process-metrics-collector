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
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        Any,
        Final,
        Mapping,
        MutableMapping,
        Tuple,
    )

    from typing_extensions import (
        TypeAlias,
    )

    CPUInfo: TypeAlias = MutableMapping[str, Any]

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
