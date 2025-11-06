#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: GPL-3.0-or-later
# treecript, a process tree metrics gatherer.
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
import pathlib
import re
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        Tuple,
    )

import pandas as pd

from .collector import (
    CPU_DETAILS_FILENAME,
)

logger = logging.getLogger(__name__)


def tdp_finder(
    series_dir: "pathlib.Path", processors_file: "pathlib.Path"
) -> "Tuple[str, float]":
    if not series_dir.is_dir():
        logger.error(f"Path {series_dir.as_posix()} is not a directory")
        raise Exception()

    cpu_details_filename = series_dir / CPU_DETAILS_FILENAME
    if not cpu_details_filename.is_file():
        logger.error(f"Path {cpu_details_filename.as_posix()} is not a filename")
        raise Exception()

    with cpu_details_filename.open(mode="r", encoding="utf-8") as cF:
        cpu_details = json.load(cF)

    model_name = cpu_details[0]["model name"]

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

    filtered_cpus = cpus[cpus[key_column].apply(lambda pn: str(pn) in model_name)]

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

    return (matches[0][0], float(matches[0][1]))


def main() -> "None":
    if len(sys.argv) >= 3:
        tdp_column, tdp_in_w = tdp_finder(
            pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
        )
        print(f"TDP ({tdp_column}) => {tdp_in_w} W")
    else:
        print(
            f"Usage: {sys.argv[0]} {{series_dir}} {{intel_datasheets_dir}}",
            file=sys.stderr,
        )
        sys.exit(1)
