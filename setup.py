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

import re
import os
import sys
import setuptools

# In this way, we are sure we are getting
# the installer's version of the library
# not the system's one
setupDir = os.path.dirname(__file__)
sys.path.insert(0, setupDir)

from treecript import __version__ as epmc_version  # noqa: E402
from treecript import __author__ as epmc_author  # noqa: E402
from treecript import __license__ as epmc_license  # noqa: E402

# Populating the long description
readme_path = os.path.join(setupDir, "README.md")
with open(readme_path, "r") as fh:
    long_description = fh.read()

# Populating the install requirements
requirements = []
requirements_path = os.path.join(setupDir, "requirements.txt")
if os.path.exists(requirements_path):
    with open(requirements_path, mode="r", encoding="utf-8") as f:
        egg = re.compile(r"#[^#]*egg=([^=&]+)")
        for line in f.read().splitlines():
            print(f"R {line}")
            m = egg.search(line)
            requirements.append(line if m is None else m.group(1))

setuptools.setup(
    name="treecript",
    version=epmc_version,
    author=epmc_author,
    author_email="jose.m.fernandez@bsc.es",
    license=epmc_license,
    description="Process tree metrics gatherer and digester",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/inab/treecript",
    project_urls={"Bug Tracker": "https://github.com/inab/treecript/issues"},
    packages=setuptools.find_packages(),
    package_data={
        "treecript": [
            "py.typed",
        ]
    },
    scripts=[
        "cpuinfo-tdp-finder.py",
        "execution-metrics-collector.py",
        "process-metrics-collector.py",
        "metrics-aggregator.py",
        "modelname-tdp-finder.py",
        "plotGraph.py",
        "tdp-finder.py",
        "execution-metrics-collector.sh",
        "plotGraph.sh",
    ],
    install_requires=requirements,
    # See https://pypi.org/classifiers/
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
