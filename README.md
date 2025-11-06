# `treecript`: Process tree metrics transcriptor (originally `Execution Process Metrics Collector`)

A set of python programs and a set of bash scripts to monitor, collect, and digest metrics of a given Linux process or command line, and its descendants.

These programs have been initially developed for ELIXIR STEERS.

## Files created and values collected by `process-metrics-collector.py`

This python program uses [psutil](https://github.com/giampaolo/psutil) library to collect the samples at an interval of 1 second (this could vary slightly, but always there will be a minimum of 1 second interval).

A subdirectory is created for each execution being inspected, whose name is based on when the sample collection started and the process. Each subdirectory has next files:

* `reference_pid.txt`: The pid of the main process being inspected.

* `sampling-rate-seconds.txt`: The sampling rate, in seconds (usually 1).

* `pids.txt`: A tabular file containing when each descendant process being spawned was created and the assigned pid.

  * `Time`: Sample timestamp (first time the process was detected).
  * `PID`: Process id.
  * `create_time`: When the process was created.
  * `PPID`: Parent process id. It is a '-' for the root process being monitored.
  * `ppid_create_time`: When the parent process was created. It is a '-' for the root process being monitored.

* `agg_metrics.tsv`: A tabular file containing the time series of aggregated metrics.

  * Timestamp.
  * Number of pids monitored in that moment.
  * Number of threads.
  * Number of different processors where all the processes and threads were running.
  * Number of different cores where all the processes and threads were running.
  * Number of different physical CPUs where all the processes and threads were running.
  * Ids of the physical CPUs, separated by spaces. This is needed for future, accurate computation of carbon footprint of the computation.
  * User memory associated to all the monitored processes.
  * Swap memory associated to all the monitored processes.
  * Number of read operations performed by all the active processes.
  * Number of write operations performed by all the active processes.
  * Number of bytes physically read by all the active processes.
  * Number of bytes physically written by all the active processes.
  * Number of bytes read (either physically or from cache) by all the active processes.
  * Number of bytes written (either physically or from cache) by all the active processes.

* `command-{pid}_{create_time}.txt`: For each created process **{pid}** which was created at **{create_time}**, a file containing the linearized command line is created.

* `command-{pid}_{create_time}.json`: For each created process **{pid}** which was created at **{create_time}**, a file containing the JSON representation of the command line is created.

* `metrics-{pid}_{create_time}.csv`: A comma-separated values file containing the time series of metrics associated to the process **{pid}** which was created at **{create_time}**. The documentation is based on [psutil.Process.memory_info](https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_info), [psutil.Process.cpu_percent](https://psutil.readthedocs.io/en/latest/#psutil.Process.cpu_percent), [psutil.Process.memory_percent](https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_percent), [psutil.Process.num_threads](https://psutil.readthedocs.io/en/latest/#psutil.Process.num_threads), [psutil.Process.cpu_times](https://psutil.readthedocs.io/en/latest/#psutil.Process.cpu_times) and [psutil.Process.memory_full_info](https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_full_info).

  * `Time`: Sample timestamp.
  * `PID`: Process id.
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
  * `processor_num`: Number of unique processors used by the process. For instance, if a process has 20 threads, but there are only available 4 processors, the value would be at most 4. The number of available processors is determined by the scheduler and the processor affinity (the processors where the process is allowed to run) attached to the process.
  * `core_num`: Number of unique CPU cores used by the process. For instance, if a process has 20 threads, but there are only available 4 processors which are in 2 different CPU cores, the value would be at most 2. The number of available CPU cores is indirectly determined by the scheduler and the processor affinity (the cores of the processors where the process is allowed to run) attached to the process.
  * `cpu_num`: Number of unique physical CPUs used by the process. For instance, if a process has 20 threads, but there are only available 4 processors which are in 2 different cores of the same physical CPU, the value would be 1. The number of available physical CPUs is indirectly determined by the scheduler and the processor affinity (the physical CPUs of the cores of the processors where the process is allowed to run) attached to the process.
  * `processor_ids`: Ids of the CPU processors, separated by spaces. This could be needed for future, accurate computation of carbon footprint of the computation.
  * `core_ids`: Ids of the CPU cores, separated by spaces. This could be needed for future, accurate computation of carbon footprint of the computation.
  * `cpu_ids`: Ids of the physical CPUs, separated by spaces. This is needed for future, accurate computation of carbon footprint of the computation.
  * `process_status`: String describing the process status.
  * `read_count`: the number of read operations performed (cumulative). This is supposed to count the number of read-related syscalls such as read() and pread() on UNIX.
  * `write_count`: the number of write operations performed (cumulative). This is supposed to count the number of write-related syscalls such as write() and pwrite() on UNIX.
  * `read_bytes`: the number of bytes read in physical disk I/O (for instance, cache miss) (cumulative). Always -1 on BSD.
  * `write_bytes`: the number of bytes written in physical disk I/O (for instance, after a flush to the storage) (cumulative). Always -1 on BSD.
  * `read_chars`: the amount of bytes which this process passed to read() and pread() syscalls (cumulative). Differently from read_bytes it doesn’t care whether or not actual physical disk I/O occurred (Linux specific).
  * `write_chars`: the amount of bytes which this process passed to write() and pwrite() syscalls (cumulative). Differently from write_bytes it doesn’t care whether or not actual physical disk I/O occurred (Linux specific).

* `cpu_details.json`: Parsed information from `/proc/cpuinfo` about the physical CPUs available in the system. Parts of this information are needed for future computation of carbon footprint of the tracked process subtree.

* `core_affinity.json`: Parsed information derived from `/proc/cpuinfo`, which provides the list of processors, as well as the ids of the physical core and CPU where they are.

You have a sample directory obtained from measuring a workflow execution using WfExS-backend workflow orchestrator at
[sample-series/Wetlab2Variations_metrics/2025_05_20-02_19-14001](sample-series/Wetlab2Variations_metrics/2025_05_20-02_19-14001) using an old version.

The command line is something like:

```bash
python execution-metrics-collector.py {base_metrics_directory} {command line} {and} {parameters}
```

The equivalent old wrapper version would be:

```bash
./execution-metrics-collector.sh {base_metrics_directory} {command line} {and} {parameters}
```

which in its code is just running the command in background, getting the `pid` of the process and running next line with `sample_period` equals to 1 second:

```bash
python process-metrics-collector.py {pid} {base_metrics_directory} {sample_period}
```

For instance, the sample directory was obtained just running next command line:

```bash
~/projects/treecript/execution-metrics-collector.sh ~/projects/treecript/Wetlab2Variations_metrics python WfExS-backend.py -L workflow_examples/local_config.yaml staged-workdir offline-exec 01a1db90-1508-4bad-beb7-7f7989838542
```

## Time series charts
The program `plotGraph.py` is a replacement for the original `plotGraph.sh`. It generates
several line charts for each monitored process, comparing the time series of
interesting metrics.

```bash
python plotGraph.py sample-series/Wetlab2Variations_metrics/2025_05_20-02_19-14001/ dest_directory
```

## Digestion

The program `tdp-finder.py` helps to obtain the TDP of an Intel processor, using the gathered metadata stored at `cpu_details.json` within the series directory.

Repository https://github.com/felixsteinke/cpu-spec-dataset contains at
[dataset](https://github.com/felixsteinke/cpu-spec-dataset/tree/main/dataset) subdirectory several tables in CSV format with
this and other details for many Intel, AMD and Ampere processors. The key column here is `ProcessorNumber`.

Forked repository https://github.com/JosuaCarl/cpu-spec-dataset contains at
[dataset](https://github.com/JosuaCarl/cpu-spec-dataset/tree/main/dataset) subdirectory tables in CSV similar to the ones from original repo, but with different column names. The key column here to match the processor is `Processor Number`.

Usage would be something like next:

```bash
git clone https://github.com/felixsteinke/cpu-spec-dataset
python tdp-finder.py sample-series/Wetlab2Variations_metrics/2025_05_20-02_19-14001/ cpu-spec-dataset/dataset/intel-cpus.csv 
```

```
TDP (ConfigTDPMax) => 28.0 W
```

or

```bash
git clone https://github.com/JosuaCarl/cpu-spec-dataset cpu-spec-dataset_Josua
python tdp-finder.py sample-series/Wetlab2Variations_metrics/2025_05_20-02_19-14001/ cpu-spec-dataset_Josua/dataset/intel-cpus.csv 
```

```
TDP (Configurable TDP-up) => 28.0 W
```

The program `metrics-aggregator.py` is an initial proof of concept to digest the gathered process tree time series. As it tries
computing the Wh of each part being executed, it needs the TDP (Thermal Design Power) or similar from the CPU.

For instance, getting all the consumptions from main steps of a workflow execution (which was using docker for its steps)
and it was collected, would be:

```bash
python metrics-aggregator.py sample-series/Wetlab2Variations_metrics/2025_05_20-02_19-14001/ dest_directory 28.0 "docker run"
```

```
                     id                                               task       W_h    joules        first_sample         last_sample        duration  duration_in_s
8   1747700411.64_14234                             8 jlaitinen/lftpalpine  0.000023  0.083231 2025-05-20 02:20:12 2025-05-20 02:20:59 0 days 00:00:47             47
11  1747700460.91_14462         11 quay.io/biocontainers/samtools:1.3.1--5  0.000012  0.044520 2025-05-20 02:21:02 2025-05-20 02:21:30 0 days 00:00:28             28
15  1747700493.64_14760  15 quay.io/biocontainers/cutadapt:1.18--py36h1...  0.000193  0.694440 2025-05-20 02:21:34 2025-05-20 02:23:28 0 days 00:01:54            114
28  1747700608.04_15216         28 quay.io/biocontainers/picard:2.18.25--0  0.000006  0.020150 2025-05-20 02:23:29 2025-05-20 02:23:51 0 days 00:00:22             22
32  1747700632.46_15945    32 quay.io/biocontainers/bwa:0.7.17--h84994c4_5  0.001796  6.464617 2025-05-20 02:23:53 2025-05-20 03:23:29 0 days 00:59:36           3576
35  1747704216.72_18987                            35 jlaitinen/lftpalpine  0.000038  0.138433 2025-05-20 03:23:37 2025-05-20 03:24:50 0 days 00:01:13             73
38   1747704311.5_19163    38 quay.io/biocontainers/bwa:0.7.17--h84994c4_5  0.001231  4.432096 2025-05-20 03:25:12 2025-05-20 03:50:00 0 days 00:24:48           1488
41  1747705802.95_20626         41 quay.io/biocontainers/samtools:1.3.1--5  0.000075  0.269880 2025-05-20 03:50:04 2025-05-20 03:51:18 0 days 00:01:14             74
44  1747705879.32_20820         44 quay.io/biocontainers/picard:2.18.25--0  0.000065  0.232261 2025-05-20 03:51:20 2025-05-20 03:54:49 0 days 00:03:29            209
48  1747706089.46_21177                      48 broadinstitute/gatk3:3.6-0  0.000348  1.254288 2025-05-20 03:54:50 2025-05-20 04:17:46 0 days 00:22:56           1376
51  1747707464.95_22167                      51 broadinstitute/gatk3:3.6-0  0.000063  0.226953 2025-05-20 04:17:46 2025-05-20 04:21:21 0 days 00:03:35            215
54  1747707680.85_22476                      54 broadinstitute/gatk3:3.6-0  0.000460  1.656543 2025-05-20 04:21:22 2025-05-20 04:38:39 0 days 00:17:17           1037
57  1747708718.81_23312                      57 broadinstitute/gatk3:3.6-0  0.000266  0.959036 2025-05-20 04:38:39 2025-05-20 04:53:24 0 days 00:14:45            885
60  1747709607.25_24083                      60 broadinstitute/gatk3:3.6-0  0.000131  0.472472 2025-05-20 04:53:28 2025-05-20 04:57:30 0 days 00:04:02            242
```

The `dest_directory` will also contain the process call graph represented both as a tree (`graph.pdf`) and as a spiral (`spiral-graph.pdf`):

![Sample process call graph (tree)](sample-charts/graph.svg)![Sample process call graph (spiral)](sample-charts/spiral-graph.svg)

a barplot representation of both task consumptions and duration and an horizontal lollipop representing the task executions relative start, duration and end:

![Sample task consumptions and duration barplots](sample-charts/consumptions.svg)![Sample task executions lollipop](sample-charts/timeline.svg)

## Visualization (outdated)
The resulting CSV file is translated to a graph image of `.pdf` type using `gnuplot`. This has to be installed (e.g. `apt install gnuplot` in Ubuntu Xenial onwards) before running this script. There is a single pdf, where its pages are separate graphs for all the above metrics, and a separate one containing all of them together for correlation.

## License
Licensed with GNU GPL V3.

This repository is a fork and an evolution from https://github.com/chamilad/process-metrics-collector
