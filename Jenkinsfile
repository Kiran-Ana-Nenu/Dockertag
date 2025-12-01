pipeline {
    agent { label 'auto-ec2' }

    environment {
        LOGFILE = "/var/log/jenkins/docker_tagging.log"
        DOCKER_LOGIN_CRED = 'docker_login'
        AWS_CREDENTIALS = 'aws-ecr-creds'
    }

    parameters {
        choice(name: 'DOCKER_REGISTRY', choices: ['Docker-hub','AWS-ECR'], description: 'Select Docker Registry')
        string(name: 'TICKET', defaultValue: '', description: 'Ticket / Release Number')
        choice(name: 'DRY_RUN', choices: ['YES','NO'], description: 'Dry run?')
        string(name: 'RECIPIENTS', defaultValue: '', description: 'Optional email recipients, comma-separated')
        choice(name: 'MODE', choices: ['LATEST_PROMOTE','CUSTOM_TAGS'], description: 'Select tagging mode')
        string(name: 'CUSTOM_TAG1', defaultValue: '', description: 'Source or first custom tag')
        string(name: 'CUSTOM_TAG2', defaultValue: '', description: 'Destination or second custom tag')
        // Active Choices parameters (server-side)
        // MODE_GROOVY disables CUSTOM_TAG fields if not CUSTOM_TAGS
        activeChoiceReactiveReferenceParam(
            name: 'MODE_GROOVY',
            referencedParameters: 'MODE,CUSTOM_TAG1,CUSTOM_TAG2',
            description: 'Reactive server-side parameter to enable/disable CUSTOM_TAG fields',
            script: ''' 
def mode = params['MODE'] ?: ''
def customTag1 = params['CUSTOM_TAG1'] ?: ''
def customTag2 = params['CUSTOM_TAG2'] ?: ''
def disabledAttr = (mode != 'CUSTOM_TAGS') ? 'disabled="true"' : ''
return """
<div style='margin:5px 0;'>
<label>CUSTOM_TAG1:</label>
<input type='text' name='CUSTOM_TAG1' value='${customTag1}' ${disabledAttr} />
</div>
<div style='margin:5px 0;'>
<label>CUSTOM_TAG2:</label>
<input type='text' name='CUSTOM_TAG2' value='${customTag2}' ${disabledAttr} />
</div>
"""
'''
        )
        activeChoiceParam(
            name: 'IMAGES_GROOVY',
            description: 'Select images to process',
            choiceType: 'CHECKBOX',
            script: '''
return ['all','appmw','othermw','cardui','middlemw','memcache']
'''
        )
    }

    stages {
        stage('Checkout Code') {
            steps {
                echo "Checking out code..."
                checkout scm
            }
        }

        stage('Validate Parameters') {
            steps {
                script {
                    if (params.MODE == 'CUSTOM_TAGS') {
                        if (!params.CUSTOM_TAG1?.trim() || !params.CUSTOM_TAG2?.trim()) {
                            error("CUSTOM_TAG1 and CUSTOM_TAG2 are required for CUSTOM_TAGS mode")
                        }
                    }
                }
            }
        }

        stage('Approval') {
            when {
                expression { return params.DRY_RUN == 'NO' }
            }
            steps {
                script {
                    try {
                        def user = input(
                            id: 'Approval', 
                            message: "Approve promotion for ticket ${params.TICKET}?", 
                            parameters: [
                                [$class: 'TextParameterDefinition', defaultValue: '', description: 'Optional note', name: 'APPROVER_NOTE']
                            ],
                            submitter: 'release-manager,team-lead', 
                            submitterParameter: 'approver'
                        )
                        echo "Approval received: ${user}"
                    } catch (FlowInterruptedException e) {
                        echo "Approval aborted by user or timeout - aborting pipeline"
                        currentBuild.result = 'ABORTED'
                        error('Promotion aborted by approver')
                    }
                }
            }
        }

        stage('Prepare Images') {
            steps {
                script {
                    def selectedImages = params.IMAGES_GROOVY instanceof String ? [params.IMAGES_GROOVY] : params.IMAGES_GROOVY
                    if ('all' in selectedImages) {
                        selectedImages = ['appmw','othermw','cardui','middlemw','memcache']
                    }
                    echo "Selected images: ${selectedImages}"
                    env.SELECTED_IMAGES = selectedImages.join(',')
                }
            }
        }

        stage('Image Tagging') {
            steps {
                script {
                    def images = env.SELECTED_IMAGES.split(',')
                    def parallelSteps = [:]
                    for (int i=0; i<images.size(); i++) {
                        def image = images[i]
                        parallelSteps["Tag-${image}"] = {
                            node {
                                lock(resource: 'docker-slot', quantity: 1) { // throttle 3 concurrent
                                    echo "Processing image: ${image}"
                                    sh """
                                    python3 scripts/fabfile.py \
                                      --registry ${params.DOCKER_REGISTRY} \
                                      --image ${image} \
                                      --mode ${params.MODE} \
                                      --custom1 ${params.CUSTOM_TAG1} \
                                      --custom2 ${params.CUSTOM_TAG2} \
                                      --dry-run ${params.DRY_RUN}
                                    """
                                }
                            }
                        }
                    }
                    parallel parallelSteps
                }
            }
        }

        stage('Send Email Notification') {
            steps {
                script {
                    sh """
                    python3 scripts/send_email.py \
                    --ticket ${params.TICKET} \
                    --recipients "${params.RECIPIENTS}" \
                    --log ${LOGFILE} \
                    --status SUCCESS
                    """
                }
            }
        }

        stage('Cleanup & Docker Prune') {
            steps {
                echo "Cleaning workspace, Docker logout and pruning unused images..."
                sh """
                docker system prune -af || true
                docker logout || true
                """
            }
        }
    }
    post {
        failure {
            script {
                sh """
                python3 scripts/send_email.py \
                --ticket ${params.TICKET} \
                --recipients "${params.RECIPIENTS}" \
                --log ${LOGFILE} \
                --status FAILURE
                """
            }
        }
    }
}
