# execution-process-metrics-collector
A python program and a set of bash scripts to monitor, collect, and visualize metrics of a given Linux process or command line, and its descendants.

## Files created and values collected

The data is collected at an interval of 1 second (this could vary slightly, but always there will be a minimum of 1 second interval).

A directory is created for each execution being inspected. Each directory has next files:

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

* `metrics-{pid}_{create_time}.csv`: A comma-separated values file containing the time series of metrics associated to the process **{pid}** which was created at **{create_time}**.
  * Timestamp.
  * Process pid.
  * Virtual memory.
  * Resident memory.
  * Percentage of CPU (it can be more than 100 for multithread processes).
  * Percentage of memory used.
  * Number of TCP connections.
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