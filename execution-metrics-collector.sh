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
source "${scriptdir}"/process-metrics-collector.sh

if [ "$0" == "${BASH_SOURCE[0]}" ] ; then
  if [ $# -eq 0 ]; then
    echo "ERROR: Command line not specified."
    echo
    echo "Usage: $(basename "$0") <command line to be run>"
    exit 1
  fi

  # Execute the program
  "$@" &

  # process id to monitor
  pid=$!

  process_metrics_collector "$pid" data_cmd 1
  # draw graph
  plotMyGraph
fi
