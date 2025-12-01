pipeline {
    agent { label 'auto-ec2' }

    environment {
        LOGFILE = "/var/log/jenkins/docker_tagging.log"
        DOCKER_LOGIN_CRED = 'docker_login'
        AWS_CREDENTIALS = 'aws-ecr-creds'
    }

    parameters {
        // Basic parameters
        choice(name: 'DOCKER_REGISTRY', choices: ['Docker-hub','AWS-ECR'], description: 'Select Docker Registry')
        string(name: 'TICKET', defaultValue: '', description: 'Ticket / Release Number')
        choice(name: 'DRY_RUN', choices: ['YES','NO'], description: 'Dry run?')
        string(name: 'RECIPIENTS', defaultValue: '', description: 'Optional email recipients, comma-separated')

        // Mode selection
        choice(name: 'MODE', choices: ['OPTION_A','OPTION_B'], description: 'Select tagging mode')

        // Server-side Active Choices for mode-specific fields
        activeChoiceReactiveParam(
            name: 'TAG_PARAMETERS',
            description: 'Show parameters depending on MODE',
            referencedParameters: 'MODE',
            script: '''
def mode = params['MODE'] ?: ''
def html = ""
if (mode == 'OPTION_A') {
    html += """
    <div>
        <label>Latest → Stable Tag:</label>
        <input type='text' name='LATEST_TO_STABLE' value='stable' />
    </div>
    <div>
        <label>Particular Tag → Latest:</label>
        <input type='text' name='PARTICULAR_TO_LATEST' value='' />
    </div>
    """
} else if (mode == 'OPTION_B') {
    html += """
    <div>
        <label>Custom Source Tag:</label>
        <input type='text' name='CUSTOM_TAG1' value='' />
    </div>
    <div>
        <label>Custom Destination Tag:</label>
        <input type='text' name='CUSTOM_TAG2' value='' />
    </div>
    """
}
return html
'''
        )

        // Images selection (checkboxes)
        activeChoiceParam(
            name: 'IMAGES',
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
                echo "Checking out repository..."
                checkout scm
            }
        }

        stage('Validate Parameters') {
            steps {
                script {
                    if (params.MODE == 'OPTION_B') {
                        if (!params.CUSTOM_TAG1?.trim() || !params.CUSTOM_TAG2?.trim()) {
                            error("CUSTOM_TAG1 and CUSTOM_TAG2 are required for Option B")
                        }
                    } else if (params.MODE == 'OPTION_A') {
                        if (!params.LATEST_TO_STABLE?.trim() || !params.PARTICULAR_TO_LATEST?.trim()) {
                            error("LATEST_TO_STABLE and PARTICULAR_TO_LATEST are required for Option A")
                        }
                    }

                    // Normalize image selection
                    def images = params.IMAGES instanceof String ? [params.IMAGES] : params.IMAGES
                    if ('all' in images) {
                        images = ['appmw','othermw','cardui','middlemw','memcache']
                    }
                    env.SELECTED_IMAGES = images.join(',')
                    echo "Selected images: ${env.SELECTED_IMAGES}"
                }
            }
        }

        stage('Approval') {
            when { expression { return params.DRY_RUN == 'NO' } }
            steps {
                script {
                    try {
                        input message: "Approve promotion for ticket ${params.TICKET}?", 
                              ok: "Proceed",
                              submitter: "release-manager,team-lead"
                    } catch (FlowInterruptedException e) {
                        echo "Promotion aborted by approver."
                        currentBuild.result = 'ABORTED'
                        error('Pipeline aborted by user')
                    }
                }
            }
        }

        stage('Image Tagging') {
            steps {
                script {
                    def images = env.SELECTED_IMAGES.split(',')
                    def parallelSteps = [:]
                    for (int i = 0; i < images.size(); i++) {
                        def image = images[i]
                        parallelSteps["Tag-${image}"] = {
                            node {
                                lock(resource: 'docker-slot', quantity: 1) { // throttle max 3
                                    echo "Processing image: ${image}"
                                    sh """
                                    python3 jenkins/scripts/fabfile.py \
                                      --registry ${params.DOCKER_REGISTRY} \
                                      --image ${image} \
                                      --mode ${params.MODE} \
                                      --custom1 '${params.CUSTOM_TAG1 ?: params.PARTICULAR_TO_LATEST}' \
                                      --custom2 '${params.CUSTOM_TAG2 ?: params.LATEST_TO_STABLE}' \
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
                    python3 jenkins/scripts/send_email.py \
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
                echo "Cleaning workspace and Docker..."
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
                python3 jenkins/scripts/send_email.py \
                    --ticket ${params.TICKET} \
                    --recipients "${params.RECIPIENTS}" \
                    --log ${LOGFILE} \
                    --status FAILURE
                """
            }
        }
    }
}
