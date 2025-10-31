#!/bin/bash

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

downloadDir="${workdir}/downloads"
mkdir -p "${downloadDir}"

jvm=https://github.com/AdoptOpenJDK/openjdk11-upstream-binaries/releases/download/jdk-11.0.16%2B8/OpenJDK11U-jdk-shenandoah_x64_linux_11.0.16_8.tar.gz
#nextflow=https://github.com/nextflow-io/nextflow/releases/download/v24.04.0/nextflow-24.04.0-all
nextflow=https://github.com/nextflow-io/nextflow/releases/download/v19.04.1/nextflow-19.04.1-all
workflow=https://github.com/inab/Wetlab2Variations/archive/31348ed533961f84cf348bf1af660ad9de6f870c.zip

declare -a general_rawreads=(
	ftp://ftp-trace.ncbi.nih.gov/giab/ftp/data/NA12878/NIST_NA12878_HG001_HiSeq_300x/140407_D00360_0017_BH947YADXX/Project_RM8398/Sample_U5c/U5c_CCGTCC_L001_R1_001.fastq.gz
	ftp://ftp-trace.ncbi.nih.gov/giab/ftp/data/NA12878/NIST_NA12878_HG001_HiSeq_300x/140407_D00360_0017_BH947YADXX/Project_RM8398/Sample_U5c/U5c_CCGTCC_L001_R2_001.fastq.gz
)

declare general_referencegenome=ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz

declare -a BSQR_files=(
	ftp://ftp.broadinstitute.org/bundle/b37/Mills_and_1000G_gold_standard.indels.b37.vcf.gz
	ftp://ftp.broadinstitute.org/bundle/b37/dbsnp_138.b37.vcf.gz
)

declare -a BSQR_indexes=(
	ftp://ftp.broadinstitute.org/bundle/b37/Mills_and_1000G_gold_standard.indels.b37.vcf.idx.gz
	ftp://ftp.broadinstitute.org/bundle/b37/dbsnp_138.b37.vcf.idx.gz
)

bwamem_rgheader='@RG\tID:H947YADXX\tSM:NA12878\tPL:ILLUMINA'

echo Fetching jvm, nextflow and workflow
wget -c -nv -P "${downloadDir}" "${jvm}" "${nextflow}" "${workflow}"

echo Sleeping 2 seconds
sleep 2

echo Fetching input files
wget -c -nv -P "${downloadDir}" "${general_rawreads[@]}" "${general_referencegenome}"
wget -c -nv -P "${downloadDir}" --user=gsapubftp-anonymous --password=  "${BSQR_files[@]}" "${BSQR_indexes[@]}"

echo Sleeping 2 more seconds
sleep 2

softDir="${workdir}/soft"

if [ ! -d "${softDir}" ] ; then
	mkdir -p "${softDir}"

	echo Install JVM
	tar -x -C "${softDir}" -f "${downloadDir}"/OpenJDK*
	mv "${softDir}"/openjdk-*/* "${softDir}"

	echo Install Nextflow
	cp -p "${downloadDir}"/nextflow* "${softDir}"/bin/nextflow
	chmod +x "${softDir}"/bin/nextflow*

	echo Extract workflow
	unzip -d "${workdir}" "${downloadDir}"/*.zip
fi

JAVA_HOME="${softDir}"
export JAVA_HOME
PATH="${softDir}/bin:$PATH"
export PATH

echo Creating yaml run file
cat > "${workdir}"/input_params.yml <<EOF
general:
  rawreads:
    - ${downloadDir}/U5c_CCGTCC_L001_R1_001.fastq.gz
    - ${downloadDir}/U5c_CCGTCC_L001_R2_001.fastq.gz
  referencegenome: ${downloadDir}/hs37d5.fa.gz
BSQR:
  files:
    - ${downloadDir}/Mills_and_1000G_gold_standard.indels.b37.vcf.gz
    - ${downloadDir}/dbsnp_138.b37.vcf.gz
  indexes:
    - ${downloadDir}/Mills_and_1000G_gold_standard.indels.b37.vcf.idx.gz
    - ${downloadDir}/dbsnp_138.b37.vcf.idx.gz
bwamem:
  rgheader: '${bwamem_rgheader}'
outputDir: ${workdir}/OUTPUTS
metricsDir: ${workdir}/WFMETRICS
EOF

nextflow run "${workdir}"/Wetlab2Variations-*/nextflow -params-file "${workdir}"/input_params.yml
