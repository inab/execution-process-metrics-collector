#!/usr/bin/env python

import datetime
import json
import logging
import pathlib
import psutil
import socket
import time
import sys

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
    ]

    recorded_pids = dict()

    while p.is_running():
        timestamp_str = datetime.datetime.now().strftime(timestamp_format)
        
        children = p.children(recursive=True)
        children.insert(0, p)

        for child in children:
            csv_filename = dir_name / f"metrics-{child.pid}.csv"
            if child.pid in recorded_pids:
                mode_w = "a"
                # This is needed for accurate CPU percentages
                child = recorded_pids[child.pid]
            else:
                logging.info(f"Writing data to CSV file {csv_filename.as_posix()}...")

                mode_w = "w"
                recorded_pids[child.pid] = child


                command_filename = dir_name / f"command-{child.pid}.txt"
                command_json = dir_name / f"command-{child.pid}.json"
                
                with command_filename.open(mode="w", encoding="utf-8") as cF:
                    print(" ".join(p.cmdline()), file=cF)
                # Maybe include more static process metadata in the future
                with command_json.open(mode="w", encoding="utf-8") as cJ:
                    json.dump(p.cmdline(), cJ)

            with child.oneshot():
                with csv_filename.open(mode=mode_w, encoding="utf-8") as cH:
                    if mode_w == "w":
                        print(",".join(metrics_cols), file=cH)
                    
                    try:
                        c_cpu = child.cpu_times()
                        c_mem = child.memory_info()
                        
                        # Counting TCP connections
                        c_conn = child.net_connections()
                        tcp_connections = 0
                        for c_c in c_conn:
                            if c_c.family == socket.AF_INET and c_c.type == socket.SOCK_STREAM:
                                tcp_connections += 1

                        metrics = (
                            timestamp_str,
                            str(child.pid),
                            str(c_mem.vms),
                            str(c_mem.rss),
                            str(child.cpu_percent()),
                            str(child.memory_percent()),
                            str(tcp_connections),
                            str(child.num_threads()),
                            str(c_cpu.user),
                            str(c_cpu.system),
                            str(c_cpu.children_user),
                            str(c_cpu.children_system),
                            str(c_cpu.iowait),
                        )
                        
                        print(",".join(metrics), file=cH)
                    except:
                        pass
        
        time.sleep(sleep_secs)


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        process_metrics_collector(int(sys.argv[1]), pathlib.Path(sys.argv[2]))