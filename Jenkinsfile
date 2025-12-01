/**
 * Jenkins Declarative Pipeline for Docker Image Tagging and Promotion.
 * Executes core logic using Fabric (fabfile.py).
 * Features: Dynamic node allocation, parameterized execution, manual approval, 
 * parallel execution with throttling, error handling, dry-run mode, and detailed email notification.
 */

// --- Configuration Variables ---
def NODE_LABEL = 'docker-builder' // For Dynamic EC2 Slave Selection
def PARALLEL_LIMIT = 3            // Parallelism Control (Throttle)
def DOCKER_HUB_CREDENTIAL_ID = 'docker_login' // Credential ID from Jenkins (as per Note)
def LOG_DIR = '/var/log/jenkins'
def LOG_FILE = "${LOG_DIR}/docker_tagging.log"
def RESULTS_FILE = 'tagging_results.json' // Stores results for email script
def RELEASE_NOTES_BASE_URL = 'https://yourcompanysjira.com/browse/' // Update this base URL

pipeline {
    // Dynamic EC2 Slave Selection & Auto-launch based on label
    agent {
        label NODE_LABEL
    }

    options {
        // Clean pipeline & Console UX Improvements (Clear Banners)
        skipDefaultCheckout()
        ansiColor('xterm')
        timeout(time: 3, unit: 'hours')
    }

    // Parameterized Jenkins Interface (Active Choices required for dynamic/multi-select)
    parameters {
        // 1. Docker Registry Selection
        choice(name: 'REGISTRY_TYPE', choices: ['docker-hub', 'aws-ecr'], description: 'Select the target Docker Registry.')

        // 2. Ticket Number for Release Notes Link
        string(name: 'TICKET_NUMBER', defaultValue: '', description: 'JIRA/Ticket number for release notes link (e.g., PROJ-123).')

        // 3. Dry Run Option
        choice(name: 'DRY_RUN', choices: ['NO', 'YES'], description: 'Set to YES to test tagging without actually pushing.')

        // 4. Optional Email Recipients
        string(name: 'OPTIONAL_RECIPIENTS', defaultValue: '', description: 'Comma-separated list of optional recipients (e.g., user1@comp.com,user2@comp.com)')

        // 5. Dependent Tagging Choice (Requires Active Choices Plugin for reactivity)
        choice(name: 'TAGGING_OPTION', choices: [
            'Option A: Single Tag Change',
            'Option B: Custom Tags'
        ], description: 'Select the type of tag change.')

        // --- Reactive Parameters for Option A/B visibility/requirements ---
        // Option A parameters:
        choice(name: 'TAG_A_TYPE', choices: [
            'latest->stable',
            'particular_tag->latest'
        ], description: 'Option A: Select the standard tag change.')
        string(name: 'CUSTOM_SOURCE_TAG', defaultValue: '', description: 'Required for "particular_tag->latest" option.')

        // Option B parameters:
        string(name: 'CUSTOM_TAG_SOURCE', defaultValue: '', description: 'Option B: Source image tag (e.g., 1.2.3)')
        string(name: 'CUSTOM_TAG_DESTINATION', defaultValue: '', description: 'Option B: Destination image tag (e.g., production-ready)')

        // 6. Multi-select Images (Active Choices Parameter - Checkbox)
        // NOTE: In the Jenkins UI, this must be configured as a multi-select Active Choices Parameter.
        choice(name: 'IMAGES_TO_TAG', choices: ['all', 'appmw', 'othermw', 'cardui', 'middlemw', 'memcache'], description: 'Select images to process (Multi-select checkbox).')
    }

    environment {
        // Log setup
        LOG_DIR_COMMAND = "mkdir -p ${LOG_DIR}"
        
        // Links
        RELEASE_NOTES_LINK = "${RELEASE_NOTES_BASE_URL}${params.TICKET_NUMBER}"
        BUILD_INFO = "Jenkins Job: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
    }

    stages {
        // 1. Checkout Code
        stage('Checkout Code') {
            steps {
                echo '## 🟢 STAGE 1: Checkout Code'
                checkout scm
                // Ensure the scripts folder is accessible
                sh "${env.LOG_DIR_COMMAND}"
            }
        }

        // 2. Validate Parameters
        stage('Validate Parameters') {
            steps {
                script {
                    echo '## 🟢 STAGE 2: Validate Parameters'
                    // Add Console UX Improvements
                    echo '=================================================='
                    echo "Validating parameters for TICKET: ${params.TICKET_NUMBER}"
                    echo '=================================================='

                    // Check for TICKET_NUMBER
                    if (params.TICKET_NUMBER == null || params.TICKET_NUMBER.trim() == '') {
                        error 'Ticket Number is required.'
                    }

                    // Prevent empty image selection
                    if (params.IMAGES_TO_TAG.trim() == '') {
                        error 'Image selection cannot be empty.'
                    }

                    // Parameter Validation: Conditional requirements
                    if (params.TAGGING_OPTION.contains('Option B')) {
                        if (params.CUSTOM_TAG_SOURCE == null || params.CUSTOM_TAG_SOURCE.trim() == '' ||
                            params.CUSTOM_TAG_DESTINATION == null || params.CUSTOM_TAG_DESTINATION.trim() == '') {
                            error 'CUSTOM_TAG_SOURCE and CUSTOM_TAG_DESTINATION are required for Option B.'
                        }
                    } else if (params.TAGGING_OPTION.contains('Option A')) {
                        if (params.TAG_A_TYPE.contains('particular_tag') && (params.CUSTOM_SOURCE_TAG == null || params.CUSTOM_SOURCE_TAG.trim() == '')) {
                            error 'CUSTOM_SOURCE_TAG is required for particular_tag->latest.'
                        }
                    }
                }
            }
        }

        // 3. Wait for Approval
        stage('Wait for Approval') {
            when {
                // NO approval required if DRY_RUN = YES
                expression { return params.DRY_RUN == 'NO' }
            }
            steps {
                script {
                    echo '## 🟡 STAGE 3: Wait for Approval (DRY_RUN = NO)'
                    // Post triggering job job need to wait for the approvals
                    def userInput = input(
                        id: 'ReleaseApproval',
                        message: "Approve tagging and promotion for TICKET: **${params.TICKET_NUMBER}**?",
                        parameters: [
                            choice(name: 'Action', choices: ['PROCEED', 'ABORT'], description: 'Select PROCEED to continue the promotion or ABORT to cancel the job.')
                        ]
                    )
                    // If approver select now abord the job
                    if (userInput.Action == 'ABORT') {
                        error 'Job aborted by user approval.'
                    }
                }
            }
        }

        // 4. Image Tagging (ONLY Fabric execution, Parallel w/ Throttle)
        stage('Image Tagging') {
            steps {
                script {
                    echo '## 🟢 STAGE 4: Image Tagging (Fabric Execution)'
                    
                    // Log in to Docker using credentials/IAM Role
                    sh 'echo "Logging in to Docker Registry..."'
                    if (params.REGISTRY_TYPE == 'docker-hub') {
                        withCredentials([usernamePassword(credentialsId: DOCKER_HUB_CREDENTIAL_ID, passwordVariable: 'DOCKER_PASSWORD', usernameVariable: 'DOCKER_USERNAME')]) {
                            sh "docker login -u ${DOCKER_USERNAME} -p ${DOCKER_PASSWORD}"
                        }
                    } else if (params.REGISTRY_TYPE == 'aws-ecr') {
                        // Assumes AWS CLI and IAM Role is configured on the 'docker-builder' node
                        sh 'aws ecr get-login-password --region <YOUR_REGION> | docker login --username AWS --password-stdin <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com'
                    }

                    // Construct Fabric command arguments
                    def taggingArgs = ""
                    if (params.TAGGING_OPTION.contains('Option A')) {
                        if (params.TAG_A_TYPE.contains('latest->stable')) {
                            taggingArgs = "--tag-type latest_to_stable"
                        } else { // particular_tag->latest
                            taggingArgs = "--tag-type custom_to_latest --custom-source-tag ${params.CUSTOM_SOURCE_TAG}"
                        }
                    } else { // Option B
                        taggingArgs = "--tag-type custom_to_custom --source-tag ${params.CUSTOM_TAG_SOURCE} --destination-tag ${params.CUSTOM_TAG_DESTINATION}"
                    }

                    // Execute Fabric command
                    // Fabric handles: No duplication of logic, Parallelism (using multiprocessing/threads inside fabfile), 
                    // Throttle (controlled inside fabfile), Error handling, Retry Mechanism, Logging.
                    sh """
                        cd scripts
                        fab -f fabfile.py tag_images: \
                            --images='${params.IMAGES_TO_TAG}' \
                            --dry-run='${params.DRY_RUN}' \
                            --parallel-limit=${PARALLEL_LIMIT} \
                            --log-file='../${LOG_FILE}' \
                            --results-file='../${RESULTS_FILE}' \
                            ${taggingArgs}
                        cd ..
                    """

                    // Log out of Docker
                    sh 'echo "Logging out of Docker..." && docker logout'
                }
            }
        }

        // 5. Send Email Notification (Python script)
        stage('Send Email Notification') {
            steps {
                echo '## 🟢 STAGE 5: Send Email Notification'
                script {
                    def recipients = "${env.GIT_COMMITTER_EMAIL},${params.OPTIONAL_RECIPIENTS}".split(',').collect { it.trim() }.findAll { it.length() > 0 }.join(',')
                    
                    // Execute the Python script for modern, styled email with table and logs.
                    sh """
                        echo 'Running Python email script...'
                        python3 scripts/send_email.py \\
                            --status 'SUCCESS' \\
                            --recipients '${recipients}' \\
                            --log-file '${LOG_FILE}' \\
                            --results-file '${RESULTS_FILE}' \\
                            --jenkins-url '${env.BUILD_URL}' \\
                            --release-link '${env.RELEASE_NOTES_LINK}' \\
                            --build-info '${BUILD_INFO}' \\
                            --dry-run-status '${params.DRY_RUN}' \\
                            --parameters-json '${groovy.json.JsonOutput.toJson(params)}'
                    """
                }
            }
        }

        // 6. Cleanup & Docker Prune
        stage('Cleanup & Docker Prune') {
            steps {
                echo '## 🟢 STAGE 6: Cleanup & Docker Prune'
                // Delete unused Docker images, clean workspaces
                sh """
                    echo 'Cleaning Docker artifacts...'
                    docker system prune -f --all --volumes || true
                    echo 'Cleaning log files...'
                    rm -f ${LOG_FILE} ${RESULTS_FILE}
                """
                // Clean workspace
                cleanWs(deleteDirs: true)
                echo 'Cleanup complete.'
            }
        }
    }

    // Post-build actions for FAILURE email
    post {
        failure {
            script {
                echo '## 🔴 Post-Build: Failure Notification'
                def recipients = "${env.GIT_COMMITTER_EMAIL},${params.OPTIONAL_RECIPIENTS}".split(',').collect { it.trim() }.findAll { it.length() > 0 }.join(',')
                
                // Execute failure email template
                sh """
                    echo 'Running Python failure email script...'
                    python3 scripts/send_email.py \\
                        --status 'FAILURE' \\
                        --recipients '${recipients}' \\
                        --log-file '${LOG_FILE}' \\
                        --jenkins-url '${env.BUILD_URL}' \\
                        --release-link '${env.RELEASE_NOTES_LINK}' \\
                        --build-info '${BUILD_INFO}' \\
                        --dry-run-status '${params.DRY_RUN}' \\
                        --parameters-json '${groovy.json.JsonOutput.toJson(params)}'
                """
            }
        }
    }
}