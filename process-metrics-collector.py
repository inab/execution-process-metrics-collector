#!/usr/bin/env python

import copy
import datetime
import json
import logging
import pathlib
import psutil
import re
import socket
import time
import sys

def parse_cpuinfo(cpuinfo_filename: "str" = "/proc/cpuinfo") -> "Tuple[Mapping[str, CPUInfo], Mapping[str, Tuple[str, str]]]":
	kvsplitter = re.compile(r"\s*:\s*")
	
	entries = []
	curr_entry = dict()
	cpu_hash = {}
	processor2corecpu = {}
	with open(cpuinfo_filename, mode="r", encoding="latin1") as cH:
		for line in cH:
			line = line.rstrip("\n")
			tokens = kvsplitter.split(line)
			if len(tokens) < 2:
				entries.append(curr_entry)
				physical_id = curr_entry.get("physical id")
				processor = curr_entry.get("processor")
				if physical_id in cpu_hash:
					curr_cpu = cpu_hash[physical_id]
				else:
					curr_cpu = copy.copy(curr_entry)
					curr_cpu["processors"] = []
					cpu_hash[physical_id] = curr_cpu
				curr_cpu["processors"].append(processor)
				processor2corecpu[processor] = (physical_id, curr_entry.get("core id"))
				curr_entry = dict()
			else:
				curr_entry[tokens[0]] = tokens if len(tokens) > 2 else tokens[1]
	if curr_entry:
		entries.append(curr_entry)
		physical_id = curr_entry.get("physical id")
		processor = curr_entry.get("processor")
		if physical_id in cpu_hash:
			curr_cpu = cpu_hash[physical_id]
		else:
			curr_cpu = copy.copy(curr_entry)
			curr_cpu["processors"] = []
		curr_cpu["processors"].append(processor)
		processor2corecpu[processor] = (physical_id, curr_entry.get("core id"))

	return cpu_hash, processor2corecpu

def process_metrics_collector(pid: int, reldatadir: pathlib.Path, sleep_secs: float = 1, timestamp_format: str = "%Y-%m-%d %H:%M:%S"):
    # If the process does not exist, it will raise a psutil.NoSuchProcess exception
    try:
        p = psutil.Process(pid)
    except psutil.NoSuchProcess:
        logging.error(f"ERROR: Process ID {pid} not found.")
        raise
    
    current_time = datetime.datetime.now()
    dir_name = reldatadir / f"{current_time.strftime('%Y_%m_%d-%H_%M')}-{pid}"
    dir_name.mkdir(parents=True, exist_ok=True)

    cpu_hash , processor2corecpu = parse_cpuinfo()

    cpu_details_filename = dir_name / "cpu_details.json"
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

    core_affinity_filename = dir_name / "core_affinity.json"
    with core_affinity_filename.open(mode="w", encoding="utf-8") as caF:
        json.dump(processor_topology, caF, indent=4)


    reference_pid_filename = dir_name / "reference_pid.txt"
    with reference_pid_filename.open(mode="w", encoding="utf-8") as cF:
        cF.write(str(pid))

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
        "process_status",
        "read_count",
        "write_count",
        "read_bytes",
        "write_bytes",
        "read_chars",
        "write_chars",
    ]

    pids_filename = dir_name / "pids.txt"

    pids_cols = [
        "Time",
        "PID",
        "create_time",
    ]

    with pids_filename.open(mode="w", encoding="utf-8") as cH:
        print("\t".join(pids_cols), file=cH)

    agg_metrics = dir_name / "agg_metrics.tsv"

    agg_metrics_cols = [
        "Time",
        "numpids",
        "numthreads",
        "maxprocessors",
        "maxcores",
        "maxcpus",
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

    recorded_pids = dict()

    while p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
        timestamp_str = datetime.datetime.now().strftime(timestamp_format)
        
        children_dicts = []
        children = p.children(recursive=True)
        children.insert(0, p)

        # First pass, gather all
        for child in children:
            child_pid_int = child.pid
            if (child_pid_int in recorded_pids) and recorded_pids[child_pid_int].create_time() == child.create_time():
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
                                'cpu_times',
                                'memory_full_info',
                                'net_connections',
                                'pid',
                                'cpu_percent',
                                'memory_percent',
                                'num_threads',
                                'cpu_num',
                                'cmdline',
                                'create_time',
                                'status',
                                'io_counters',
                            ],
                        )

                        threads_processor_num = set()
                        threads_core_num = set()
                        threads_cpu_num = set()
                        for thr in child_threads:
                            processor_id = str(psutil.Process(thr.id).cpu_num() if thr.id != child_d["pid"] else child_d["cpu_num"])
                            threads_processor_num.add(processor_id)

                            unambiguous_core_id = processor2corecpu[processor_id]
                            threads_core_num.add(unambiguous_core_id)
                            threads_cpu_num.add(unambiguous_core_id[0])

                        child_d["threads_processor_num"] = threads_processor_num
                        child_d["threads_core_num"] = threads_core_num
                        child_d["threads_cpu_num"] = threads_cpu_num

                        children_dicts.append((child_d, mode_w))
            except Exception as e:
                logging.exception("FIXME: Unexpected exception, please report developers")
                pass

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
        for (child_d, mode_w) in children_dicts:
            child_pid = str(child_d["pid"])
            create_time = child_d["create_time"]
            csv_filename = dir_name / f"metrics-{child_pid}_{create_time}.csv"

            if mode_w == "w":
                logging.info(f"Writing data to CSV file {csv_filename.as_posix()}...")

                command_filename = dir_name / f"command-{child_pid}_{create_time}.txt"
                command_json = dir_name / f"command-{child_pid}_{create_time}.json"
                
                with command_filename.open(mode="w", encoding="utf-8") as cF:
                    print(" ".join(child_d["cmdline"]), file=cF)
                # Maybe include more static process metadata in the future
                with command_json.open(mode="w", encoding="utf-8") as cJ:
                    json.dump(child_d["cmdline"], cJ)
                
                with pids_filename.open(mode="a", encoding="utf-8") as cH:
                    creation_timestamp = datetime.datetime.fromtimestamp(create_time).strftime(timestamp_format)
                    print("\t".join((creation_timestamp, child_pid, str(create_time))), file=cH)

            with csv_filename.open(mode=mode_w, encoding="utf-8") as cH:
                if mode_w == "w":
                    print(",".join(metrics_cols), file=cH)
                    
                # Counting TCP connections
                c_conn = child_d["net_connections"]
                tcp_connections = 0
                for c_c in c_conn:
                    if c_c.family == socket.AF_INET and c_c.type == socket.SOCK_STREAM:
                        tcp_connections += 1

                c_cpu = child_d["cpu_times"]
                c_mem = child_d["memory_full_info"]
                c_io = child_d["io_counters"]
                metrics = (
                    timestamp_str,
                    child_pid,
                    str(c_mem.vms),
                    str(c_mem.rss),
                    str(child_d["cpu_percent"]),
                    str(child_d["memory_percent"]),
                    str(tcp_connections),
                    str(child_d["num_threads"]),
                    str(c_cpu.user),
                    str(c_cpu.system),
                    str(c_cpu.children_user),
                    str(c_cpu.children_system),
                    str(c_cpu.iowait),
                    str(c_mem.uss),
                    str(c_mem.swap),
                    str(len(child_d["threads_processor_num"])),
                    str(len(child_d["threads_core_num"])),
                    str(len(child_d["threads_cpu_num"])),
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
                sumuss += c_mem.uss
                sumswap += c_mem.swap
                sumthreads += child_d["num_threads"]
                sum_read_count += c_io.read_count
                sum_write_count += c_io.write_count
                sum_read_bytes += c_io.read_bytes
                sum_write_bytes += c_io.write_bytes
                sum_read_chars += c_io.read_chars
                sum_write_chars += c_io.write_chars
                        
                print(",".join(metrics), file=cH)

        with agg_metrics.open(mode="a", encoding="utf-8") as cH:
            print("\t".join(
                (
                    timestamp_str,
                    str(len(children_dicts)),
                    str(sumthreads),
                    str(len(unique_processors)),
                    str(len(unique_cores)),
                    str(len(unique_cpus)),
                    str(sumuss),
                    str(sumswap),
                    str(sum_read_count),
                    str(sum_write_count),
                    str(sum_read_bytes),
                    str(sum_write_bytes),
                    str(sum_read_chars),
                    str(sum_write_chars),
                )
            ), file=cH)
        
        time.sleep(sleep_secs)


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        if len(sys.argv) >= 4:
            sleep_secs = float(sys.argv[3])
        else:
            sleep_secs = 1
        process_metrics_collector(int(sys.argv[1]), pathlib.Path(sys.argv[2]), sleep_secs=sleep_secs)
    else:
        print(f"Usage: {sys.argv[0]} {{pid}} {{results_dir}} [sleep_secs]", file=sys.stderr)
        sys.exit(1)