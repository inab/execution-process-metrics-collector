#!/bin/bash

# Read collected metrices from the CSV file and plot graphs
#
# This function will end script execution.
#
# This function is to be called after an interrupt like SIGINT or SIGKILL
# is received.
#
function plotGraph() {

  # bring cursor to next line after interrupt
      local csv_filename="$1"
      local dir_name="$(dirname "$csv_filename")"
      local output_filename="${dir_name}/metrics.pdf"
      local command="${dir_name}/command.txt"
      if [ -f "$command" ] ; then
            local commandline="$(<$command)"
            local title="Command \"${commandline}\""
      elif [ -n "$pid" ] ; then
            local title="Process ID $pid"
      else
            local title="Process <unknown>"
      fi
  # plot graphs if there is a data file
  if [ -f "$csv_filename" ]; then
      local creation="$(stat -c '%w' "$csv_filename")"
    gnuplot <<- EOF
      title='$title' . "\n" . '$creation'
      csv_filename='$csv_filename'
      output_filename='$output_filename'
      
      print "Using data from ". csv_filename . "..."
      print "Plotting graphs to ". output_filename
      
      # Set separator to comma
      set datafile separator ","
      
      set xdata time
      set timefmt "%Y-%m-%d %H:%M:%S"
      
      #set term dumb
      #base=""
      #countme=2
      #first(x) = (countme > 0) ? (countme  = countme -1 , base = x, base) : base
      #plot csv_filename using 1:2
      #print sprintf("Esto es una %s",base)
      
      # Output to png with a font size of 10, using pngcairo for anti-aliasing
      #set term pngcairo size 1024,800 noenhanced font "Helvetica,10"
      set term pdfcairo size 29.7cm,21cm enhanced font "Helvetica,10"

      set format x "%H:%M:%S"
      
      # Set border color around the graph
      set border ls 50 lt rgb "#939393"

      # Hide left and right vertical borders
      set border 16 lw 0
      set border 64 lw 0

      # Set tic color
      set tics nomirror textcolor rgb "#939393"

      # Set horizontal lines on the ytics
      set grid ytics lt 1 lc rgb "#d8d8d8" lw 2
      set yrange [0:100]

      set y2tics nomirror

      # Rotate x axis lables
      set xtics rotate

      # Set graph size relative to the canvas
      set size 1,0.95

      # Move legend to the bottom
      set key bmargin center box lt rgb "#d8d8d8" horizontal

      
      # Plot graph,
      # xticlabels(1) - first column as x tic labels
      # "with lines" - line graph
      # "smooth unique"
      # "lw 2" - line width
      # "lt rgb " - line style color
      # "t " - legend labels
      #
      # CPU and memory usage
      #set output dir_name . "/cpu-mem-usage.png"
      



      set output output_filename
      set title "CPU and Memory Usage\n" . title noenhanced
      plot csv_filename using 1:4 with lines smooth unique lw 2 lt rgb "#4848d6" t "CPU Usage %",\
       csv_filename using 1:5 with lines smooth unique lw 2 lt rgb "#b40000" t "Memory Usage %"

      # CPU and memory usage
      set title "CPU, Virtual and Resident Memory Usage\n" . title noenhanced
      plot csv_filename using 1:4 with lines smooth unique lw 2 lt rgb "#4848d6" t "CPU Usage %" axis x1y1,\
       csv_filename using 1:2 with lines smooth unique lw 2 lt rgb "#b40000" t "Virtual memory" axis x1y2, \
       csv_filename using 1:3 with lines smooth unique lw 2 lt rgb "#b48000" t "Resident memory" axis x1y2
      
      # CPU and memory usage
      set title "CPU and Virtual Memory Usage\n" . title noenhanced
      plot csv_filename using 1:4 with lines smooth unique lw 2 lt rgb "#4848d6" t "CPU Usage %" axis x1y1,\
       csv_filename using 1:2 with lines smooth unique lw 2 lt rgb "#b40000" t "Virtual memory" axis x1y2
      
      # CPU and memory usage
      set title "CPU and Resident Memory Usage\n" . title noenhanced
      plot csv_filename using 1:4 with lines smooth unique lw 2 lt rgb "#4848d6" t "CPU Usage %" axis x1y1,\
       csv_filename using 1:3 with lines smooth unique lw 2 lt rgb "#b48000" t "Resident memory" axis x1y2
      
      # TCP count
      #set output dir_name . "/tcp-count.png"
      set title "TCP Connections Count\n" . title noenhanced
      plot csv_filename using 1:4 with lines smooth unique lw 2 lt rgb "#ed8004" t "TCP Connection Count" axis x1y2

      # Thread count
      #set output dir_name . "/thread-count.png"
      set title "Thread Count\n" . title noenhanced
      plot csv_filename using 1:7 with lines smooth unique lw 2 lt rgb "#48d65b" t "Thread Count" axis x1y2

       # All together
       #set output dir_name . "/all-metrices.png"
       set title "All Metrics\n" . title noenhanced
       plot csv_filename using 1:4 with lines smooth unique lw 2 lt rgb "#4848d6" t "CPU Usage %",\
        csv_filename using 1:5 with lines smooth unique lw 2 lt rgb "#b40000" t "Memory Usage %", \
        csv_filename using 1:6 with lines smooth unique lw 2 lt rgb "#ed8004" t "TCP Connection Count", \
        csv_filename using 1:7 with lines smooth unique lw 2 lt rgb "#48d65b" t "Thread Count"
EOF
  fi

}

if [ "$0" == "${BASH_SOURCE[0]}" ] ; then
      for A in "$@" ; do
            plotGraph "$A"
      done
fi
