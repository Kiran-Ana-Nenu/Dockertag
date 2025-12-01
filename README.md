# Jenkins Docker Promotion Pipeline

Repository contains Jenkinsfile, helper scripts, and templates for the Docker image promotion pipeline.

## How to use

1. Open the `Jenkinsfile` in this repo and paste into your Jenkins job (pipeline script from SCM recommended).
2. Ensure Jenkins has the following credentials configured:
   - `docker_login` (username/password or token) for Docker registries.
   - AWS credentials (if using ECR) or configure an IAM role on EC2 agents.
3. Install the recommended plugins listed below.
4. Place templates and scripts under the job workspace (same structure as repo).
5. Configure LDAP/AD plugin and group mapping in Jenkins for approvals.

## Required Jenkins Plugins
- Pipeline (workflow-aggregator)
- Git
- Credentials Binding
- Docker Pipeline
- Throttle Concurrent Builds (optional)
- LDAP Plugin or Active Directory Plugin
- AnsiColor
- Email Extension (optional)
- Blue Ocean (optional)

## Job Parameters
- REGISTRY: Docker-hub or AWS-ECR
- TICKET: Ticket number used in release notes link
- DRY_RUN: YES or NO
- EMAIL_RECIPIENTS: optional comma-separated addresses
- PROMOTE_STRATEGY: latest or custom
- CUSTOM_TAG1, CUSTOM_TAG2: used when custom selected
- IMAGES: comma-separated image names
- SLAVE_TYPE: EC2 agent label (t-series/m-series/mx-series)

## Logs
- Per-image logs are saved under `logs/` in workspace.
- Master log appended to `/var/log/jenkins/docker_tagging.log`.

## Email
The send_email.py script uses environment variables for SMTP:
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_TLS
