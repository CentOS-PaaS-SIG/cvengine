env.ghprbGhRepository = env.ghprbGhRepository ?: 'CentOS-PaaS-SIG/ci-pipeline'
env.ghprbActualCommit = env.ghprbActualCommit ?: 'master'
env.ghprbPullAuthorLogin = env.ghprbPullAuthorLogin ?: ''

env.TARGET_BRANCH = env.TARGET_BRANCH ?: 'master'

// Needed for podTemplate()
env.CVENGINE_TAG = env.CVENGINE_TAG ?: 'stable'
env.SLAVE_TAG = env.SLAVE_TAG ?: 'stable'

env.DOCKER_REPO_URL = env.DOCKER_REPO_URL ?: '172.30.1.1:5000'
env.OPENSHIFT_NAMESPACE = env.OPENSHIFT_NAMESPACE ?: 'continuous-infra'
env.OPENSHIFT_SERVICE_ACCOUNT = env.OPENSHIFT_SERVICE_ACCOUNT ?: 'jenkins'

// Audit file for all messages sent.
msgAuditFile = "messages/message-audit.json"

// IRC properties
IRC_NICK = "contra-bot"
IRC_CHANNEL = "#contra-ci-cd"

// Number of times to keep retrying to make sure message is ingested
// by datagrepper
fedmsgRetryCount = 120

// Execution ID for this run of the pipeline
executionID = UUID.randomUUID().toString()

// Pod name to use
podName = 'fedora-atomic-' + executionID + '-' + TARGET_BRANCH

library identifier: "ci-pipeline@${env.ghprbActualCommit}",
        retriever: modernSCM([$class: 'GitSCMSource',
                              remote: "https://github.com/${env.ghprbGhRepository}",
                              traits: [[$class: 'jenkins.plugins.git.traits.BranchDiscoveryTrait'],
                                       [$class: 'RefSpecsSCMSourceTrait',
                                        templates: [[value: '+refs/heads/*:refs/remotes/@{remote}/*'],
                                                    [value: '+refs/pull/*:refs/remotes/origin/pr/*']]]]])
properties(
        [
                buildDiscarder(logRotator(artifactDaysToKeepStr: '30', artifactNumToKeepStr: '', daysToKeepStr: '90', numToKeepStr: '')),
                disableConcurrentBuilds(),
                parameters(
                        [
                                string(description: 'CI Message that triggered the pipeline', name: 'CI_MESSAGE'),
                                string(defaultValue: 'f27', description: 'Fedora target branch', name: 'TARGET_BRANCH'),
                                string(defaultValue: '', description: 'HTTP Server', name: 'HTTP_SERVER'),
                                string(defaultValue: '', description: 'HTTP dir', name: 'HTTP_DIR'),
                                string(defaultValue: 'ci-pipeline', description: 'Main project repo', name: 'PROJECT_REPO'),
                                string(defaultValue: '', description: 'Main topic to publish on', name: 'MAIN_TOPIC'),
                                string(defaultValue: '', description: 'Principal for authenticating with fedora build system', name: 'FEDORA_PRINCIPAL'),
                                string(defaultValue: 'master', description: '', name: 'ghprbActualCommit'),
                                string(defaultValue: 'CentOS-PaaS-SIG/ci-pipeline', description: '', name: 'ghprbGhRepository'),
                                string(defaultValue: '', description: '', name: 'sha1'),
                                string(defaultValue: '', description: '', name: 'ghprbPullId'),
                                string(defaultValue: '', description: '', name: 'ghprbPullAuthorLogin'),
                                string(defaultValue: 'stable', description: 'Tag for rpmbuild image', name: 'SLAVE_TAG'),
                                string(defaultValue: 'stable', description: 'Tag for rpmbuild image', name: 'CVENGINE_TAG'),
                                string(defaultValue: '172.30.1.1:5000', description: 'Docker repo url for Openshift instance', name: 'DOCKER_REPO_URL'),
                                string(defaultValue: 'continuous-infra', description: 'Project namespace for Openshift operations', name: 'OPENSHIFT_NAMESPACE'),
                                string(defaultValue: 'jenkins', description: 'Service Account for Openshift operations', name: 'OPENSHIFT_SERVICE_ACCOUNT'),
                                booleanParam(defaultValue: false, description: 'Force generation of the image', name: 'GENERATE_IMAGE'),
                        ]
                ),
        ]
)

podTemplate(name: podName,
            label: podName,
            cloud: 'openshift',
            serviceAccount: OPENSHIFT_SERVICE_ACCOUNT,
            idleMinutes: 0,
            namespace: OPENSHIFT_NAMESPACE,

        containers: [
                containerTemplate(name: 'jnlp',
                        image: DOCKER_REPO_URL + '/' + OPENSHIFT_NAMESPACE + '/jenkins-continuous-infra-slave:' + SLAVE_TAG,
                        ttyEnabled: false,
                        args: '${computer.jnlpmac} ${computer.name}',
                        command: '',
                        workingDir: '/workDir'),
                // This adds the rpmbuild test container to the pod.
                containerTemplate(name: 'cvengine-ci',
                        alwaysPullImage: true,
                        image: DOCKER_REPO_URL + '/' + OPENSHIFT_NAMESPACE + '/cvengine-ci:' + CVENGINE_TAG,
                        ttyEnabled: true,
                        command: 'cat',
                        privileged: true,
                        workingDir: '/workDir')
        ],
        volumes: [emptyDirVolume(memory: false, mountPath: '/sys/class/net')])
{
    node(podName) {

        def currentStage = ""

        ansiColor('xterm') {
            timestamps {
                // We need to set env.HOME because the openshift slave image
                // forces this to /home/jenkins and then ~ expands to that
                // even though id == "root"
                // See https://github.com/openshift/jenkins/blob/master/slave-base/Dockerfile#L5
                //
                // Even the kubernetes plugin will create a pod with containers
                // whose $HOME env var will be its workingDir
                // See https://github.com/jenkinsci/kubernetes-plugin/blob/master/src/main/java/org/csanchez/jenkins/plugins/kubernetes/KubernetesLauncher.java#L311
                //
                env.HOME = "/root"
                //
                try {
                    // Prepare our environment
                    currentStage = "prepare-environment"
                    stage(currentStage) {
                        deleteDir()
                        // Set our default env variables
                        pipelineUtils.setDefaultEnvVars()
                        // Prepare Credentials (keys, passwords, etc)
                        //pipelineUtils.prepareCredentials()
                        // Decorate our build
                        pipelineUtils.updateBuildDisplayAndDescription()
                        // Gather some info about the node we are running on for diagnostics
                        pipelineUtils.verifyPod(OPENSHIFT_NAMESPACE, env.NODE_NAME)
                    }

                    currentStage = "cvengine-ci"
                    stage(currentStage) {
                        // Set stage specific vars
                        //pipelineUtils.setStageEnvVars(currentStage)

                        // Run functional tests
                        pipelineUtils.executeInContainer(currentStage, "cvengine-ci", "/cvengine/ci/run_cvengine_ci.sh")
                    }

                } catch (e) {
                    // Set build result
                    currentBuild.result = 'FAILURE'

                    // Report the exception
                    echo "Error: Exception from " + currentStage + ":"
                    echo e.getMessage()

                    // Throw the error
                    throw e

                } finally {
                    // Set the build display name and description
                    pipelineUtils.setBuildDisplayAndDescription()

                    pipelineUtils.getContainerLogsFromPod(OPENSHIFT_NAMESPACE, env.NODE_NAME)

                    // Archive our artifacts
                    step([$class: 'ArtifactArchiver', allowEmptyArchive: true, artifacts: '**/logs/**,*.txt,*.groovy,**/job.*,**/*.groovy,**/inventory.*', excludes: '**/job.props,**/job.props.groovy,**/*.example', fingerprint: true])

                }
            }
        }
    }
}
