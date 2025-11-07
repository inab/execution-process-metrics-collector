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

import copy
import datetime
import docker
import json
import logging
import pathlib
import psutil
import re
import socket
import subprocess
import time
import sys

from typing import (
    cast,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from typing import (
        Any,
        Final,
        Mapping,
        MutableMapping,
        MutableSequence,
        Optional,
        Sequence,
        Set,
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

# Module level logger
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


def analyse_list_of_processes(
    children: "Sequence[psutil.Process]",
    processor2corecpu: "Mapping[str, Tuple[str, str]]",
    recorded_pids: "MutableMapping[int, psutil.Process]",
    children_dicts: "MutableSequence[Tuple[Mapping[str, Any], str]]",
    container_data: "Sequence[Tuple[str, float, str, int]]" = list(),
    docker_following_pids: "Mapping[int, int]" = dict(),
) -> "Sequence[Tuple[int, int]]":
    new_pid_pairs: "MutableSequence[Tuple[int, int]]" = []

    container_data_rw = cast(
        "MutableSequence[Tuple[str, float, str, int]]", copy.copy(container_data)
    )

    for child in children:
        child_pid_int = child.pid
        if (child_pid_int in recorded_pids) and recorded_pids[
            child_pid_int
        ].create_time() == child.create_time():
            mode_w = "a"
            # This is needed for accurate CPU percentages
            child = recorded_pids[child_pid_int]
        else:
            mode_w = "w"
            recorded_pids[child_pid_int] = child

        try:
            with child.oneshot():
                # Skip zombie processes
                if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
                    child_threads = child.threads()
                    child_d = child.as_dict(
                        attrs=[
                            "name",
                            "cpu_times",
                            "net_connections",
                            "pid",
                            "cpu_percent",
                            "memory_percent",
                            "num_threads",
                            "cpu_num",
                            "cmdline",
                            "create_time",
                            "status",
                            "io_counters",
                            "ppid",
                            "memory_info",
                            "memory_full_info",
                        ],
                    )

                    threads_processor_num: "Set[int]" = set()
                    threads_core_num: "Set[str]" = set()
                    threads_cpu_num: "Set[str]" = set()
                    for thr in child_threads:
                        processor_id: "int" = child_d["cpu_num"]
                        if thr.id > 0 and thr.id != child_d["pid"]:
                            try:
                                processor_id = psutil.Process(thr.id).cpu_num()
                            except psutil.NoSuchProcess:
                                # For transient cases
                                pass
                        threads_processor_num.add(processor_id)
                        processor_id_str = str(processor_id)

                        unambiguous_core_id = processor2corecpu[processor_id_str]
                        threads_core_num.add(unambiguous_core_id[1])
                        threads_cpu_num.add(unambiguous_core_id[0])

                    child_d["threads_processor_num"] = threads_processor_num
                    child_d["threads_core_num"] = threads_core_num
                    child_d["threads_cpu_num"] = threads_cpu_num

                    # First attempt: already recorded
                    if len(docker_following_pids) > 0:
                        new_ppid = docker_following_pids.get(child_pid_int)
                        # Patching the reference to the parent
                        if new_ppid is not None:
                            # logger.error(
                            #    f"switched {child_pid_int} parent: {child_d['ppid']} => {new_ppid}"
                            # )
                            child_d["ppid"] = new_ppid

                    # Are there docker instances involved?
                    if (
                        len(container_data_rw) > 0
                        and child_d["name"] == "docker"
                        and child_d["cmdline"][1] == "run"
                    ):
                        # logger.error(f"Candidate docker {child_pid_int}")
                        # Matching
                        i_c_t_t: "Optional[int]"
                        for i_c_t_t, c_t_t in enumerate(container_data_rw):
                            (
                                container_id,
                                container_creation,
                                container_image,
                                container_pid,
                            ) = c_t_t
                            if (
                                container_creation > child_d["create_time"]
                                and container_image in child_d["cmdline"]
                            ):
                                new_pid_pairs.append((container_pid, child_pid_int))
                                # logger.error(
                                #    f"Matched docker {child_pid_int} => child {container_pid}"
                                # )
                                break
                        else:
                            i_c_t_t = None

                        if i_c_t_t is not None:
                            del container_data_rw[i_c_t_t]

                    children_dicts.append((child_d, mode_w))
                elif mode_w == "w" and child_pid_int in recorded_pids:
                    # Keeping the internal structures tidied up
                    del recorded_pids[child_pid_int]
        except psutil.NoSuchProcess:
            # Keeping the internal structures tidied up
            if mode_w == "w" and child_pid_int in recorded_pids:
                del recorded_pids[child_pid_int]
        except Exception:
            logger.exception("FIXME: Unexpected exception, please report developers")
            pass

    return new_pid_pairs


def execution_metrics_collector(
    cmdline: "Sequence[str]",
    reldatadir: "pathlib.Path",
    sleep_secs: "float" = 1,
    timestamp_format: "str" = "%Y-%m-%d %H:%M:%S",
    match_docker: "bool" = False,
) -> "pathlib.Path":
    pop = subprocess.Popen(cmdline)
    metrics_path = process_metrics_collector(
        pop.pid,
        reldatadir,
        sleep_secs=sleep_secs,
        timestamp_format=timestamp_format,
        match_docker=match_docker,
    )
    # Just for completeness
    pop.wait()

    return metrics_path


def process_metrics_collector(
    pid: "int",
    reldatadir: "pathlib.Path",
    sleep_secs: "float" = 1,
    timestamp_format: "str" = "%Y-%m-%d %H:%M:%S",
    match_docker: "bool" = False,
) -> "pathlib.Path":
    # If the process does not exist, it will raise a psutil.NoSuchProcess exception
    try:
        p = psutil.Process(pid)
    except psutil.NoSuchProcess:
        logger.error(f"ERROR: Process ID {pid} not found.")
        raise

    current_time = datetime.datetime.now()
    dir_name = reldatadir / f"{current_time.strftime('%Y_%m_%d-%H_%M')}-{pid}"
    dir_name.mkdir(parents=True, exist_ok=True)

    cpu_hash, processor2corecpu = parse_cpuinfo()

    cpu_details_filename = dir_name / CPU_DETAILS_FILENAME
    with cpu_details_filename.open(mode="w", encoding="utf-8") as cdF:
        json.dump(list(cpu_hash.values()), cdF, indent=4)

    processor_topology = [
        {
            "processor_id": processor_id,
            "cpu_id": physid_core[0],
            "core_id": physid_core[1],
        }
        for processor_id, physid_core in processor2corecpu.items()
    ]

    core_affinity_filename = dir_name / CORE_AFFINITY_FILENAME
    with core_affinity_filename.open(mode="w", encoding="utf-8") as caF:
        json.dump(processor_topology, caF, indent=4)

    reference_pid_filename = dir_name / REFERENCE_PID_FILENAME
    with reference_pid_filename.open(mode="w", encoding="utf-8") as cF:
        cF.write(str(pid))

    sampling_period_filename = dir_name / SAMPLING_PERIOD_FILENAME
    with sampling_period_filename.open(mode="w", encoding="utf-8") as sF:
        sF.write(str(sleep_secs))

    metrics_cols = [
        "Time",
        "PID",
        "Virt",
        "Res",
        "CPU",
        "Memory",
        "TCP Connections",
        "Thread Count",
        "User",
        "System",
        "Children_User",
        "Children_System",
        "IO",
        "uss",
        "swap",
        "processor_num",
        "core_num",
        "cpu_num",
        "processor_ids",
        "core_ids",
        "cpu_ids",
        "process_status",
        "read_count",
        "write_count",
        "read_bytes",
        "write_bytes",
        "read_chars",
        "write_chars",
    ]

    pids_filename = dir_name / PIDS_FILENAME

    pids_cols = [
        "Time",
        "PID",
        "create_time",
        "PPID",
        "ppid_create_time",
    ]

    with pids_filename.open(mode="w", encoding="utf-8") as cH:
        print("\t".join(pids_cols), file=cH)

    agg_metrics = dir_name / AGGREGATION_METRICS_FILENAME

    agg_metrics_cols = [
        "Time",
        "numpids",
        "numthreads",
        "maxprocessors",
        "maxcores",
        "maxcpus",
        "cpu_ids",
        "sumuss",
        "sumswap",
        "sum_read_count",
        "sum_write_count",
        "sum_read_bytes",
        "sum_write_bytes",
        "sum_read_chars",
        "sum_write_chars",
    ]

    with agg_metrics.open(mode="w", encoding="utf-8") as cH:
        print("\t".join(agg_metrics_cols), file=cH)

    docker_cli = None
    if match_docker:
        try:
            docker_cli = docker.from_env()
        except docker.errors.DockerException:
            logger.info(
                "Docker service not reachable. Processes spawned using docker will not be properly tracked"
            )

    recorded_pids: "MutableMapping[int, psutil.Process]" = dict()

    # From docker cli to child process
    docker_followed_pids: "MutableMapping[int, int]" = dict()
    # From child process to docker cli
    docker_following_pids: "MutableMapping[int, int]" = dict()

    docker_avoided_pids: "Set[int]" = set()

    while p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
        container_data = []

        possible_docker_pids = set()
        if docker_cli is not None:
            containers = docker_cli.containers.list()

            docker_prev_pids = set(docker_following_pids.keys())
            docker_prev_notpids = set(docker_avoided_pids)
            for container in containers:
                container_pid = container.attrs.get("State", {}).get("Pid")
                if container_pid is not None:
                    if container_pid in docker_prev_pids:
                        docker_prev_pids.remove(container_pid)
                    elif container_pid in docker_prev_notpids:
                        docker_prev_notpids.remove(container_pid)
                    else:
                        possible_docker_pids.add(container_pid)
                        container_created = container.attrs["Created"]
                        if sys.version_info < (3, 11):
                            matched = re.search(
                                r"\:(\d\d)(?:\.\d+)?Z$", container_created
                            )
                            if matched is not None:
                                container_created = (
                                    container_created[0 : matched.span()[0]]
                                    + ":"
                                    + matched.group(1)
                                    + "+00:00"
                                )
                        container_data.append(
                            (
                                container.id,
                                datetime.datetime.fromisoformat(
                                    container_created
                                ).timestamp(),
                                container.attrs["Config"].get("Image"),
                                container_pid,
                            )
                        )

            # Keeping the internal lists clean
            if len(docker_prev_notpids) > 0:
                docker_avoided_pids -= docker_prev_notpids

            # Keeping the internal lists clean
            if len(docker_prev_pids) > 0:
                for prev_pid in docker_prev_pids:
                    parent_pid = docker_following_pids.pop(prev_pid)
                    if parent_pid in docker_followed_pids:
                        del docker_followed_pids[parent_pid]

            # Sorting in place by date
            if len(container_data) > 1:
                container_data.sort(key=lambda c: c[1])

        timestamp_str = datetime.datetime.now().strftime(timestamp_format)

        children_dicts: "MutableSequence[Tuple[Mapping[str, Any], str]]" = []
        children = p.children(recursive=True)
        children.insert(0, p)

        # First pass, gather all
        new_pid_pairs = analyse_list_of_processes(
            children,
            processor2corecpu,
            recorded_pids,
            children_dicts,
            container_data=container_data,
            docker_following_pids=docker_following_pids,
        )

        for child_pid, parent_pid in new_pid_pairs:
            possible_docker_pids.remove(child_pid)
            docker_followed_pids[parent_pid] = child_pid
            docker_following_pids[child_pid] = parent_pid

        if len(docker_following_pids) > 0:
            docker_following_pids_instances = []
            for the_pid in docker_following_pids.keys():
                try:
                    the_pid_instance = (
                        recorded_pids[the_pid]
                        if the_pid in recorded_pids
                        else psutil.Process(the_pid)
                    )
                    docker_following_pids_instances.append(the_pid_instance)
                    docker_following_pids_instances.extend(
                        the_pid_instance.children(recursive=True)
                    )
                except psutil.NoSuchProcess:
                    logger.error(f"ERROR: Process ID {the_pid} from docker not found.")

            if len(docker_following_pids_instances) > 0:
                children.extend(docker_following_pids_instances)
                analyse_list_of_processes(
                    docker_following_pids_instances,
                    processor2corecpu,
                    recorded_pids,
                    children_dicts,
                    docker_following_pids=docker_following_pids,
                )

        # Does any docker unmatched pid remain?
        if len(possible_docker_pids) > 0:
            docker_avoided_pids.update(possible_docker_pids)

        children_dicts_dict = {
            child_d["pid"]: child_d for (child_d, mode_w) in children_dicts
        }

        # Second pass, print all
        unique_processors = set()
        unique_cores = set()
        unique_cpus = set()
        sumuss = 0
        sumswap = 0
        sumthreads = 0
        sum_read_count = 0
        sum_write_count = 0
        sum_read_bytes = 0
        sum_write_bytes = 0
        sum_read_chars = 0
        sum_write_chars = 0
        for child_d, mode_w in children_dicts:
            child_pid = child_d["pid"]
            child_pid_str = str(child_pid)
            create_time = child_d["create_time"]
            csv_filename = dir_name / METRICS_CSV_FILENAME_TEMPLATE.format(
                child_pid_str, create_time
            )

            if mode_w == "w":
                logger.info(f"Writing data to CSV file {csv_filename.as_posix()}...")

                command_filename = dir_name / COMMAND_TXT_FILENAME_TEMPLATE.format(
                    child_pid_str, create_time
                )
                command_json = dir_name / COMMAND_JSON_FILENAME_TEMPLATE.format(
                    child_pid_str, create_time
                )

                with command_filename.open(mode="w", encoding="utf-8") as cF:
                    print(" ".join(child_d["cmdline"]), file=cF)
                # Maybe include more static process metadata in the future
                with command_json.open(mode="w", encoding="utf-8") as cJ:
                    json.dump(child_d["cmdline"], cJ)

                parent_pid_str: "str" = str(child_d["ppid"])
                parent_create_time = children_dicts_dict.get(child_d["ppid"], {}).get(
                    "create_time"
                )
                if parent_create_time is not None:
                    # parent_creation_timestamp = datetime.datetime.fromtimestamp(
                    #    parent_create_time
                    # ).strftime(timestamp_format)
                    parent_creation_timestamp = str(parent_create_time)
                else:
                    # logger.error(f"{child_pid} {parent_pid_str}")
                    parent_pid_str = "-"
                    parent_creation_timestamp = "-"

                with pids_filename.open(mode="a", encoding="utf-8") as cH:
                    creation_timestamp = datetime.datetime.fromtimestamp(
                        create_time
                    ).strftime(timestamp_format)
                    print(
                        "\t".join(
                            (
                                creation_timestamp,
                                child_pid_str,
                                str(create_time),
                                parent_pid_str,
                                parent_creation_timestamp,
                            )
                        ),
                        file=cH,
                    )

            with csv_filename.open(mode=mode_w, encoding="utf-8") as cH:
                if mode_w == "w":
                    print(",".join(metrics_cols), file=cH)

                # Counting TCP connections
                c_conn = child_d["net_connections"]
                tcp_connections = 0
                if c_conn is not None:
                    for c_c in c_conn:
                        if (
                            c_c.family == socket.AF_INET
                            and c_c.type == socket.SOCK_STREAM
                        ):
                            tcp_connections += 1

                c_cpu = child_d["cpu_times"]
                c_mem = child_d["memory_info"]
                c_mem_vms = c_mem.vms
                c_mem_rss = c_mem.rss
                c_full_mem = child_d["memory_full_info"]
                c_full_mem_uss = getattr(c_full_mem, "uss", 0)
                c_full_mem_swap = getattr(c_full_mem, "swap", 0)
                c_io = child_d["io_counters"]
                metrics = (
                    timestamp_str,
                    child_pid_str,
                    str(c_mem_vms),
                    str(c_mem_rss),
                    str(child_d["cpu_percent"]),
                    str(child_d["memory_percent"]),
                    str(tcp_connections),
                    str(child_d["num_threads"]),
                    str(c_cpu.user),
                    str(c_cpu.system),
                    str(c_cpu.children_user),
                    str(c_cpu.children_system),
                    str(c_cpu.iowait),
                    str(c_full_mem_uss),
                    str(c_full_mem_swap),
                    str(len(child_d["threads_processor_num"])),
                    str(len(child_d["threads_core_num"])),
                    str(len(child_d["threads_cpu_num"])),
                    " ".join(map(str, child_d["threads_processor_num"])),
                    " ".join(map(str, child_d["threads_core_num"])),
                    " ".join(map(str, child_d["threads_cpu_num"])),
                    str(child_d["status"]),
                    str(c_io.read_count),
                    str(c_io.write_count),
                    str(c_io.read_bytes),
                    str(c_io.write_bytes),
                    str(c_io.read_chars),
                    str(c_io.write_chars),
                )

                # Aggregated statistics
                # unique_cpus.add(child_d["cpu_num"])
                unique_processors.update(child_d["threads_processor_num"])
                unique_cores.update(child_d["threads_core_num"])
                unique_cpus.update(child_d["threads_cpu_num"])
                sumuss += c_full_mem_uss
                sumswap += c_full_mem_swap
                sumthreads += child_d["num_threads"]
                sum_read_count += c_io.read_count
                sum_write_count += c_io.write_count
                sum_read_bytes += c_io.read_bytes
                sum_write_bytes += c_io.write_bytes
                sum_read_chars += c_io.read_chars
                sum_write_chars += c_io.write_chars

                print(",".join(metrics), file=cH)

        with agg_metrics.open(mode="a", encoding="utf-8") as cH:
            print(
                "\t".join(
                    (
                        timestamp_str,
                        str(len(children_dicts)),
                        str(sumthreads),
                        str(len(unique_processors)),
                        str(len(unique_cores)),
                        str(len(unique_cpus)),
                        " ".join(unique_cpus),
                        str(sumuss),
                        str(sumswap),
                        str(sum_read_count),
                        str(sum_write_count),
                        str(sum_read_bytes),
                        str(sum_write_bytes),
                        str(sum_read_chars),
                        str(sum_write_chars),
                    )
                ),
                file=cH,
            )

        time.sleep(sleep_secs)

    return dir_name


def main() -> "None":
    if len(sys.argv) >= 3:
        if len(sys.argv) >= 4:
            sleep_secs = float(sys.argv[3])
        else:
            sleep_secs = 1
        process_metrics_collector(
            int(sys.argv[1]),
            pathlib.Path(sys.argv[2]),
            sleep_secs=sleep_secs,
            match_docker=True,
        )
    else:
        print(
            f"Usage: {sys.argv[0]} {{pid}} {{results_dir}} [sleep_secs]",
            file=sys.stderr,
        )
        sys.exit(1)


def main__commandline() -> "None":
    if len(sys.argv) >= 3:
        execution_metrics_collector(
            sys.argv[2:],
            pathlib.Path(sys.argv[1]),
            sleep_secs=1,
            match_docker=True,
        )
    else:
        print(
            f"Usage: {sys.argv[0]} {{results_dir}} <command line to be run>",
            file=sys.stderr,
        )
        sys.exit(1)
