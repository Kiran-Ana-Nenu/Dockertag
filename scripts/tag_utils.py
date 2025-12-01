#!/usr/bin/env python3
import subprocess
import time

def run_command(cmd, retries=3, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except subprocess.CalledProcessError as e:
            attempt += 1
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Command failed: {cmd}, attempt {attempt}")
            if attempt >= retries:
                raise e
            time.sleep(delay)
    return False

def pull_image(image):
    return run_command(f"docker pull {image}")

def tag_image(source, target):
    return run_command(f"docker tag {source} {target}")

def push_image(image):
    return run_command(f"docker push {image}")
