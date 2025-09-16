#!/usr/bin/env bash

set -eux

BASEDIR="$(cd "$(dirname "$0")"||exit 1; pwd)"

export DCI_LOGIN="${DCI_LOGIN:-admin}"
export DCI_PASSWORD="${DCI_PASSWORD:-admin}"
export DCI_CS_URL="${DCI_CS_URL:-http://localhost}"

function create_venv(){
    rm -rf venv
    python3 -m venv venv
    source venv/bin/activate
    python3 -m pip install --upgrade pip
    python3 --version
    pip --version
    pip install ansible
    pip install dciclient
}

function activate_venv(){
    source venv/bin/activate
}

function debug(){
    ansible --version
    ansible-playbook --version
}

function run_unit_tests() {
    modules='dci_user dci_team dci_topic dci_component dci_feeder dci_product dci_job'

    for module in $modules; do
        ansible-playbook unit-tests/$module/playbook.yml -v
    done
}

function run_plugin_tests() {
    plugins='filter_plugins/version_sort filter_plugins/cmdline_to_json'

    for plugin in $plugins; do
        ansible-playbook unit-tests/${plugin}/playbook.yml -v
    done

    rm -f junit-playbook.xml
    env JUNIT_OUTPUT_DIR=$PWD JUNIT_TEST_CASE_REGEX='(test|validate)_ ' ansible-playbook unit-tests/callback/junit-playbook.yml -vvvv
    test -r junit-playbook.xml
    grep -C 5 "All assertions passed" junit-playbook.xml
}


function run_functional_tests() {

    environments='openstack rhel'
    for environment in $environments; do
        source $BASEDIR/admin.sh
        ansible-playbook "scenario-tests/${environment}/setup_env.yml" -v
        clean_environment

        source ./feeder.sh
        ansible-playbook "scenario-tests/${environment}/feeder.yml" -v
        clean_environment

        source ./remoteci.sh
        ansible-playbook "scenario-tests/${environment}/remoteci.yml" -v
        clean_environment

        rm -f feeder.sh remoteci.sh content.download
    done
}

create_venv
activate_venv
debug

if [[ ! -z ${1+x} ]]; then
    if [[ "$1" == "unit" ]]; then
        run_unit_tests
    elif [[ "$1" == "plugins" ]]; then
        run_plugin_tests
    elif [[ "$1" == "functional" ]]; then
        run_functional_tests
    else
        echo "Usage: run_test.sh [unit|plugins|functional]"
    fi
else
  run_unit_tests
  run_plugin_tests
  run_functional_tests
fi
