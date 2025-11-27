#!/bin/bash

scriptDir="$(dirname "$(realpath "$0")")"

if [ $# -ge 1 ] ; then
	workdir="$1"
	outputdir="$2"
else
	echo "Usage: $0 {workdir} {outputdir}"
	exit 1
fi

if [ ! -d "$workdir" ] ; then
	"$SHELL" "$scriptDir"/download-NXF-and-amplicon-analysis-pipeline.bash "$workdir"
fi

downloadDir="${workdir}/downloads"
softDir="${workdir}/soft"

JAVA_HOME="${softDir}"
export JAVA_HOME
PATH="${softDir}/bin:$PATH"
export PATH

workflowDir="$(echo "${workdir}"/amplicon-analysis-pipeline-*)"

declare genome=R64-1-1
declare genome_source=Ensembl
declare organism=Saccharomyces_cerevisiae
declare igenomes_base="${downloadDir}"/igenomes_base

declare igenomes_prefix="${igenomes_base}"/${organism}/${genome_source}/${genome}

echo Creating input and yaml run files
#cat > "${workdir}"/inputs.csv <<EOF
#sample,fastq_1,fastq_2,single_end
#SAMPLE1_PE,${downloadDir}/sample1_R1.fastq.gz,${downloadDir}/sample1_R2.fastq.gz,false
#SAMPLE2_PE,${downloadDir}/sample2_R1.fastq.gz,${downloadDir}/sample2_R2.fastq.gz,false
#EOF
# SAMPLE3_SE,${downloadDir}/sample1_R1.fastq.gz,,true
# SAMPLE3_SE,${downloadDir}/sample2_R1.fastq.gz,,true
cat > "${workdir}"/inputs.csv <<EOF
sample,fastq_1,fastq_2,single_end
ERR2237853,${downloadDir}/amplicon-paired-ERR2237853_1.fastq.gz,${downloadDir}/amplicon-paired-ERR2237853_2.fastq.gz,false
ERR1594332,${downloadDir}/amplicon-single-ERR1594332.fastq.gz,,true
SRR1620013,${downloadDir}/wgs-paired-SRR1620013_1_small.fastq.gz,${downloadDir}/wgs-paired-SRR1620013_2_small.fastq.gz,false
EOF

cat > "${workdir}"/input_params.yml <<EOF
input: ${workdir}/inputs.csv

ssu_db_fasta: ${downloadDir}/ssu_db/SILVA-SSU.fasta
ssu_db_tax: ${downloadDir}/ssu_db/SILVA-SSU-tax.txt
ssu_db_otu: ${downloadDir}/ssu_db/SILVA-SSU.otu
ssu_db_mscluster: ${downloadDir}/ssu_db/SILVA-SSU.fasta.mscluster

lsu_db_fasta: ${downloadDir}/lsu_db/SILVA-LSU.fasta
lsu_db_tax: ${downloadDir}/lsu_db/SILVA-LSU-tax.txt
lsu_db_otu: ${downloadDir}/lsu_db/SILVA-LSU.otu
lsu_db_mscluster: ${downloadDir}/lsu_db/SILVA-LSU.fasta.mscluster

unite_db_fasta: ${downloadDir}/unite_db/UNITE.fasta
unite_db_tax: ${downloadDir}/unite_db/UNITE-tax.txt
unite_db_otu: ${downloadDir}/unite_db/UNITE.otu
unite_db_mscluster: ${downloadDir}/unite_db/UNITE.fasta.mscluster

itsone_db_fasta: ${downloadDir}/itsone_db/ITSone.fasta
itsone_db_tax: ${downloadDir}/itsone_db/ITSone-tax.txt
itsone_db_otu: ${downloadDir}/itsone_db/ITSone.otu
itsone_db_mscluster: ${downloadDir}/itsone_db/ITSone.fasta.mscluster

pr2_db_fasta: ${downloadDir}/pr2_db/PR2.fasta
pr2_db_tax: ${downloadDir}/pr2_db/PR2-tax.txt
pr2_db_otu: ${downloadDir}/pr2_db/PR2.otu
pr2_db_mscluster: ${downloadDir}/pr2_db/PR2.fasta.mscluster

rrnas_rfam_covariance_model: ${downloadDir}/rrnas_rfam/
rrnas_rfam_claninfo: ${downloadDir}/rrnas_rfam/ribo.clan_info

genome: ${genome}
igenomes_base: ${igenomes_base}
genomes:
  R64-1-1:
    fasta: ${igenomes_prefix}/Sequence/WholeGenomeFasta/genome.fa
    bwa: ${igenomes_prefix}/Sequence/BWAIndex/version0.6.0/
    bowtie2: ${igenomes_prefix}/Sequence/Bowtie2Index/
    star: ${igenomes_prefix}/Sequence/STARIndex/
    bismark: ${igenomes_prefix}/Sequence/BismarkIndex/
    gtf: ${igenomes_prefix}/Annotation/Genes/genes.gtf
    bed12: ${igenomes_prefix}/Annotation/Genes/genes.bed

validationSchemaIgnoreParams: genomes

outdir: ${outputdir} 
EOF

cat > "${workdir}"/custom.conf <<EOF
docker {
    enabled = true
    autoMounts = true
    registry = "quay.io"
}
EOF

nextflow run "${workflowDir}" -c "${workdir}"/custom.conf -params-file "${workdir}"/input_params.yml
