<!-- # Jenkins Docker Promotion Pipeline

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
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_TLS -->
### 🌟 Docker Image Tagging and Promotion Pipeline

This repository contains the Jenkins Declarative Pipeline and supporting scripts for a controlled Docker image promotion process. The core tagging logic is executed exclusively via **Fabric**.

### 🚀 Usage Guide (Jenkins Parameters)

Navigate to the Jenkins job and select **Build with Parameters**.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| **REGISTRY_TYPE** | Choice | Select `docker-hub` or `aws-ecr`. |
| **TICKET_NUMBER** | String | The JIRA/Ticket number (e.g., `PROJ-123`) used for the release notes link in the email. |
| **DRY_RUN** | Choice | **`YES`**: Skips Docker `push` and the Approval Gate. Logs all tag/pull operations. **`NO`**: Full execution, requires manual approval, performs Docker `push`. |
| **OPTIONAL_RECIPIENTS** | String | Comma-separated list of extra email addresses. |
| **TAGGING_OPTION** | Choice (Reactive) | **Selects the promotion path.** This choice dynamically shows/hides the related parameters (Option A or Option B). |
| **TAG_A_TYPE** | Choice (Reactive) | *(Visible for Option A)*: Selects `latest -> stable` or `particular_tag -> latest`. |
| **CUSTOM_SOURCE_TAG** | String (Reactive) | *(Required for `particular_tag -> latest`)*: The specific tag to be promoted to `latest`. |
| **CUSTOM_TAG_SOURCE** | String (Reactive) | *(Required for Option B)*: The source tag string (e.g., `1.2.3`). |
| **CUSTOM_TAG_DESTINATION** | String (Reactive) | *(Required for Option B)*: The destination tag string (e.g., `prod-v1`). |
| **IMAGES_TO_TAG** | Active Choices (Checkbox) | **Multi-select** the images to be processed (`all`, `appmw`, etc.). |

### 🛠️ Pipeline Stages & Key Features

| Stage | Action & Features |
| :--- | :--- |
| **1. Checkout Code** | Checks out the project, ensuring scripts are available. |
| **2. Validate Parameters** | **Parameter Validation** checks for required fields (e.g., `TICKET_NUMBER`, `CUSTOM_TAG` requirements) and prevents empty image selection. |
| **3. Wait for Approval** | **Manual Approval Gate** using `input` step. **Skipped if DRY_RUN = YES**. Allows approver to `PROCEED` or `ABORT` (which fails the job). |
| **4. Image Tagging** | Core logic executed by **`scripts/fabfile.py` (ONLY Fabric execution)**. Includes: **Dynamic Docker Login**, **Parallel Image Tagging** using `ThreadPoolExecutor`, **Throttle** control (`PARALLEL_LIMIT=3`), **Retry Mechanism** (3 attempts for Docker commands), **Validation** (via `docker pull`), and detailed **Logging** to `/var/log/jenkins/docker_tagging.log`. |
| **5. Send Email Notification** | Executes **`scripts/send_email.py`** to send a highly-styled, modern HTML email. Includes: **Image-by-Image Results Table**, **Status Badges** (animated/color-coded), **Parameter Printing**, **Log Attachment**, and **Clickable Links** to Jenkins job and Release Notes. |
| **6. Cleanup & Docker Prune** | Cleans the workspace (`cleanWs`) and runs `docker system prune -f --all` to **Delete unused Docker images** and artifacts on the slave node. |

### 🔗 Directories and Files

| Path | Purpose |
| :--- | :--- |
| **`Jenkinsfile`** | The main Declarative Pipeline script. |
| **`scripts/fabfile.py`** | **Core logic:** Handles parallelism, throttling, retries, and logging for Docker operations. |
| **`scripts/send_email.py`** | **Notification logic:** Generates and sends the modern HTML email. |
| **`templates/`** | Contains `email_success.html` and `email_failure.html` for email styling and content. |

### 🔒 Credentials and Environment

* **Docker Hub:** Uses the Jenkins credential ID **`docker_login`** (Username/Password).
* **AWS ECR:** Assumes an **IAM Role** is attached to the EC2 slave node, granting ECR read/write permissions for password-less login.
* **Node:** The job requires a dynamically provisioned EC2 slave with the label **`docker-builder`**.