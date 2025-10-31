#!/bin/bash

workdir="$(mktemp -d --tmpdir treecript_demo.XXXXXXXXXX)"

cleanup() {
	set +e
	# This is needed in order to avoid
	# potential "permission denied" messages
	chmod -R u+w "${workdir}"
	rm -rf "${workdir}"
}

trap cleanup EXIT

file1=https://www.kernel.org/pub/linux/kernel/v6.x/linux-6.6.114.tar.gz
file2=https://www.kernel.org/pub/linux/kernel/v6.x/linux-6.6.114.tar.xz

echo Fetching first file "${file1}"
wget -nv -P "${workdir}" "${file1}"
echo Sleeping 2 seconds
sleep 2
echo Fetching second file "${file2}"
wget -nv -P "${workdir}" "${file2}"
echo Sleeping 2 more seconds
sleep 2
echo Testing integrity of first file
gunzip -t "${workdir}"/*.gz
tar tf "${workdir}"/*.gz
echo Sleeping the last 2 seconds
sleep 2
echo Testing integrity of second file
xz -T -t "${workdir}"/*.xz
tar tf "${workdir}"/*.xz
