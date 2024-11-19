# execution-process-metrics-collector
A python program and a set of bash scripts to monitor, collect, and visualize metrics of a given Linux process or command line, and its descendants.

## Files created and values collected by `process-metrics-collector.py`

This python program uses [psutil](https://github.com/giampaolo/psutil) library to collect the samples at an interval of 1 second (this could vary slightly, but always there will be a minimum of 1 second interval).

A subdirectory is created for each execution being inspected, whose name is based on when the sample collection started and the process. Each subdirectory has next files:

* `reference_pid.txt`: The pid of the main process being inspected.

* `pids.txt`: A tabular file containing when each descendant process being spawned was created and the assigned pid.

* `agg_metrics.tsv`: A tabular file containing the time series of aggregated metrics.
  * Timestamp.
  * Number of pids monitored in that moment.
  * Number of threads.
  * Number of CPUs where all the processes and threads were running.
  * User memory associated to all the monitored processes.
  * Swap memory associated to all the monitored processes.

* `command-{pid}_{create_time}.txt`: For each created process **{pid}** which was created at **{create_time}**, a file containing the linearized command line is created.

* `command-{pid}_{create_time}.json`: For each created process **{pid}** which was created at **{create_time}**, a file containing the JSON representation of the command line is created.

* `metrics-{pid}_{create_time}.csv`: A comma-separated values file containing the time series of metrics associated to the process **{pid}** which was created at **{create_time}**. The documentation is based on [psutil.Process.memory_info](https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_info), [psutil.Process.cpu_percent](https://psutil.readthedocs.io/en/latest/#psutil.Process.cpu_percent), [psutil.Process.memory_percent](https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_percent), [psutil.Process.num_threads](https://psutil.readthedocs.io/en/latest/#psutil.Process.num_threads), [psutil.Process.cpu_times](https://psutil.readthedocs.io/en/latest/#psutil.Process.cpu_times) and [psutil.Process.memory_full_info](https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_full_info).

  * `Time`: Sample timestamp.
  * `PID`: Process pid.
  * `Virt`: aka "Virtual Memory Size", this is the total amount of virtual memory used by the process. On UNIX it matches `top`‘s VIRT column. On Windows this is an alias for pagefile field and it matches "Mem Usage" "VM Size" column of `taskmgr.exe`.
  * `Res`: aka "Resident Set Size", this is the non-swapped physical memory a process has used. On UNIX it matches `top`‘s RES column. On Windows this is an alias for wset field and it matches "Mem Usage" column of `taskmgr.exe`.
  * `CPU`: Return a float representing the process CPU utilization as a percentage which can also be > 100.0 in case of a process running multiple threads on different CPUs.
  * `Memory`: Compare process memory to total physical system memory and calculate process [RSS](https://en.wikipedia.org/wiki/Resident_set_size) memory utilization as a percentage.
  * `TCP connections`: number of open TCP connections (useful to understand whether the process is connecting to network resources).
  * `Thread Count`: The number of threads currently used by this process (non cumulative).
  * `User`: time spent in user mode (in seconds). When a multithreaded, CPU intensive process can run in parallel, it can be bigger than the elapsed time since the process was started.
  * `System`: time spent in kernel mode (in seconds). A high system time usage indicates lots of system calls, which might be a clue of an inefficient or an I/O intensive process (e.g. database operations).
  * `Children_User`: user time of all child processes (always 0 on Windows and macOS).
  * `Children_System`: system time of all child processes (always 0 on Windows and macOS).
  * `IO`: (Linux) time spent waiting for blocking I/O to complete. This value is excluded from user and system times count (because the CPU is not doing any work). Intensive operations (like swap related ones) in slow storage are the main source of these stalls.
  * `uss`: (Linux, macOS, Windows) aka “Unique Set Size”, this is the memory which is unique to a process and which would be freed if the process was terminated right now.
  * `swap`: (Linux) amount of memory that has been swapped out to disk. It is a sign either of a memory hungry process or a process with memory leaks.
  * `cpu_num`: Number of unique CPU cores used by the process. For instance, if a process has 20 threads, but there are only available 4 processor cores, the value would be at most 4. The number of available processor cores is determined by the scheduler and the processor affinity (the cores where the process is allowed to run) attached to the process.

  * Cumulative process user time.
  * Cumulative process system time.
  * Cumulative process user time, including children. 
  * Cumulative process system time, including children.
  * Percentage of I/O wait.
  * User memory of the process.
  * Swap memory of the process.
  * Number of CPUs where the threads of the process are running.

## Visualization
The resulting CSV file is translated to a graph image of `.pdf` type using `gnuplot`. This has to be installed (e.g. `apt install gnuplot` in Ubuntu Xenial onwards) before running this script. There is a single pdf, where its pages are separate graphs for all the above metrics, and a separate one containing all of them together for correlation.

## License
Licensed with GNU GPL V3.

This repository is a fork and an evolution from https://github.com/chamilad/process-metrics-collector