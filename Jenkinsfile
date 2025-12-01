// Jenkinsfile - Declarative pipeline for image tagging & promotion
}
steps {
script {
// Use Jenkins input step with restricted approvers (set in job config)
input message: 'Approve promotion?', ok: 'Promote', submitter: 'team-lead,release-manager'
}
}
}


stage('Image Tagging') {
steps {
script {
echo "== Image Tagging (parallel) =="


// Build a map of closures for parallel step
def branches = [:]


def images = IMAGES_LIST
// If 'all' specified, replace with canonical list
if (images.size() == 1 && images[0] == 'all') {
images = ['appmw','othermw','cardui','middlemw','memcache']
}


images.each { img ->
branches[img] = {
// Wrap each image run with throttle using Throttle Concurrent Builds plugin
// Requires "Throttle Concurrent Builds" plugin configured or Lockable Resources plugin
throttle(['category': 'docker-tagging','maxPerNode': env.PARALLEL_SLOTS.toInteger(), 'maxTotal': env.PARALLEL_SLOTS.toInteger()]) {
node {
stage("Tag-${img}") {
echo "Processing ${img}"
// Call Fabric script on agent
sh "python3 scripts/fabfile.py --image ${img} --mode ${params.MODE} --custom1 '${params.CUSTOM_TAG1}' --custom2 '${params.CUSTOM_TAG2}' --registry ${params.DOCKER_REGISTRY} --dry-run ${params.DRY_RUN} --logfile ${env.LOGFILE}"
}
}
}
}
}


parallel branches
}
}
}


stage('Send Email Notification') {
steps {
script {
echo "== Sending Email =="
sh "python3 scripts/send_email.py --ticket '${params.TICKET}' --recipients '${params.RECIPIENTS}' --log '${env.LOGFILE}' --dry-run ${params.DRY_RUN}"
}
}
}


stage('Cleanup & Docker Prune') {
steps {
echo "== Cleanup =="
sh "bash -x scripts/cleanup.sh || true"
}
}
}


post {
always {
echo 'Pipeline finished — archiving logs'
archiveArtifacts artifacts: 'logs/**', allowEmptyArchive: true
}
failure {
echo 'Pipeline failed — sending failure email'
sh "python3 scripts/send_email.py --ticket '${params.TICKET}' --recipients '${params.RECIPIENTS}' --log '${env.LOGFILE}' --status FAILURE"
}
}
}