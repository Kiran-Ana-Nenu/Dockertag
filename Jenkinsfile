// Jenkinsfile: Docker Image Promotion Pipeline (Declarative + Scripted helpers)
// Ticket: DevOpsAutom-1234
// Author: KiranRoy

pipeline {
  agent none
  options {
    ansiColor('xterm')
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  parameters {
    choice(name: 'REGISTRY', choices: ['Docker-hub', 'AWS-ECR'], description: 'Select docker registry')
    string(name: 'TICKET', defaultValue: 'DevOpsAutom-1234', description: 'Ticket number (used in release notes link)')
    choice(name: 'DRY_RUN', choices: ['YES','NO'], description: 'Dry run?')
    string(name: 'EMAIL_RECIPIENTS', defaultValue: '', description: 'Optional comma-separated recipient emails')
    choice(name: 'PROMOTE_STRATEGY', choices: ['latest','custom'], description: 'Option A: latest, Option B: custom tags')
    string(name: 'CUSTOM_TAG1', defaultValue: '', description: 'Custom tag 1 (required for custom)')
    string(name: 'CUSTOM_TAG2', defaultValue: '', description: 'Custom tag 2 (required for custom)')
    text(name: 'IMAGES', defaultValue: 'appmw,othermw,cardui,middlemw,memcache', description: 'Comma-separated image names (multi-select simulated)')
    choice(name: 'SLAVE_TYPE', choices: ['t-series','m-series','mx-series'], description: 'EC2 agent family label')
  }

  stages {
    stage('Checkout Code') {
      agent { label 'master' }
      steps {
        echo "\\n=== Checkout Code ===\\n"
        checkout scm
        sh 'mkdir -p logs'
      }
    }

    stage('Validate Parameters') {
      agent { label 'master' }
      steps {
        script {
          echo "\\n=== Validate Parameters ===\\n"
          if (params.PROMOTE_STRATEGY == 'custom') {
            if (!params.CUSTOM_TAG1?.trim() || !params.CUSTOM_TAG2?.trim()) {
              error 'CUSTOM_TAG1 and CUSTOM_TAG2 are required for custom strategy.'
            }
          }
          IMAGES = params.IMAGES.split(',').collect{ it.trim() }.findAll{ it }
          if (IMAGES.size() == 0) {
            error 'No images provided in IMAGES parameter.'
          }
          echo "Images -> ${IMAGES}"
        }
      }
    }

    stage('Pre-Approval (Restricted Users)') {
      when {
        expression { return params.DRY_RUN == 'NO' }
      }
      agent { label 'master' }
      steps {
        script {
          echo "\\n=== Pre-Approval Check ===\\n"
          def allowedUsers = []
          try {
            allowedUsers = ldapGetApprovers()
          } catch (e) {
            echo "Failed to fetch approvers from LDAP: ${e}"
            error 'Unable to resolve approvers. Contact Admin.'
          }

          def approver = input message: 'Approve Promotion?', ok: 'Approve', parameters: [string(name: 'APPROVER', defaultValue: '', description: 'Enter your username')]
          if (!allowedUsers.contains(approver.APPROVER)) {
            error "User ${approver.APPROVER} is not authorized to approve this promotion."
          }
          echo "Approved by ${approver.APPROVER}"
        }
      }
    }

    stage('Image Tagging (Parallel w/ Throttle)') {
      agent { label params.SLAVE_TYPE }
      steps {
        script {
          echo "\\n=== Image Tagging ===\\n"
          def parallelTasks = [:]
          def throttleLimit = 3

          IMAGES.each { img ->
            def imageName = img
            parallelTasks[imageName] = {
              node(params.SLAVE_TYPE) {
                stage("Process ${imageName}") {
                  wrap([$class: 'BuildUser']) {
                    sh "echo Processing ${imageName} > logs/${imageName}.log"
                    try {
                      withRetry(3) {
                        sh "python3 scripts/tag_utils.py --registry ${params.REGISTRY} --image ${imageName} --strategy ${params.PROMOTE_STRATEGY} --tag1 '${params.CUSTOM_TAG1}' --tag2 '${params.CUSTOM_TAG2}' --dry-run ${params.DRY_RUN} --ticket ${params.TICKET}"
                      }
                    } catch (err) {
                      echo "Failed for ${imageName}: ${err}"
                      sh "echo FAILED: ${err} >> logs/${imageName}.log"
                      currentBuild.result = 'UNSTABLE'
                    }
                  }
                }
              }
            }
          }

          def chunks = IMAGES.collate(throttleLimit)
          for (chunk in chunks) {
            parallel chunk.collectEntries { [(it): parallelTasks[it] ] }
          }
        }
      }
    }

    stage('Send Email Notification (Python script)') {
      agent { label 'master' }
      steps {
        script {
          echo "\\n=== Sending Email ===\\n"
          sh "python3 scripts/send_email.py --ticket ${params.TICKET} --recipients '${params.EMAIL_RECIPIENTS}' --dry-run ${params.DRY_RUN} --job-url '${env.BUILD_URL}'"
        }
      }
      post {
        always {
          archiveArtifacts artifacts: 'logs/**', allowEmptyArchive: true
        }
      }
    }

    stage('Cleanup & Docker Prune') {
      agent { label params.SLAVE_TYPE }
      steps {
        script {
          echo "\\n=== Cleanup ===\\n"
          sh 'docker logout || true'
          sh 'docker system prune -af || true'
        }
      }
    }
  }

  post {
    success { echo 'Pipeline succeeded' }
    unstable { echo 'Pipeline unstable: some image promotions failed' }
    failure { echo 'Pipeline failed' }
    always {
      echo "Write master log to /var/log/jenkins/docker_tagging.log"
      sh "cat logs/*.log >> /var/log/jenkins/docker_tagging.log || true"
    }
  }
}

@NonCPS
def withRetry(int attempts = 3, Closure body) {
  int i = 0
  while (true) {
    try {
      i++
      return body.call()
    } catch (err) {
      if (i >= attempts) {
        throw err
      }
      echo "Retry ${i}/${attempts} after error: ${err}"
      sleep time: 5, unit: 'SECONDS'
    }
  }
}

@NonCPS
def ldapGetApprovers() {
  // Placeholder: implement LDAP lookup via shell script or Jenkins LDAP plugin
  return ['kiran','admin','opsuser']
}
