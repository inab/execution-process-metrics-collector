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

import pytest
import inspect
import os
import pathlib
import shutil
import subprocess

from treecript.collector import execution_metrics_collector
from treecript.tdp_finder import tdp_finder_from_series
from treecript import tdp_sources

from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from typing import (
        Optional,
        Sequence,
    )
    from typing_extensions import (
        Final,
    )


COLLECTOR_TESTBED = pytest.mark.parametrize(
    ["command_line", "should_fail"],
    [
        (["/usr/bin/sleep", "3"], None),
    ],
)


@pytest.mark.filterwarnings("ignore:.*:pytest.PytestReturnNotNoneWarning")
@COLLECTOR_TESTBED
def test_collector(
    tmpdir: "str",
    command_line: "Sequence[str]",
    should_fail: "Optional[Sequence[str]]",
) -> "pathlib.Path":
    try:
        metrics_path = execution_metrics_collector(
            command_line,
            pathlib.Path(tmpdir),
            match_docker=True,
        )
    except BaseException:
        current_frame = inspect.currentframe()
        if (
            should_fail is None
            or current_frame is None
            or current_frame.f_code.co_name not in should_fail
        ):  # type: ignore[union-attr]
            raise
    else:
        current_frame = inspect.currentframe()
        if (
            should_fail is not None
            and current_frame is not None
            and current_frame.f_code.co_name in should_fail
        ):  # type: ignore[union-attr]
            raise AssertionError(
                f"Method {current_frame.f_code.co_name} should have failed with command line {command_line}"
            )  # type: ignore[union-attr]

    return metrics_path


CPU_SPEC_DATASET_REPO: "Final[str]" = "https://github.com/JosuaCarl/cpu-spec-dataset"


@COLLECTOR_TESTBED
def test_tdp_finder_from_series(
    tmpdir: "str",
    command_line: "Sequence[str]",
    should_fail: "Optional[Sequence[str]]",
) -> "None":
    metrics_path = test_collector(tmpdir, command_line, should_fail)

    spec_path = pathlib.Path(tmpdir) / "cpu_spec_dataset"
    # Try materialising from cached contents
    if not spec_path.exists():
        source_spec_path = os.environ.get("CACHED_CPU_SPEC_DATASET")
        if source_spec_path is not None and os.path.exists(source_spec_path):
            shutil.copytree(source_spec_path, spec_path)

    if not spec_path.exists():
        git_path = shutil.which("git")
        assert git_path is not None, "git not found"
        subprocess.run(
            [git_path, "clone", CPU_SPEC_DATASET_REPO, spec_path.as_posix()], check=True
        )

    assert spec_path.is_dir()

    processors_files = list((spec_path / "dataset").glob("*.csv"))

    assert len(processors_files) > 0

    # Try materialising from cached contents
    cpumark_path = pathlib.Path(tmpdir) / "cpumark_table.csv"
    if not cpumark_path.exists():
        source_cpumark_path = os.environ.get("CACHED_CPUMARK_DATASET")
        if source_cpumark_path is not None and os.path.exists(source_cpumark_path):
            shutil.copy2(source_cpumark_path, cpumark_path, follow_symlinks=False)

    if not cpumark_path.exists():
        tdp_sources.scrape_tdp_table_cpubenchmark(cpumark_path)

    assert cpumark_path.is_file()

    processors_files.append(cpumark_path)

    try:
        tdp_finder_from_series(metrics_path, processors_files)
    except BaseException:
        current_frame = inspect.currentframe()
        if (
            should_fail is None
            or current_frame is None
            or current_frame.f_code.co_name not in should_fail
        ):  # type: ignore[union-attr]
            raise
    else:
        current_frame = inspect.currentframe()
        if (
            should_fail is not None
            and current_frame is not None
            and current_frame.f_code.co_name in should_fail
        ):  # type: ignore[union-attr]
            raise AssertionError(
                f"Method {current_frame.f_code.co_name} should have failed with command line {command_line}"
            )  # type: ignore[union-attr]
