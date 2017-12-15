# Overview
The Container Validation Engine (CVEngine) provides a framework for validating
containers on a target container platform.

CVEngine is intended to be used in many phases of a container's lifecycle,
including:

  * When a developer wants to test their container
  * When Quality Engineering is verifying a new build
  * When preparing to release a container to production
  * etc.

Additionally, CVEngine can be used to validate a new build of a container
platform itself by deploying a newly built instance of the platform then
testing containers on top of it.

## Architecture
CVEngine is broken into four main components:

### cvengine.py
This module is the main entrypoint into container validation and orchestrates
the process end to end.

### Container Validation Data
This module, CVData, encapsulates all configuration information about a
running container validation scenario.  A CVData object will be instantiated
in cvengine.py then passed to each subsequent component.

NOTE: This component does not actually exist yet, but will be implemented
shortly.

### Environment Handlers
CVEngine will have the capability to execute a container validation against
a preexisting container platform as well as to deploy a target platform
on they fly. Environment handlers are responsible for provisioning and
connecting to the host or hosts that a container platform will run on.

For container platforms that have already been deployed, this could be as
simple as needing to know the IP address and credentials for the container
platform host. For more complex scenarios, CVEngine might need to deploy
VMs, bootstrap a node to host a container, etc. Environment handlers provide
the mechanisms for doing all of this.

A BaseEnvironmentHandler class provides the common functionality for
environment handlers, then child classes will exist for each environment
that we want to support. These could include, but are not limited to:

  * Environments that have already been provisioned
  * RHEL hosts that need to be bootstrapped to run a container
  * OpenStack instances where CVEngine needs to provision instances, volumes,
    etc.
  * OpenShift instances where CVEngine will deploy containers against
  * etc.

NOTE: Environment handlers do not actually exist yet. Currently, the only
mode that is supported is running against an Atomic host instance that
has already been provisioned. I've included this section to illustrate
the target architecture for CVEngine.

### Platform Handlers
Platform handlers encapsulate the core logic for interacting with containers
on a container platform. Specifically, these wrap commands for deploying a
container, fetching artifacts from a container, cleaning up a running
container, etc.

For initial versions of container validation, the following platforms
will be supported:

  * Atomic host (rhel, fedora, centos, etc.) This is the only platform
    that is supported today.
  * OpenShift
  * Docker (a generic host running docker, RHEL, Fedora, etc.)

# Usage
## Prerequisites
Prior to executing a container validation, you must create the following:

### Metadata File
A metadata file (cvdata) must be created to instruct the CVEngine how to
run the validation. Full documentation for the metadata file specification
does not yet exist, but there is a sample file in the ```example```
directory of this repository.

### Test playbooks
A set (minimum of one) of Ansible playbooks should be created to deploy
and test your container on the target container platform. Full documentation
for the ansible playbook specification does not yet exist, but there is a
sample playbook in the ```example``` directory of this repository. The
URLs to these playbooks should be specified in the metadata file for the
target platform on which you would like your container to be validated.

## Installation
CVEngine can currently only be installed from source by cloning the
repository and running the following from the repository root:

```python setup.py install```
or
```pip install .```

## Execution
### Using cvengine command
At install time, a command, ```cvengine``` is placed in your $PATH. This will
pull input parameters from environment variables and execute the specified
container validation. The following environment variables must be set:

  * CV_IMAGE_URL: Location of the container image. In most cases,
    this should be a string that can be passed to the "docker pull"
    command. Alternatively, this could be a full URL to a file that
    gets fetched by the test playbooks and then loaded in docker.
    The latter method is not handled by the cvengine and is left to
    the playbooks to implement.
  * CV_CVDATA_URL: Location of the cvdata metadata file
  * CV_CONFIG: The json/yaml-formatted container validation config, which
    includes environment and platform configuration options. NOTE: the
    specific format of this config will be documented more fully shortly. Also
    note that the CVEngine code may be refactored to allow for more easily
    passing in configuration via command line options. For now, this method
    was chosen to allow faster implementation of core features and usage
    modes.
  * CV_ARTIFACTS_DIRECTORY: A directory on the host where cvengine is running
    where any artifacts will be placed after the container validation
    executes
  * CV_EXTRA_VARS: An optional json/yaml-formatted string containing extra
    variables to be passed to the deploy/test playbooks. Any variables
    specified here will be passed to all playbooks.

### As a python module
CVEngine can be included as a module in another python script using code
similar to the following:

```python
import cvengine
...
cvengine.run_container_validation(agrs...)
```

See the docstring on the run_container_validation function in
cvengine/cvengine.py for information on required arguments.

### As a docker container
The Dockerfile included in this repository can be used to build a container
image with cvengine and all of its dependencies installed. To build the
image, clone the repository, then run ```docker build .``` from the root of
the repository. Note that the state of the cvengine code deployed in the image
will match the state in your local checkout of the cvengine repository.
This is handy for testing new code changes, or for running a target branch
or version of cvengine.

At container runtime, the cvengine command is executed. See the section
above on running the cvengine command for notes on environment variables
that must be specified when running the container.
