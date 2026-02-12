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

import collections
import http.cookiejar
import json
import pathlib
import sys
import urllib.request

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        Final,
        Sequence,
    )

CPUBENCHMARK_NET_MEGA_PAGE_URL: "Final[str]" = (
    "https://www.cpubenchmark.net/CPU_mega_page.html"
)
CPUBENCHMARK_NET_DATA_URL: "Final[str]" = "https://www.cpubenchmark.net/data/"

DEFAULT_USER_AGENT: "Final[str]" = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
)

CRAWLERS_NAME_COLUMN: "Final[str]" = "Name_from_CPUBenchmark"
CRAWLERS_TDP_COLUMN: "Final[str]" = "TDP"

HONORED_KEY_COLUMNS_CRAWLERS: "Final[Sequence[str]]" = (CRAWLERS_NAME_COLUMN,)


def scrape_tdp_table_cpubenchmark(cache_file: "pathlib.Path") -> "None":
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    opener.addheaders = [
        ("User-Agent", DEFAULT_USER_AGENT),
    ]
    req = urllib.request.Request(
        CPUBENCHMARK_NET_MEGA_PAGE_URL,
    )
    with opener.open(req) as _:
        # We are here only for the cookies ;-)
        pass

    datareq = urllib.request.Request(
        CPUBENCHMARK_NET_DATA_URL,
        headers=dict(
            [
                ("Accept", "application/json, text/javascript, */*; q=0.01"),
                ("X-Requested-With", "XMLHttpRequest"),
                ("Referer", CPUBENCHMARK_NET_MEGA_PAGE_URL),
            ]
        ),
    )
    with opener.open(datareq) as datareq_response:
        data = json.load(datareq_response, object_pairs_hook=collections.OrderedDict)
        assert isinstance(data, collections.OrderedDict) and "data" in data

        with cache_file.open(mode="wt", encoding="utf-8") as open_fh:
            open_fh.write(
                '"'
                + '","'.join((CRAWLERS_NAME_COLUMN, CRAWLERS_TDP_COLUMN, "Cores"))
                + '"\n'
            )
            for processor_entry in data["data"]:
                if processor_entry["tdp"] != "NA":
                    open_fh.write(
                        '"'
                        + '","'.join(
                            (
                                processor_entry["name"],
                                processor_entry["tdp"],
                                processor_entry["cores"],
                            )
                        )
                        + '"\n'
                    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scrape_tdp_table_cpubenchmark(pathlib.Path(sys.argv[1]))
        sys.exit(0)
    else:
        print(
            f"Usage: {sys.argv[0]} {{dest_file}}",
            file=sys.stderr,
        )
        sys.exit(1)
