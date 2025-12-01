# scripts/fabfile.py
"""
Fabric script for parallel Docker image tagging and promotion.
Handles retry mechanisms, logging, and dry-run execution.
"""
from fabric.api import task, local, settings
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- Configuration ---
# Placeholder: Define your common repository prefix here
DOCKER_REPO_PREFIX = "mycompanyrepo"

# --- Logging Setup ---
# Jenkins job log for summary and failure status
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_image_logger(image_name, log_file):
    """Sets up a logger to append detailed output to the main log file."""
    image_logger = logging.getLogger(image_name)
    image_logger.setLevel(logging.INFO)
    
    # Check if handler exists to avoid duplication
    if not image_logger.handlers:
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        image_logger.addHandler(file_handler)
    return image_logger

def retry_command(command, image_logger, retries=3):
    """Wrap Docker pull/tag/push commands with retry for transient network issues."""
    for attempt in range(retries):
        try:
            image_logger.info(f"Attempt {attempt + 1} of {retries}: Executing command: {command}")
            # Use 'local' for execution on the local machine (Jenkins slave)
            with settings(warn_only=False):
                local(command)
            return True
        except Exception as e:
            image_logger.error(f"Command failed on attempt {attempt + 1}: {e}")
            if attempt + 1 == retries:
                raise
            # Wait a bit before retrying
            import time; time.sleep(2 ** attempt) 
    return False # Should not be reached

def process_image(image_name, source_tag, destination_tag, dry_run, log_file):
    """
    Core function to pull, tag, and push a single Docker image.
    Handles logging, validation, and dry-run.
    """
    image_logger = setup_image_logger(image_name, log_file)
    source_image = f"{DOCKER_REPO_PREFIX}/{image_name}:{source_tag}"
    dest_image = f"{DOCKER_REPO_PREFIX}/{image_name}:{destination_tag}"
    result = {
        'image': image_name,
        'source': source_tag,
        'destination': destination_tag,
        'status': 'FAILURE',
        'message': ''
    }

    image_logger.info(f"\n--- Starting Tagging for {image_name} ---")
    image_logger.info(f"Source: {source_image}, Destination: {dest_image}, Dry Run: {dry_run}")
    
    try:
        # 1. Validate image exists before pulling & Docker Pull with Retry
        # Pull command serves as validation. If it fails, the image doesn't exist/can't be accessed.
        retry_command(f"docker pull {source_image}", image_logger)

        # 2. Docker Tag
        retry_command(f"docker tag {source_image} {dest_image}", image_logger)

        # 3. Docker Push (Conditional on Dry Run)
        if dry_run == 'NO':
            image_logger.info("DRY_RUN is NO. Attempting to push...")
            retry_command(f"docker push {dest_image}", image_logger)
            result['status'] = 'SUCCESS'
            result['message'] = 'Image successfully tagged and pushed.'
        else:
            image_logger.info("DRY_RUN is YES. Skipping docker push.")
            result['status'] = 'DRY_RUN_SUCCESS'
            result['message'] = 'Image successfully tagged (Dry Run).'
            
    except Exception as e:
        error_msg = f"Failed to process {image_name}. Error: {e}"
        image_logger.error(error_msg)
        result['status'] = 'FAILURE'
        result['message'] = str(e)

    image_logger.info(f"--- Finished Tagging for {image_name} ({result['status']}) ---\n")
    return result

@task
def tag_images(images, dry_run, parallel_limit, log_file, results_file, 
               tag_type='latest_to_stable', source_tag=None, destination_tag=None, custom_source_tag=None):
    """
    Main Fabric task to coordinate parallel tagging.
    """
    logging.info("--- FABRIC TASK: tag_images started ---")
    
    # 1. Determine the actual tags based on input parameters
    final_images = images.split(',')
    if 'all' in final_images and len(final_images) > 1:
        final_images.remove('all')

    if tag_type == 'latest_to_stable':
        source = 'latest'
        destination = 'stable'
    elif tag_type == 'custom_to_latest':
        source = custom_source_tag # Passed from CUSTOM_SOURCE_TAG
        destination = 'latest'
    elif tag_type == 'custom_to_custom':
        source = source_tag
        destination = destination_tag
    else:
        raise ValueError(f"Invalid tag_type: {tag_type}")

    logging.info(f"Tagging operation: Source={source} -> Destination={destination}")
    logging.info(f"Images to process: {final_images}")
    
    # 2. Prepare tasks for parallel execution (Throttle is applied here)
    tasks = []
    for image in final_images:
        tasks.append((image.strip(), source, destination, dry_run, log_file))

    all_results = []
    
    # 3. Parallel image tagging with ThreadPoolExecutor (Throttle limit)
    with ThreadPoolExecutor(max_workers=int(parallel_limit)) as executor:
        futures = [executor.submit(process_image, *task_args) for task_args in tasks]
        for future in futures:
            all_results.append(future.result())

    # 4. Save results for the email script
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=4)
        
    logging.info(f"--- FABRIC TASK: tag_images finished. Results saved to {results_file} ---")

    # 5. Check for any overall failure and raise an exception to fail the Jenkins job
    if any(r['status'] == 'FAILURE' for r in all_results):
        # This exception will be caught by the Jenkinsfile's try/catch block
        raise Exception("One or more image tagging operations failed. Check logs for details.")