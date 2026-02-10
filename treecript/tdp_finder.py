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
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        Sequence,
        Tuple,
    )

from .common import (
    CPU_DETAILS_FILENAME,
    parse_cpuinfo,
    tdp_finder_from_cpuinfo,
    tdp_finder_from_model_name,
)

logger = logging.getLogger(__name__)


def tdp_finder_from_series(
    series_dir: "pathlib.Path", processors_file: "pathlib.Path"
) -> "Sequence[Tuple[str, str, float]]":
    if not series_dir.is_dir():
        logger.error(f"Path {series_dir.as_posix()} is not a directory")
        raise Exception()

    cpu_details_filename = series_dir / CPU_DETAILS_FILENAME
    if not cpu_details_filename.is_file():
        logger.error(f"Path {cpu_details_filename.as_posix()} is not a filename")
        raise Exception()

    with cpu_details_filename.open(mode="r", encoding="utf-8") as cF:
        cpu_details = json.load(cF)

    return tdp_finder_from_cpuinfo(cpu_details, processors_file)


def tdp_finder_from_raw(
    cpuinfo_file: "pathlib.Path", processors_file: "pathlib.Path"
) -> "Sequence[Tuple[str, str, float]]":
    if not cpuinfo_file.is_file():
        logger.error(f"Path {cpuinfo_file.as_posix()} is not a file")
        raise Exception()

    cpu_hash, processor2corecpu = parse_cpuinfo(cpuinfo_file.as_posix())

    return tdp_finder_from_cpuinfo(list(cpu_hash.values()), processors_file)


def main_tdp_finder() -> "None":
    if len(sys.argv) >= 3:
        for model_name, tdp_column, tdp_in_w in tdp_finder_from_series(
            pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
        ):
            print(f"Model [{model_name}] => TDP [{tdp_column}] => {tdp_in_w} W")
    else:
        print(
            f"Usage: {sys.argv[0]} {{series_dir}} {{intel_datasheets_dir}}",
            file=sys.stderr,
        )
        sys.exit(1)


def main_cpuinfo_tdp_finder() -> "None":
    if len(sys.argv) >= 3:
        for model_name, tdp_column, tdp_in_w in tdp_finder_from_raw(
            pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
        ):
            print(f"Model [{model_name}] => TDP [{tdp_column}] => {tdp_in_w} W")
    else:
        print(
            f"Usage: {sys.argv[0]} {{cpuinfo_file}} {{intel_datasheets_dir}}",
            file=sys.stderr,
        )
        sys.exit(1)


def main_modelname_tdp_finder() -> "None":
    if len(sys.argv) >= 3:
        model_name, tdp_column, tdp_in_w = tdp_finder_from_model_name(
            sys.argv[1], pathlib.Path(sys.argv[2])
        )
        print(f"Model [{model_name}] => TDP [{tdp_column}] => {tdp_in_w} W")
    else:
        print(
            f"Usage: {sys.argv[0]} {{model_string}} {{intel_datasheets_dir}}",
            file=sys.stderr,
        )
        sys.exit(1)
