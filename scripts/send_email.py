# scripts/send_email.py (Placeholder - Requires 'requests' or 'smtplib' for actual sending)
"""
Python script to generate a modern, HTML email notification with detailed results.
"""
import argparse
import json
import os
import smtplib # Example import
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# --- Configuration ---
SMTP_SERVER = 'your.smtp.server'
SENDER_EMAIL = 'jenkins@yourcompany.com'
COMPANY_LOGO_URL = 'http://yourcompany.com/logo.png' # Placeholder

def load_template(template_name):
    """Loads the HTML template from the templates directory."""
    try:
        # Assumes execution from 'scripts/' and templates are in '../templates/'
        template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', template_name)
        with open(template_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error: Template {template_name} not found!</h1>"

def create_results_table(results):
    """Generates the HTML table for Image-by-Image Results."""
    html = """
    <table style="width:100%; border-collapse: collapse; text-align: left;">
        <thead>
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 8px; border: 1px solid #ddd;">Image Name</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Tag Change</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Status</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Message</th>
            </tr>
        </thead>
        <tbody>
    """
    for item in results:
        status = item.get('status', 'UNKNOWN')
        color = {
            'SUCCESS': '#d4edda',   # Green
            'DRY_RUN_SUCCESS': '#fff3cd', # Yellow/Cream
            'FAILURE': '#f8d7da'    # Red
        }.get(status, '#e2e3e5')

        tag_change = f"{item['source']} &rarr; {item['destination']}"
        
        # Color-coded SUCCESS / FAILURE / DRY_RUN
        html += f"""
            <tr style="background-color: {color};">
                <td style="padding: 8px; border: 1px solid #ddd;">{item['image']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{tag_change}</td>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>{status}</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item['message']}</td>
            </tr>
        """
    html += "</tbody></table>"
    return html

def print_parameters(params_json):
    """Generates an HTML list for printed parameters."""
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError:
        return f"<div>Error decoding parameters: {params_json}</div>"

    html = "<ul style='list-style-type: none; padding-left: 0;'>"
    for key, value in params.items():
        # Exclude sensitive/unnecessary parameters
        if key not in ['TICKET_NUMBER', 'OPTIONAL_RECIPIENTS', 'TAGGING_OPTION', 'TAG_A_TYPE', 'CUSTOM_SOURCE_TAG', 'CUSTOM_TAG_SOURCE', 'CUSTOM_TAG_DESTINATION', 'REGISTRY_TYPE', 'DRY_RUN', 'IMAGES_TO_TAG']:
            continue
        html += f"<li style='margin-bottom: 5px;'><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
    html += "</ul>"
    return html

def create_email_body(args, results):
    """Replaces placeholders in the HTML template."""
    
    # Determine template and subject/color theme
    if args.status == 'SUCCESS':
        template = load_template('email_success.html')
        subject_status = "SUCCESS"
        primary_color = "#007bff" # Blue for promotion/success
        tag_line = "Image Promotion Completed"
    else:
        template = load_template('email_failure.html')
        subject_status = "FAILURE"
        primary_color = "#dc3545" # Red for failure
        tag_line = "Image Promotion Failed"

    # Animated status badge (simplified text version for a placeholder)
    status_badge = f"""
    <span style="display: inline-block; background-color: {primary_color}; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;">
        {args.status.upper()}
    </span>
    """
    
    # Build content parts
    results_table = create_results_table(results)
    params_list = print_parameters(args.parameters_json)
    
    # Placeholder replacements (These must match the variables in the HTML templates)
    replacements = {
        '{{STATUS_BADGE}}': status_badge,
        '{{TAG_LINE}}': tag_line,
        '{{TICKET_NUMBER}}': args.release_link.split('/')[-1], # Extract ticket number from link
        '{{RELEASE_NOTES_LINK}}': args.release_link, # Clickable links to release notes
        '{{JENKINS_JOB_LINK}}': args.jenkins_url,    # Clickable link to Jenkins job
        '{{IMAGE_RESULTS_TABLE}}': results_table,
        '{{PARAMETERS_LIST}}': params_list,
        '{{DRY_RUN_STATUS}}': args.dry_run_status,
        '{{PRIMARY_COLOR}}': primary_color,
        '{{COMPANY_LOGO_URL}}': COMPANY_LOGO_URL,
        '{{BUILD_INFO}}': args.build_info,
        # ... other fields like {{COMPANY_FOOTER}} ...
    }

    body = template
    for key, value in replacements.items():
        body = body.replace(key, value)
        
    return f"[{subject_status}] Docker Tagging Job: {args.release_link.split('/')[-1]}", body

def send_email_notification(args):
    """Prepares and sends the final email."""
    
    # 1. Load Results
    results = []
    if os.path.exists(args.results_file):
        try:
            with open(args.results_file, 'r') as f:
                results = json.load(f)
        except json.JSONDecodeError:
            print(f"Error reading JSON results file: {args.results_file}")
            # If JSON fails, treat as an overall failure if status was SUCCESS
    
    # 2. Create Email Content
    subject, html_body = create_email_body(args, results)
    
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = args.recipients

    # Attach HTML body
    msg.attach(MIMEText(html_body, 'html'))

    # 3. Attach Log File
    if os.path.exists(args.log_file):
        try:
            with open(args.log_file, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="log")
                attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(args.log_file))
                msg.attach(attach)
        except Exception as e:
            print(f"Error attaching log file: {e}")

    # 4. Send Email (Placeholder logic)
    try:
        # Use actual SMTP library or a corporate email API here
        # server = smtplib.SMTP(SMTP_SERVER)
        # server.sendmail(SENDER_EMAIL, args.recipients.split(','), msg.as_string())
        # server.quit()
        print(f"Successfully generated and (mock) sent email to: {args.recipients}")
        print(f"Email Subject: {subject}")
    except Exception as e:
        print(f"Failed to send email: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send Docker Tagging Email Notification.')
    parser.add_argument('--status', required=True, choices=['SUCCESS', 'FAILURE'], help='The overall job status.')
    parser.add_argument('--recipients', required=True, help='Comma-separated list of email recipients.')
    parser.add_argument('--log-file', required=True, help='Path to the consolidated log file to attach.')
    parser.add_argument('--results-file', help='Path to the JSON results file (required for SUCCESS).')
    parser.add_argument('--jenkins-url', required=True, help='Clickable link to the Jenkins job.')
    parser.add_argument('--release-link', required=True, help='Clickable link to the release notes/ticket.')
    parser.add_argument('--build-info', required=True, help='Job name and build number.')
    parser.add_argument('--dry-run-status', required=True, help='YES or NO for Dry Run status.')
    parser.add_argument('--parameters-json', required=True, help='JSON string of all Jenkins parameters.')
    
    args = parser.parse_args()
    send_email_notification(args)