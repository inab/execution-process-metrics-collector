# execution-process-metrics-collector
A set of bash scripts to monitor, collect, and visualize metrics of a given Linux process or command line

## Values Collected
1. Virtual memory usage - collected by the `top` command
2. Resident memory Usage - collected by the `top` command
3. CPU Usage - Collected by the `top` command
4. Percentage of memory Usage - Collected by the `top` command
5. TCP Connection Count - Collected by the `lsof` command
6. Thread Count - Collected by the `ps` command

The data is collected at an interval of 1 second (this could vary slightly, but always there will be a minimum of 1 second interval).

The collected data are stored as a CSV file.

## Visualization
The resulting CSV file is translated to a graph image of `.pdf` type using `gnuplot`. This has to be installed (e.g. `apt install gnuplot` in Ubuntu Xenial onwards) before running this script. There is a single pdf, where its pages are separate graphs for all the above metrics, and a separate one containing all of them together for correlation.

## License
Licensed with GNU GPL V3.

This repository is a fork and an evolution from https://github.com/chamilad/process-metrics-collector