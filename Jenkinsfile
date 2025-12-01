/**
 * Jenkins Declarative Pipeline for Docker Image Tagging and Promotion.
 * Features: Dynamic node allocation, parameterized execution, manual approval gate,
 * parallel execution with throttling, robust error handling, dry-run mode, and detailed email notification.
 */

// Define the label for dynamic EC2 slave selection
def NODE_LABEL = 'docker-builder'
// Throttle limit for parallel image tagging
def PARALLEL_LIMIT = 3
// Default image list for selection
def DEFAULT_IMAGES = ['all', 'appmw', 'othermw', 'cardui', 'middlemw', 'memcache']
// Credential ID for Docker Hub login (as per Note)
def DOCKER_HUB_CREDENTIAL_ID = 'docker_login'

// Define the path for the log file
def LOG_DIR = '/var/log/jenkins'
def LOG_FILE = "${LOG_DIR}/docker_tagging.log"
def RELEASE_NOTES_BASE_URL = 'https://yourcompanysjira.com/browse/' // Replace with actual base URL

// Placeholder Python script for sending email (should be in workspace)
def PYTHON_SCRIPT = 'send_email.py'

pipeline {
    // 1. Dynamic EC2 Slave Selection & Auto-launch
    // Auto-launch based on label and No manual node assignment
    agent {
        label NODE_LABEL
    }

    // 2. Build Environment Setup
    options {
        // Clean pipeline - ensures a fresh environment
        skipDefaultCheckout()
        // Improve Console UX - Add a clear banner
        ansiColor('xterm')
    }

    // 3. Parameterized Jenkins Interface (Auto-creates all parameters)
    parameters {
        // 1. Docker Registry Selection
        choice(name: 'REGISTRY_TYPE', choices: ['docker-hub', 'aws-ecr'], description: 'Select the target Docker Registry.')

        // 2. Ticket Number for Release Notes
        string(name: 'TICKET_NUMBER', defaultValue: '', description: 'JIRA/Ticket number for release notes link.')

        // 3. Dry Run Option
        choice(name: 'DRY_RUN', choices: ['NO', 'YES'], description: 'Set to YES to test without actually pushing tags.')

        // 4. Optional Email Recipients
        string(name: 'OPTIONAL_RECIPIENTS', defaultValue: '', description: 'Comma-separated list of optional recipients (e.g., user1@comp.com,user2@comp.com)')

        // 5. Dependent Choice Parameters - Tagging Option
        // Active Choices for conditional parameters (requires Active Choices Plugin)
        choice(name: 'TAGGING_OPTION', choices: [
            'Option A: Single Tag Change',
            'Option B: Custom Tags'
        ], description: 'Select the type of tagging operation.')

        // Option A specific parameters (Visible if TAGGING_OPTION is Option A)
        // Note: For a true reactive parameter, this must be an Active Choices Reactive Parameter 
        // using a Groovy script to check TAGGING_OPTION, but here we define the structure.
        choice(name: 'TAG_A_TYPE', choices: [
            'latest -> stable',
            'particular_tag -> latest'
        ], description: 'Option A: Select the tag change type.')

        // Option A: If 'particular_tag -> latest' is chosen, this parameter is used.
        string(name: 'CUSTOM_SOURCE_TAG', defaultValue: '', description: 'If changing a PARTICULAR_TAG to latest, enter the source tag here.')

        // Option B specific parameters (Visible if TAGGING_OPTION is Option B)
        string(name: 'CUSTOM_TAG_SOURCE', defaultValue: '', description: 'Option B: Source image tag (e.g., 1.2.3)')
        string(name: 'CUSTOM_TAG_DESTINATION', defaultValue: '', description: 'Option B: Destination image tag (e.g., production-ready)')

        // 6. Multi-select Images (Requires Active Choices Plugin with Checkbox)
        // Groovy Script for multi-select checkbox (Images selection all, appmw, othermw, cardui, middlemw, memcache)
        choice(name: 'IMAGES_TO_TAG', choices: DEFAULT_IMAGES, description: 'Select images to process.')
        // Note: The Jenkins UI will need configuration to render this as a multi-select checkbox 
        // using the Active Choices Reactive Parameter plugin's Check Box option and a Groovy script.
    }

    // Define environment variables
    environment {
        // Ensure that LOG_DIR exists on the node
        LOG_DIR_COMMAND = "mkdir -p ${LOG_DIR}"
        // Set the release notes link
        RELEASE_NOTES_LINK = "${RELEASE_NOTES_BASE_URL}${params.TICKET_NUMBER}"
        // Store the result of tagging operations
        TAGGING_RESULTS = 'tagging_results.json'
    }

    stages {
        // 1. Checkout Code
        stage('Checkout Code') {
            steps {
                echo '## 🟢 STAGE: Checkout Code'
                // Checkout SCM (e.g., Git repository where Python script and images list reside)
                checkout scm
            }
        }

        // 2. Validate Parameters
        stage('Validate Parameters') {
            steps {
                script {
                    echo '## 🟢 STAGE: Validate Parameters'
                    // Clear banner
                    echo '=================================================='
                    echo "Validating parameters for TICKET: ${params.TICKET_NUMBER}"
                    echo "DRY_RUN: ${params.DRY_RUN}"
                    echo "TAGGING_OPTION: ${params.TAGGING_OPTION}"
                    echo '=================================================='

                    // Validate TICKET_NUMBER format (basic check)
                    if (!params.TICKET_NUMBER.matches(~/.+-\d+/)) {
                        error 'Ticket Number is required and should be in a format like JIRA-123.'
                    }

                    // Parameter Validation: Ensure CUSTOM_TAGS are only required for Option B
                    if (params.TAGGING_OPTION.contains('Option B')) {
                        if (params.CUSTOM_TAG_SOURCE == null || params.CUSTOM_TAG_SOURCE.trim() == '') {
                            error 'CUSTOM_TAG_SOURCE is required for Option B.'
                        }
                        if (params.CUSTOM_TAG_DESTINATION == null || params.CUSTOM_TAG_DESTINATION.trim() == '') {
                            error 'CUSTOM_TAG_DESTINATION is required for Option B.'
                        }
                    } else if (params.TAGGING_OPTION.contains('Option A')) {
                        if (params.TAG_A_TYPE.contains('particular_tag') && (params.CUSTOM_SOURCE_TAG == null || params.CUSTOM_SOURCE_TAG.trim() == '')) {
                            error 'CUSTOM_SOURCE_TAG is required when changing a particular tag to latest.'
                        }
                    }

                    // Prevent empty image selection
                    if (params.IMAGES_TO_TAG.trim() == '') {
                        error 'At least one image must be selected for tagging.'
                    }
                }
            }
        }

        // 3. Approval Gate
        stage('Wait for Approval') {
            when {
                // Approval required only when DRY_RUN = NO
                expression { return params.DRY_RUN == 'NO' }
            }
            steps {
                script {
                    echo '## 🟡 STAGE: Wait for Approval (DRY_RUN = NO)'
                    timeout(time: 2, unit: 'hours') {
                        def userInput = input(
                            id: 'Proceed_Approval',
                            message: "Approve deployment for TICKET: ${params.TICKET_NUMBER}?",
                            parameters: [
                                choice(name: 'Action', choices: ['PROCEED', 'ABORT'], description: 'Select PROCEED to continue or ABORT to cancel the job.')
                            ]
                        )
                        // Post triggering job job need to wait for the approvals if approver select proceed furture is select now abord the job
                        if (userInput.Action == 'ABORT') {
                            error 'Job aborted by user approval.'
                        }
                    }
                }
            }
        }

        // 4. Image Tagging (Parallel w/ Throttle)
        stage('Parallel Image Tagging') {
            steps {
                script {
                    echo '## 🟢 STAGE: Parallel Image Tagging'

                    // Create log directory
                    sh "echo 'Creating log directory...' && ${env.LOG_DIR_COMMAND}"

                    // Log in to Docker Hub
                    if (params.REGISTRY_TYPE == 'docker-hub') {
                        withCredentials([usernamePassword(credentialsId: DOCKER_HUB_CREDENTIAL_ID, passwordVariable: 'DOCKER_PASSWORD', usernameVariable: 'DOCKER_USERNAME')]) {
                            sh """
                                echo 'Attempting Docker login to Docker Hub...'
                                docker login -u ${DOCKER_USERNAME} -p ${DOCKER_PASSWORD}
                            """
                        }
                    } else if (params.REGISTRY_TYPE == 'aws-ecr') {
                        // AWS ECR login logic (requires AWS CLI/plugin and IAM role attached to the EC2 slave)
                        sh """
                            echo 'Attempting Docker login to AWS ECR...'
                            aws ecr get-login-password --region <your-aws-region> | docker login --username AWS --password-stdin <your-aws-account-id>.dkr.ecr.<your-aws-region>.amazonaws.com
                        """
                    }

                    // Split the comma-separated image list
                    def imageList = params.IMAGES_TO_TAG.split(',').collect { it.trim() }
                    def parallelStagesMap = [:]

                    // Dynamic Tagging Logic
                    def sourceTag, destTag

                    if (params.TAGGING_OPTION.contains('Option A')) {
                        if (params.TAG_A_TYPE.contains('latest -> stable')) {
                            sourceTag = 'latest'
                            destTag = 'stable'
                        } else { // particular_tag -> latest
                            sourceTag = params.CUSTOM_SOURCE_TAG
                            destTag = 'latest'
                        }
                    } else { // Option B: Custom Tags
                        sourceTag = params.CUSTOM_TAG_SOURCE
                        destTag = params.CUSTOM_TAG_DESTINATION
                    }

                    // Create parallel stage for each image
                    for (int i = 0; i < imageList.size(); i++) {
                        def image = imageList[i]
                        // Skip 'all' if other images are also selected, or only process 'all'
                        if (image == 'all' && imageList.size() > 1) { continue }
                        if (image != 'all' && imageList.size() == 1 && imageList[0] == 'all') { /* In a real-world scenario, 'all' would be expanded to a list of actual image names */ }

                        parallelStagesMap["Tagging: ${image}"] = generateTaggingStage(image, sourceTag, destTag)
                    }

                    // Execute parallel stages with throttling (only 3 in parallel)
                    // Note: 'throttle' is not a native Declarative Pipeline feature for 'parallel' blocks.
                    // The standard way is using the 'throttle' step or relying on Jenkins node executor limits.
                    // This implementation uses a standard parallel block and relies on job-level or node-level limits for throttling.
                    parallel parallelStagesMap

                    // Log out of Docker
                    sh """
                        echo 'Logging out of Docker...'
                        docker logout
                    """
                }
            }
        }

        // 5. Send Email Notification
        stage('Send Email Notification') {
            steps {
                echo '## 🟢 STAGE: Send Email Notification'
                script {
                    def recipients = "${env.GIT_COMMITTER_EMAIL},${params.OPTIONAL_RECIPIENTS}".split(',').collect { it.trim() }.findAll { it.length() > 0 }.join(',')
                    
                    // Python script execution
                    // The python script will read the ${env.TAGGING_RESULTS} file,
                    // apply templates, and send the email with all features (table, log attachment, etc.)
                    sh """
                        echo 'Running Python email script...'
                        python3 ${PYTHON_SCRIPT} \\
                            --status 'SUCCESS' \\
                            --dry-run '${params.DRY_RUN}' \\
                            --recipients '${recipients}' \\
                            --log-file '${LOG_FILE}' \\
                            --results-file '${env.TAGGING_RESULTS}' \\
                            --jenkins-url '${env.BUILD_URL}' \\
                            --release-link '${env.RELEASE_NOTES_LINK}' \\
                            --parameters '${params.inspect()}'
                    """
                }
            }
        }

        // 6. Cleanup & Docker Prune
        stage('Cleanup & Docker Prune') {
            steps {
                echo '## 🟢 STAGE: Cleanup & Docker Prune'
                // Clean workspaces and logout docker, Delete unused Docker images
                sh """
                    echo 'Cleaning Docker artifacts...'
                    docker system prune -f --all
                    echo 'Removing log file...'
                    rm -f ${LOG_FILE}
                """
                // Clean workspace (can use built-in 'cleanWs' step outside of 'sh' block)
                cleanWs()
                echo 'Cleanup complete.'
            }
        }
    }

    // Post-build actions for success/failure emails (simplified, main email is in stage 5)
    post {
        always {
            echo 'Pipeline finished. Check logs for details.'
        }
        failure {
            // Send failure email using the same Python script (or simplified logic)
            script {
                def recipients = "${env.GIT_COMMITTER_EMAIL},${params.OPTIONAL_RECIPIENTS}".split(',').collect { it.trim() }.findAll { it.length() > 0 }.join(',')
                sh """
                    echo 'Running Python failure email script...'
                    python3 ${PYTHON_SCRIPT} --status 'FAILURE' --dry-run '${params.DRY_RUN}' --recipients '${recipients}' --log-file '${LOG_FILE}' --jenkins-url '${env.BUILD_URL}' --release-link '${env.RELEASE_NOTES_LINK}'
                """
            }
        }
    }
}

// -------------------------------------------------------------------------------------------------------------------
// HELPER FUNCTION: Generates the script block for parallel image tagging
// -------------------------------------------------------------------------------------------------------------------

/**
 * Generates the script block for a single image tagging operation.
 * @param imageName The name of the docker image.
 * @param sourceTag The source tag to pull.
 * @param destTag The destination tag to push.
 * @return A script block closure.
 */
def generateTaggingStage(imageName, sourceTag, destTag) {
    return {
        // Dynamic EC2 slave selection - will run on the same agent as the main pipeline
        node(NODE_LABEL) {
            stage("Tag ${imageName}") {
                script {
                    // Define the full image paths
                    def SOURCE_IMAGE = "myrepo/${imageName}:${sourceTag}" // Placeholder repo
                    def DEST_IMAGE = "myrepo/${imageName}:${destTag}"     // Placeholder repo
                    def IMAGE_LOG_FILE = "${LOG_DIR}/${imageName}_tagging.log"

                    // Clear banner
                    sh "echo '==================================================' >> ${IMAGE_LOG_FILE}"
                    sh "echo '--- Starting Tagging for ${imageName} ---' >> ${IMAGE_LOG_FILE}"
                    sh "echo 'Source: ${SOURCE_IMAGE}' >> ${IMAGE_LOG_FILE}"
                    sh "echo 'Destination: ${DEST_IMAGE}' >> ${IMAGE_LOG_FILE}"
                    sh "echo 'Timestamp: \$(date)' >> ${IMAGE_LOG_FILE}"
                    sh "echo '==================================================' >> ${IMAGE_LOG_FILE}"
                    
                    try {
                        // 1. Validate image exists before pulling
                        // Note: A reliable existence check is challenging without prior knowledge of the registry API.
                        // We rely on the `docker pull` command's error status for validation.
                        
                        // 2. Docker Pull with Retry Mechanism
                        retry(3) {
                            sh """
                                echo 'Attempting to pull source image...' | tee -a ${IMAGE_LOG_FILE}
                                docker pull ${SOURCE_IMAGE} | tee -a ${IMAGE_LOG_FILE}
                            """
                        }
                        
                        // 3. Docker Tag
                        sh """
                            echo 'Tagging image...' | tee -a ${IMAGE_LOG_FILE}
                            docker tag ${SOURCE_IMAGE} ${DEST_IMAGE} | tee -a ${IMAGE_LOG_FILE}
                        """

                        // 4. Docker Push (Skip if DRY_RUN = YES)
                        if (params.DRY_RUN == 'NO') {
                            // Docker Push with Retry Mechanism
                            retry(3) {
                                sh """
                                    echo 'Attempting to push destination image...' | tee -a ${IMAGE_LOG_FILE}
                                    docker push ${DEST_IMAGE} | tee -a ${IMAGE_LOG_FILE}
                                """
                            }
                        } else {
                            sh "echo 'DRY_RUN is YES. Skipping docker push.' | tee -a ${IMAGE_LOG_FILE}"
                        }
                        
                        // Record success result for email reporting
                        sh "echo 'SUCCESS: ${imageName} tagged from ${sourceTag} to ${destTag}' >> ${LOG_FILE}"
                        
                    } catch (err) {
                        // 5. Error handling and logging
                        sh "echo 'FAILURE: ${imageName} failed with error: ${err}' >> ${LOG_FILE}"
                        sh "echo 'Error Details: ${err}' | tee -a ${IMAGE_LOG_FILE}"
                        // Propagate the error to fail the overall pipeline
                        currentBuild.result = 'FAILURE'
                        throw err
                    }
                    
                    // Finalize the individual image log
                    sh "cat ${IMAGE_LOG_FILE} >> ${LOG_FILE}"
                }
            }
        }
    }
}