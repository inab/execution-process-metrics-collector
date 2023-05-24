#!/bin/bash

scriptdir="$(dirname "${BASH_SOURCE[0]}")"
case "$scriptdir" in
  /*)
    true
    ;;
  .)
    scriptdir="$PWD"
    ;;
  *)
    scriptdir="${PWD}/scriptdir"
    ;;
esac

# Import the plotGraph function
source "${scriptdir}"/plotGraph.sh

# This global variable must be assigned later
csv_filename="/dev/null"
function plotMyGraph() {
  plotGraph "$csv_filename"
}

function process_metrics_collector() {
  local pid="$1"
  local reldatadir="$2"
  local sleep_secs="$3"
  # check if process exists
  kill -0 $pid > /dev/null 2>&1
  local pid_exist=$?

  if [ $pid_exist != 0 ]; then
    echo "ERROR: Process ID $pid not found."
    return 1
  fi

  local current_time=$(date +"%Y_%m_%d-%H_%M")
  local dir_name="${reldatadir}/${current_time}-${pid}"
  # This global variable is initialized here
  csv_filename="${dir_name}/metrics.csv"
  local command_filename="${dir_name}/command.txt"

  # create data directory
  mkdir -p "$dir_name"
  tr '\0' ' ' < /proc/"$pid"/cmdline > "$command_filename"


  # add SIGINT & SIGTERM trap
  trap "plotMyGraph" SIGINT SIGTERM SIGKILL

  echo "Writing data to CSV file $csv_filename..."

  # write CSV headers
  echo "Time,Virt,Res,CPU,Memory,TCP Connections,Thread Count" > "$csv_filename"

  # check if process exists
  kill -0 $pid > /dev/null 2>&1
  pid_exist=$?

  # collect until process exits
  while [ $pid_exist == 0 ]; do
    # check if process exists
    kill -0 $pid > /dev/null 2>&1
    pid_exist=$?

    if [ $pid_exist == 0 ]; then
      # read cpu and mem percentages
      local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
      local cpu_mem_usage=$(top -b -n 1 | grep -w -E "^ *$pid" | awk '{print $5 "," $6 "," $9 "," $10}')
      local tcp_cons=$(lsof -i -a -p $pid -w | tail -n +2 | wc -l)
      local tcount=$(ps -o nlwp h $pid | tr -d ' ')

      # write CSV row
      echo "$timestamp,$cpu_mem_usage,$tcp_cons,$tcount" >> $csv_filename
      sleep "$sleep_secs"
    fi
  done
}

if [ "$0" == "${BASH_SOURCE[0]}" ] ; then
  if [ -z $1 ]; then
    echo "ERROR: Process ID not specified."
    echo
    echo "Usage: $(basename "$0") <PID>"
    exit 1
  fi

  # process id to monitor
  pid="$1"

  process_metrics_collector "$pid" data 1
  # draw graph
  plotMyGraph
fi
