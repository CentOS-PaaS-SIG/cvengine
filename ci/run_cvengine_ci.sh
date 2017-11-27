#! /bin/bash

# Make sure we have or have downloaded the test
if [ -z "${TEST_SUBJECTS:-}" ]; then
    echo "No subject defined"
    exit
fi


echo "Checking if file exists"
if [ ! -f ${TEST_SUBJECTS:-} ]; then
    echo "Downloading test subject"
    wget -q -O testimage.qcow2 ${TEST_SUBJECTS}
    export TEST_SUBJECTS=${PWD}/testimage.qcow2
    echo "Test file written to $TEST_SUBJECTS"
else
    echo "File found"
fi


echo "Running container validation playbook"
ansible-playbook -v --inventory=$ANSIBLE_INVENTORY \
        --extra-vars "subjects=$TEST_SUBJECTS" \
        /cvengine/ci/run_cvengine_ci.yaml
