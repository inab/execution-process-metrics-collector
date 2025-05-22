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
import pathlib
import re
import sys

import pandas as pd

from .collector import (
    CPU_DETAILS_FILENAME,
)

logger = logging.getLogger(__name__)


def tdp_finder(series_dir: "pathlib.Path", processors_file: "pathlib.Path") -> "float":
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

    cpus = pd.read_csv(processors_file)

    tdp_str = cpus[
        cpus["ProcessorNumber"].apply(lambda pn: str(pn) in model_name)
    ].ConfigTDPMax.values[0]
    matched = re.search(r"^([0-9]+(?:\.[0-9]+])?) W", tdp_str)
    if matched is not None:
        tdp_matched = matched.group(1)
    else:
        tdp_matched = tdp_str

    return float(tdp_matched)


def main() -> "None":
    if len(sys.argv) >= 3:
        tdp_in_w = tdp_finder(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
        print(f"TDP => {tdp_in_w} W")
    else:
        print(
            f"Usage: {sys.argv[0]} {{series_dir}} {{intel_datasheets_dir}}",
            file=sys.stderr,
        )
        sys.exit(1)
