// Needed for podTemplate()
env.CVENGINE_TAG = env.CVENGINE_TAG ?: 'stable'
env.SLAVE_TAG = env.SLAVE_TAG ?: 'stable'

env.DOCKER_REPO_URL = env.DOCKER_REPO_URL ?: '172.30.254.79:5000'
env.OPENSHIFT_NAMESPACE = env.OPENSHIFT_NAMESPACE ?: 'continuous-infra'
env.OPENSHIFT_SERVICE_ACCOUNT = env.OPENSHIFT_SERVICE_ACCOUNT ?: 'jenkins'

// Execution ID for this run of the pipeline
executionID = UUID.randomUUID().toString()

// Pod name to use
podName = 'cvengine-' + executionID

library identifier: "ci-pipeline@master",
        retriever: modernSCM([$class: 'GitSCMSource',
                              remote: "https://github.com/CentOS-Paas-SIG/ci-pipeline"])
properties(
        [
                buildDiscarder(logRotator(artifactDaysToKeepStr: '30', artifactNumToKeepStr: '', daysToKeepStr: '90', numToKeepStr: '')),
                parameters(
                        [
                                string(defaultValue: 'stable', description: 'Tag for Jenkins slave image', name: 'SLAVE_TAG'),
                                string(defaultValue: 'stable', description: 'Tag for cvengine image', name: 'CVENGINE_TAG'),
                                string(defaultValue: '172.30.254.79:5000', description: 'Docker repo url for Openshift instance', name: 'DOCKER_REPO_URL'),
                                string(defaultValue: 'continuous-infra', description: 'Project namespace for Openshift operations', name: 'OPENSHIFT_NAMESPACE'),
                                string(defaultValue: 'jenkins', description: 'Service Account for Openshift operations', name: 'OPENSHIFT_SERVICE_ACCOUNT'),
                                string(defaultValue: 'alpine', description: 'The container image to be validated', name: 'CVENGINE_IMAGE_URL'),
                                string(defaultValue: 'https://raw.githubusercontent.com/CentOS-PaaS-SIG/cvengine/master/example/cvdata.yml', description: 'The container validation metadata file URL', name: 'CVENGINE_METADATA_URL'),
                                string(defaultValue: 'atomic', description: 'The container platform to validate the container against', name: 'CVENGINE_TARGET_PLATFORM'),
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
                containerTemplate(name: 'cvengine',
                        alwaysPullImage: true,
                        image: DOCKER_REPO_URL + '/' + OPENSHIFT_NAMESPACE + '/cvengine:' + CVENGINE_TAG,
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
                        // Decorate our build
                        pipelineUtils.updateBuildDisplayAndDescription()
                        // Gather some info about the node we are running on for diagnostics
                        pipelineUtils.verifyPod(OPENSHIFT_NAMESPACE, env.NODE_NAME)
                    }

                    currentStage = "cvengine"
                    stage(currentStage) {
                        // Set stage specific vars
                        env."CV_IMAGE_URL" = "${env.CVENGINE_IMAGE_URL}"
                        env."CV_CVDATA_URL" = "${env.CVENGINE_METADATA_URL}"
                        env."CV_TARGET_PLATFORM" = "${env.CVENGINE_TARGET_PLATFORM}"

                        // Run the container validation
                        pipelineUtils.executeInContainer(currentStage, "cvengine", "/cvengine/ci/run_cvengine.py")
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
                    // Set the build display name
                    currentBuild.displayName = "Build#: ${env.BUILD_NUMBER} - Image: ${env.CVENGINE_IMAGE_URL} - Platform: ${env.CVENGINE_TARGET_PLATFORM}"

                    pipelineUtils.getContainerLogsFromPod(OPENSHIFT_NAMESPACE, env.NODE_NAME)

                    // Archive our artifacts
                    step([$class: 'ArtifactArchiver', allowEmptyArchive: true, artifacts: '**/logs/**,*.txt,*.groovy,**/job.*,**/*.groovy,**/inventory.*', excludes: '**/job.props,**/job.props.groovy,**/*.example', fingerprint: true])

                }
            }
        }
    }
}
