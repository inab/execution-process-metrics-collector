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

import pytest
import inspect
import pathlib

from execution_process_metrics_collector.collector import execution_metrics_collector

from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from typing import (
        Optional,
        Sequence,
    )


COLLECTOR_TESTBED = pytest.mark.parametrize(
    ["command_line", "should_fail"],
    [
        (["/usr/bin/sleep", "3"], None),
    ],
)


@COLLECTOR_TESTBED
def test_collector(
    tmpdir: "str",
    command_line: "Sequence[str]",
    should_fail: "Optional[Sequence[str]]",
) -> "None":
    try:
        execution_metrics_collector(
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
