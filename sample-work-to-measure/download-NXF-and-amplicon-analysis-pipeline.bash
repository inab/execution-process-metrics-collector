#!/bin/bash

if [ $# -ge 0 ] ; then
	workdir="$1"
else
	workdir="$(mktemp -d --tmpdir treecript_demo_nextflow.XXXXXXXXXX)"
	#workdir=/tmp/ATINA/WORKDIR
	#mkdir -p "$workdir"

	cleanup() {
		set +e
		# This is needed in order to avoid
		# potential "permission denied" messages
		chmod -R u+w "${workdir}"
		rm -rf "${workdir}"
	}

	trap cleanup EXIT
fi

downloadDir="${workdir}/downloads"
softDownloadDir="${workdir}/soft-downloads"
mkdir -p "${softDownloadDir}" "${downloadDir}"

jvm=https://github.com/AdoptOpenJDK/openjdk11-upstream-binaries/releases/download/jdk-11.0.16%2B8/OpenJDK11U-jdk-shenandoah_x64_linux_11.0.16_8.tar.gz
nextflow_version=24.04.6
nextflow=https://github.com/nextflow-io/nextflow/releases/download/v${nextflow_version}/nextflow-${nextflow_version}-all
workflow=https://github.com/EBI-Metagenomics/amplicon-analysis-pipeline/archive/f40c51fa51de3553b3c3e52ab72dc942b485a257.zip

#declare -a input_sample=(
#	https://raw.githubusercontent.com/nf-core/test-datasets/viralrecon/illumina/amplicon/sample1_R1.fastq.gz
#	https://raw.githubusercontent.com/nf-core/test-datasets/viralrecon/illumina/amplicon/sample1_R2.fastq.gz
#	https://raw.githubusercontent.com/nf-core/test-datasets/viralrecon/illumina/amplicon/sample2_R1.fastq.gz
#	https://raw.githubusercontent.com/nf-core/test-datasets/viralrecon/illumina/amplicon/sample2_R2.fastq.gz
#)
declare -a input_sample=(
	https://raw.githubusercontent.com/EBI-Metagenomics/pipeline-v5/master/input_examples/amplicon-paired-ERR2237853_1.fastq.gz
	https://raw.githubusercontent.com/EBI-Metagenomics/pipeline-v5/master/input_examples/amplicon-paired-ERR2237853_2.fastq.gz
	https://raw.githubusercontent.com/EBI-Metagenomics/pipeline-v5/master/input_examples/amplicon-single-ERR1594332.fastq.gz
	https://raw.githubusercontent.com/EBI-Metagenomics/pipeline-v5/master/input_examples/wgs-paired-SRR1620013_1_small.fastq.gz
	https://raw.githubusercontent.com/EBI-Metagenomics/pipeline-v5/master/input_examples/wgs-paired-SRR1620013_2_small.fastq.gz
)

declare ssu_db=https://ftp.ebi.ac.uk/pub/databases/metagenomics/pipelines/tool-dbs/silva-ssu/silva-ssu_138.1.tar.gz
declare lsu_db=https://ftp.ebi.ac.uk/pub/databases/metagenomics/pipelines/tool-dbs/silva-lsu/silva-lsu_138.1.tar.gz
declare unite_db=https://ftp.ebi.ac.uk/pub/databases/metagenomics/pipelines/tool-dbs/unite/unite_9.0.tar.gz
declare itsone_db=https://ftp.ebi.ac.uk/pub/databases/metagenomics/pipelines/tool-dbs/itsonedb/itsonedb_1.141.tar.gz
declare pr2_db=https://ftp.ebi.ac.uk/pub/databases/metagenomics/pipelines/tool-dbs/pr2/pr2_5.0.0.tar.gz
declare rrnas_rfam=https://ftp.ebi.ac.uk/pub/databases/metagenomics/pipelines/tool-dbs/rfam/rfam_14.10.tar.gz
declare genome=R64-1-1
declare genome_source=Ensembl
declare organism=Saccharomyces_cerevisiae
declare igenomes=http://igenomes.illumina.com.s3-website-us-east-1.amazonaws.com/${organism}/Ensembl/${genome}/${organism}_${genome_source}_${genome}.tar.gz

echo Fetching jvm, nextflow and workflow
wget -c -nv -P "${softDownloadDir}" "${jvm}" "${nextflow}" "${workflow}"

echo Sleeping 2 seconds
sleep 2

echo Fetching input and reference files
wget -c -nv -P "${downloadDir}" "${input_sample[@]}" "${ssu_db}" "${lsu_db}" "${unite_db}" "${itsone_db}" "${pr2_db}" "${rrnas_rfam}" "${igenomes}"

NXF_HOME="${workdir}/.nextflow"
export NXF_HOME

echo Sleeping 2 seconds
sleep 2

echo Preparing the layout of the reference files
mkdir -p "${downloadDir}/ssu_db"
tar -x -C "${downloadDir}/ssu_db" -f "${downloadDir}"/silva-ssu_*.tar.gz
mkdir -p "${downloadDir}/lsu_db"
tar -x -C "${downloadDir}/lsu_db" -f "${downloadDir}"/silva-lsu_*.tar.gz
mkdir -p "${downloadDir}/unite_db"
tar -x -C "${downloadDir}/unite_db" -f "${downloadDir}"/unite_*.tar.gz
mkdir -p "${downloadDir}/itsone_db"
tar -x -C "${downloadDir}/itsone_db" -f "${downloadDir}"/itsonedb_*.tar.gz
mkdir -p "${downloadDir}/pr2_db"
tar -x -C "${downloadDir}/pr2_db" -f "${downloadDir}"/pr2_*.tar.gz
mkdir -p "${downloadDir}/rrnas_rfam"
tar -x -C "${downloadDir}/rrnas_rfam" -f "${downloadDir}"/rfam_*.tar.gz
mkdir -p "${downloadDir}/igenomes_base"
tar -x -C "${downloadDir}/igenomes_base" -f "${downloadDir}"/${organism}_${genome_source}_${genome}.tar.gz


echo Sleeping 2 seconds
sleep 2

echo Preparing the layout of software and workflow
softDir="${workdir}/soft"

if [ ! -d "${softDir}" ] ; then
	mkdir -p "${softDir}"

	echo Install JVM
	tar -x -C "${softDir}" -f "${softDownloadDir}"/OpenJDK*
	mv "${softDir}"/openjdk-*/* "${softDir}"

	echo Install Nextflow
	cp -p "${softDownloadDir}"/nextflow* "${softDir}"/bin/nextflow
	chmod +x "${softDir}"/bin/nextflow*

	echo Extract workflow
	unzip -d "${workdir}" "${softDownloadDir}"/*.zip
fi
