# Sample work to test `treecript` and other technical metrics collectors

This directory contains a series of bash scripts which automate several
tasks which can be used as sample work to test the different capabilities
of technical metrics collectors like `treecript`.

* [download-and-test-linux-6.6.bash](download-and-test-linux-6.6.bash) is a script
  which fetches content compressed with two different algorithms (in this case,
  public snapshots of the Linux Kernel source code) to a temporary directory,
  and tests the integrity of both archives as well as lists their internal
  contents. It assumes both `tar`, `gunzip` and `unxz` are available.

* [download-and-run-nextflow-workflow.bash](download-and-run-nextflow-workflow.bash):
  This script fetches into a temporary directory both an old variant
  calling workflow written in Nextflow v1, as well as all its
  dependencies: a JVM; a capable old nextflow engine;
  the inputs; the reference datasets; ... Once all is fetched the layout
  is prepared to be able to run the workflow using the inputs and DBs.
  It assumes `docker` is properly setup, up and running for the user using
  the script.

* [download-NXF-and-amplicon-analysis-pipeline.bash](download-NXF-and-amplicon-analysis-pipeline.bash)
  and [run-downloaded-NXF-and-amplicon-analysis-pipeline.bash](run-downloaded-NXF-and-amplicon-analysis-pipeline.bash):
  The first bash script fetches to a given input working directory the workflow
  [amplicon-analysis-pipeline v6.0.4](https://github.com/EBI-Metagenomics/amplicon-analysis-pipeline/tree/v6.0.4),
  as well as all the input, database and software pre-conditions. Once all the
  content is fetched, the directories layout expected by the workflow is
  prepared.
  
  The second bash script takes as input a working directory already prepared
  by the previous script, as well as an output directory. This last one
  will be used to store the results computed by the workflow when it uses
  the fetched inputs.

