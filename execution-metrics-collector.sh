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

# Redefine process_metrics_collector to use newer implementation
function process_metrics_collector() {
  python "${scriptdir}"/process-metrics-collector.py "$@"
}

if [ "$0" == "${BASH_SOURCE[0]}" ] ; then
  if [ $# -lt 2 ]; then
    echo "ERROR: Command line not properly specified."
    echo
    echo "Usage: $(basename "$0") {metrics_dir} <command line to be run>"
    exit 1
  fi

  # Save the path to the metrics directory
  metrics_dir="$1"
  shift

  # Execute the program
  "$@" &

  # process id to monitor
  pid=$!

  process_metrics_collector "$pid" "$metrics_dir" 1
  # draw graphs (to be revamped)
  plotGraph /dev/null
fi
