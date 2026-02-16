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

import argparse
import json
import logging
import pathlib
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
    series_dir: "pathlib.Path", processors_files: "Sequence[pathlib.Path]"
) -> "Sequence[Tuple[str, str, float, pathlib.Path]]":
    if not series_dir.is_dir():
        logger.error(f"Path {series_dir.as_posix()} is not a directory")
        raise Exception()

    cpu_details_filename = series_dir / CPU_DETAILS_FILENAME
    if not cpu_details_filename.is_file():
        logger.error(f"Path {cpu_details_filename.as_posix()} is not a filename")
        raise Exception()

    with cpu_details_filename.open(mode="r", encoding="utf-8") as cF:
        cpu_details = json.load(cF)

    return tdp_finder_from_cpuinfo(cpu_details, processors_files)


def tdp_finder_from_raw(
    cpuinfo_file: "pathlib.Path", processors_files: "Sequence[pathlib.Path]"
) -> "Sequence[Tuple[str, str, float, pathlib.Path]]":
    if not cpuinfo_file.is_file():
        logger.error(f"Path {cpuinfo_file.as_posix()} is not a file")
        raise Exception()

    cpu_hash, processor2corecpu = parse_cpuinfo(cpuinfo_file.as_posix())

    return tdp_finder_from_cpuinfo(list(cpu_hash.values()), processors_files)


def main_tdp_finder() -> "None":
    par_parser = argparse.ArgumentParser()

    meg = par_parser.add_mutually_exclusive_group()
    meg.add_argument(
        "-q",
        dest="logging_level",
        const=logging.ERROR,
        help="Be quiet, print only the consumption",
        action="store_const",
    )
    meg.add_argument(
        "-d",
        dest="logging_level",
        const=logging.DEBUG,
        help="Switch logging to Be quiet, print only the consumption",
        action="store_const",
    )

    par_parser.add_argument(
        "series_dir",
        help="Directory of the gathered metrics timeline, where the CPU details were recorded",
    )
    par_parser.add_argument(
        "cpu_database_files",
        nargs="+",
        help="The CSV files where the list of CPUs are available, along with their consumptions",
    )

    args = par_parser.parse_args()

    logging_level = (
        args.logging_level if args.logging_level is not None else logging.WARNING
    )

    logging.basicConfig(level=logging_level)

    for model_name, tdp_column, tdp_in_w, processors_file in tdp_finder_from_series(
        pathlib.Path(args.series_dir), list(map(pathlib.Path, args.cpu_database_files))
    ):
        if logging_level < logging.ERROR:
            print(
                f"Model [{model_name}] => TDP [{tdp_column}] => {tdp_in_w} W => File {processors_file.as_posix()}"
            )
        else:
            print(str(tdp_in_w))


def main_cpuinfo_tdp_finder() -> "None":
    par_parser = argparse.ArgumentParser()

    meg = par_parser.add_mutually_exclusive_group()
    meg.add_argument(
        "-q",
        dest="logging_level",
        const=logging.ERROR,
        help="Be quiet, print only the consumption",
        action="store_const",
    )
    meg.add_argument(
        "-d",
        dest="logging_level",
        const=logging.DEBUG,
        help="Switch logging to Be quiet, print only the consumption",
        action="store_const",
    )

    par_parser.add_argument(
        "cpuinfo_file",
        help="CPU details provided by Linux kernel, usually available at /proc/cpuinfo",
    )
    par_parser.add_argument(
        "cpu_database_files",
        nargs="+",
        help="The CSV files where the list of CPUs are available, along with their consumptions",
    )

    args = par_parser.parse_args()

    logging_level = (
        args.logging_level if args.logging_level is not None else logging.WARNING
    )

    logging.basicConfig(level=logging_level)

    for model_name, tdp_column, tdp_in_w, processors_file in tdp_finder_from_raw(
        pathlib.Path(args.cpuinfo_file),
        list(map(pathlib.Path, args.cpu_database_files)),
    ):
        if logging_level < logging.ERROR:
            print(
                f"Model [{model_name}] => TDP [{tdp_column}] => {tdp_in_w} W => File {processors_file.as_posix()}"
            )
        else:
            print(str(tdp_in_w))


def main_modelname_tdp_finder() -> "None":
    par_parser = argparse.ArgumentParser()

    meg = par_parser.add_mutually_exclusive_group()
    meg.add_argument(
        "-q",
        dest="logging_level",
        const=logging.ERROR,
        help="Be quiet, print only the consumption",
        action="store_const",
    )
    meg.add_argument(
        "-d",
        dest="logging_level",
        const=logging.DEBUG,
        help="Switch logging to Be quiet, print only the consumption",
        action="store_const",
    )

    par_parser.add_argument(
        "model_string",
        help="Processor model string to be searched",
    )
    par_parser.add_argument(
        "cpu_database_files",
        nargs="+",
        help="The CSV files where the list of CPUs are available, along with their consumptions",
    )

    args = par_parser.parse_args()

    logging_level = (
        args.logging_level if args.logging_level is not None else logging.WARNING
    )

    logging.basicConfig(level=logging_level)

    model_name, tdp_column, tdp_in_w, processors_file = tdp_finder_from_model_name(
        args.model_string, list(map(pathlib.Path, args.cpu_database_files))
    )
    if logging_level < logging.ERROR:
        print(
            f"Model [{model_name}] => TDP [{tdp_column}] => {tdp_in_w} W => File {processors_file.as_posix()}"
        )
    else:
        print(str(tdp_in_w))
