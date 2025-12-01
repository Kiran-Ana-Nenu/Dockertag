/**
 * Jenkins Declarative Pipeline for Docker Image Tagging and Promotion.
 * Executes core logic using Fabric (fabfile.py) scripts.
 * * NOTE: The global 'agent none' setting requires you to uncomment and define 
 * an 'agent' block within the stages that execute actual work (Stage 1, 4, 5, 6).
 */

// --- Configuration Variables (Defined outside pipeline block for safety) ---
// If you want to use specific nodes, uncomment the line below and use the 
// variable in an 'agent { label NODE_LABEL }' block in your stages.
// def NODE_LABEL = 'docker-builderT || docker-builderM || docker-builderR' 
def PARALLEL_LIMIT = 3            
def DOCKER_HUB_CREDENTIAL_ID = 'docker_login' // Credential ID for Docker Hub
def LOG_DIR = '/var/log/jenkins'
def RESULTS_FILE = 'tagging_results.json' // File used by Python script to store tagging outcomes
def RELEASE_NOTES_BASE_URL = 'https://yourcompanysjira.com/browse/' // Update this base URL
def PYTHON_SCRIPT_PATH = 'scripts/send_email.py'
def FABRIC_SCRIPT_PATH = 'scripts/fabfile.py'

pipeline {
    // Setting global agent to 'none'. You must define an agent in your stages!
    agent none 

    options {
        skipDefaultCheckout()
        timeout(time: 3, unit: 'HOURS') 
    }

    // --- Parameterized Jenkins Interface ---
    parameters {
        // 1. Docker Registry Selection
        choice(name: 'REGISTRY_TYPE', choices: ['docker-hub', 'aws-ecr'], description: 'Select the target Docker Registry.')

        // 2. Ticket Number for Release Notes Link
        string(name: 'TICKET_NUMBER', defaultValue: '', description: 'JIRA/Ticket number for release notes link (e.g., PROJ-123).')

        // 3. Dry Run Option
        choice(name: 'DRY_RUN', choices: ['NO', 'YES'], description: 'Set to YES to test tagging without actually pushing.')

        // 4. Optional Email Recipients
        string(name: 'OPTIONAL_RECIPIENTS', defaultValue: '', description: 'Comma-separated list of optional recipients (e.g., user1@comp.com,user2@comp.com)')

        // 5. Image Tag Change Selection
        choice(name: 'TAGGING_OPTION', choices: [
            'Option A: Standard Tag Change',
            'Option B: Custom Tags'
        ], description: 'Select the type of tag change.')

        choice(name: 'TAG_A_TYPE', choices: [
            'latest->stable',
            'particular_tag->latest'
        ], description: 'Option A: Select the standard tag change.')
        string(name: 'CUSTOM_SOURCE_TAG', defaultValue: '', description: 'Required for "particular_tag->latest" option.')

        string(name: 'CUSTOM_TAG_SOURCE', defaultValue: '', description: 'Option B: Source image tag (e.g., 1.2.3)')
        string(name: 'CUSTOM_TAG_DESTINATION', defaultValue: '', description: 'Option B: Destination image tag (e.g., production-ready)')

        // 6. Multi-select Images 
        // NOTE: The visual checklist requires the Active Choices Parameter Plugin in the Jenkins UI.
        choice(name: 'IMAGES_TO_TAG', choices: [
            'all', 
            'Frontend', 
            'Appmw', 
            'bladeEngine', 
            'Squidservice', 
            'Gatewayimg', 
            'Othermw', 
            'Cardui', 
            'Middlemw', 
            'Memcache'
        ], description: 'Select images to process (Multi-select checkbox).')
    }

    // --- Environment Variables ---
    environment {
        // Dynamic Timestamp for unique log files (e.g., 20251201-190053)
        TIMESTAMP = new Date().format('yyyyMMdd-HHmmss')
        LOG_DIR_COMMAND = "mkdir -p ${LOG_DIR}"
        
        // Dynamic Log File Path
        LOG_FILE_PATH = "${LOG_DIR}/docker_tagging-${env.TIMESTAMP}.log"

        // AWS configuration (Update these placeholders with actual values)
        AWS_REGION = 'us-east-1' 
        AWS_ACCOUNT_ID = '123456789012' 
        
        // Links 
        RELEASE_NOTES_LINK = "${RELEASE_NOTES_BASE_URL}${params.TICKET_NUMBER}"
        BUILD_INFO = "Jenkins Job: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        
        // Extracted variables for clarity
        DRY_RUN_STATUS = "${params.DRY_RUN}"
        
        // Store all parameters as JSON string for the Python script
        PARAMETERS_JSON = groovy.json.JsonOutput.toJson(params)
    }

    stages {
        // 1. Checkout Code
        stage('1. Checkout Code') {
            // Uncomment and set your desired agent label here
            // agent {
            //     label 'your-default-node'
            // }
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '## 🟢 STAGE 1: Checkout Code'
                    checkout scm
                    sh "${env.LOG_DIR_COMMAND}"
                    
                    // Robustness Check: Ensure Python 3 is available
                    script {
                        echo 'Checking required dependencies: Python 3 and Fabric setup.'
                        sh 'which python3 || error "Python 3 not found on agent. Cannot run Fabric/Email script!"'
                    }
                }
            }
        }

        // 2. Validate Parameters
        stage('2. Validate Parameters') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    script {
                        echo '## 🟢 STAGE 2: Validate Parameters'

                        // Robustness Logic: Enforce "all" OR custom list, but not both
                        def selectedImages = params.IMAGES_TO_TAG.split(',').collect { it.trim() }
                        
                        if (selectedImages.contains('all') && selectedImages.size() > 1) {
                            error 'Parameter Validation Failed: You cannot select "all" along with specific images.'
                        }
                        
                        // Check for TICKET_NUMBER & empty image selection
                        if (params.TICKET_NUMBER == null || params.TICKET_NUMBER.trim() == '') {
                            error 'Parameter Validation Failed: Ticket Number is required.'
                        }
                        if (params.IMAGES_TO_TAG.trim() == '') {
                            error 'Parameter Validation Failed: Image selection cannot be empty.'
                        }

                        // Parameter Validation: Conditional requirements for Option A/B
                        if (params.TAGGING_OPTION.contains('Option B')) {
                            if (params.CUSTOM_TAG_SOURCE == null || params.CUSTOM_TAG_SOURCE.trim() == '' ||
                                params.CUSTOM_TAG_DESTINATION == null || params.CUSTOM_TAG_DESTINATION.trim() == '') {
                                error 'Parameter Validation Failed: CUSTOM_TAG_SOURCE and CUSTOM_TAG_DESTINATION are required for Option B.'
                            }
                        } else if (params.TAG_A_TYPE.contains('particular_tag') && (params.CUSTOM_SOURCE_TAG == null || params.CUSTOM_SOURCE_TAG.trim() == '')) {
                            error 'Parameter Validation Failed: CUSTOM_SOURCE_TAG is required for particular_tag->latest.'
                        }
                    }
                }
            }
        }

        // 3. Wait for Approval
        stage('3. Wait for Approval') {
            when {
                expression { return params.DRY_RUN == 'NO' }
            }
            steps {
                script {
                    echo '## 🟡 STAGE 3: Wait for Approval (DRY_RUN = NO)'
                    timeout(time: 2, unit: 'HOURS') {
                        def userInput = input(
                            id: 'ReleaseApproval',
                            message: "Approve tagging and promotion for TICKET: **${params.TICKET_NUMBER}**?",
                            // AUTHORIZATION: Only users with 'admin' or 'adminuser' roles can approve
                            authorizedSid: 'admin, adminuser',
                            parameters: [
                                choice(name: 'Action', choices: ['PROCEED', 'ABORT'], description: 'Select PROCEED to continue the promotion or ABORT to cancel the job.')
                            ]
                        )
                        if (userInput.Action == 'ABORT') {
                            error 'Job aborted by user approval.'
                        }
                    }
                }
            }
        }

        // 4. Image Tagging (Core Logic Execution)
        stage('4. Parallel Image Tagging') {
            // Uncomment and set the required agent label for Docker operations here.
            // agent {
            //     label 'docker-builderT' 
            // }
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    script {
                        echo '## 🟢 STAGE 4: Image Tagging (Fabric Execution)'
                        
                        // Docker Registry Handling (Login)
                        sh 'echo "Logging in to Docker Registry..."'
                        if (params.REGISTRY_TYPE == 'docker-hub') {
                            withCredentials([usernamePassword(credentialsId: DOCKER_HUB_CREDENTIAL_ID, passwordVariable: 'DOCKER_PASSWORD', usernameVariable: 'DOCKER_USERNAME')]) {
                                sh "docker login -u ${DOCKER_USERNAME} -p ${DOCKER_PASSWORD}"
                            }
                        } else if (params.REGISTRY_TYPE == 'aws-ecr') {
                            // Enhanced Security: Use withEnv for account/region variables
                            withEnv(["AWS_ACCOUNT=${env.AWS_ACCOUNT_ID}", "AWS_REG=${env.AWS_REGION}"]) {
                                sh 'aws ecr get-login-password --region ${AWS_REG} | docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.${AWS_REG}.amazonaws.com'
                            }
                        }

                        // Construct Fabric Command Arguments
                        def taggingArgs = ""
                        if (params.TAGGING_OPTION.contains('Option A')) {
                            if (params.TAG_A_TYPE.contains('latest->stable')) {
                                taggingArgs = "--tag-type latest_to_stable"
                            } else { 
                                taggingArgs = "--tag-type custom_to_latest --custom-source-tag ${params.CUSTOM_SOURCE_TAG}"
                            }
                        } else { 
                            taggingArgs = "--tag-type custom_to_custom --source-tag ${params.CUSTOM_TAG_SOURCE} --destination-tag ${params.CUSTOM_TAG_DESTINATION}"
                        }

                        // Execute Fabric Command (Using Dynamic LOG_FILE_PATH)
                        sh """
                            echo 'Executing Fabric script: ${FABRIC_SCRIPT_PATH}'
                            python3 ${FABRIC_SCRIPT_PATH} tag_images: \
                                --images='${params.IMAGES_TO_TAG}' \
                                --dry-run='${params.DRY_RUN}' \
                                --parallel-limit=${PARALLEL_LIMIT} \
                                --log-file='${env.LOG_FILE_PATH}' \
                                --results-file='${RESULTS_FILE}' \
                                ${taggingArgs}
                        """

                        // Print Tagging Results to Console for quick viewing
                        echo '=================================================='
                        echo "Image Tagging Results (${RESULTS_FILE}):"
                        echo '=================================================='
                        sh "if [ -f ${RESULTS_FILE} ]; then cat ${RESULTS_FILE}; else echo 'ERROR: Results file not found or empty.'; fi"
                        echo '=================================================='
                        
                        sh 'echo "Logging out of Docker..." && docker logout'
                    }
                }
            }
        }

        // 5. Send Email Notification (Python script)
        stage('5. Send Email Notification') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    script {
                        echo '## 🟢 STAGE 5: Send Email Notification'
                        def recipients = "${env.GIT_COMMITTER_EMAIL},${params.OPTIONAL_RECIPIENTS}".split(',').collect { it.trim() }.findAll { it.length() > 0 }.join(',')
                        
                        // Execute the Python script (Using Dynamic LOG_FILE_PATH)
                        sh """
                            echo 'Running Python email script: ${PYTHON_SCRIPT_PATH}'
                            python3 ${PYTHON_SCRIPT_PATH} \\
                                --status 'SUCCESS' \\
                                --recipients '${recipients}' \\
                                --log-file '${env.LOG_FILE_PATH}' \\
                                --results-file '${RESULTS_FILE}' \\
                                --jenkins-url '${env.BUILD_URL}' \\
                                --release-link '${env.RELEASE_NOTES_LINK}' \\
                                --build-info '${BUILD_INFO}' \\
                                --dry-run-status '${env.DRY_RUN_STATUS}' \\
                                --parameters-json '${env.PARAMETERS_JSON}'
                        """
                    }
                }
            }
        }

        // 6. Cleanup & Docker Prune
        stage('6. Cleanup & Docker Prune') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
                    echo '## 🟢 STAGE 6: Cleanup & Docker Prune'
                    
                    // Consolidated Cleanup (logs, results, docker)
                    sh """
                        echo 'Cleaning Docker artifacts...'
                        docker system prune -f --all --volumes || true 
                        echo 'Cleaning temporary files...'
                        // Using Dynamic LOG_FILE_PATH for cleanup
                        rm -f ${env.LOG_FILE_PATH} ${RESULTS_FILE} || true
                    """
                    // Final workspace cleanup
                    cleanWs(deleteDirs: true)
                    echo 'Cleanup complete.'
                }
            }
        }
    }

    // --- Post-Build Actions ---
    post {
        failure {
            script {
                echo '## 🔴 Post-Build: Failure Notification'
                def recipients = "${env.GIT_COMMITTER_EMAIL},${params.OPTIONAL_RECIPIENTS}".split(',').collect { it.trim() }.findAll { it.length() > 0 }.join(',')
                
                // Execute failure email template (Using Dynamic LOG_FILE_PATH)
                sh """
                    echo 'Running Python failure email script: ${PYTHON_SCRIPT_PATH}'
                    python3 ${PYTHON_SCRIPT_PATH} \\
                        --status 'FAILURE' \\
                        --recipients '${recipients}' \\
                        --log-file '${env.LOG_FILE_PATH}' \\
                        --jenkins-url '${env.BUILD_URL}' \\
                        --release-link '${env.RELEASE_NOTES_LINK}' \\
                        --build-info '${BUILD_INFO}' \\
                        --dry-run-status '${env.DRY_RUN_STATUS}' \\
                        --parameters-json '${env.PARAMETERS_JSON}'
                """
            }
        }
    }
}