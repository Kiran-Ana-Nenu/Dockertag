#!/usr/bin/env python3
"""
tag_utils.py
Utility script to validate existence of images and perform tagging/pushing with retry and dry-run support.
"""
import argparse
import subprocess
import sys
import time
import logging
from pathlib import Path

LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger('tag_utils')
handler = logging.FileHandler(LOG_DIR / 'tag_utils.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

RETRY_COUNT = 3
RETRY_DELAY = 5

def run_cmd(cmd):
    logger.info('RUN: %s', cmd)
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        logger.info(out)
        return out
    except subprocess.CalledProcessError as e:
        logger.error('Command failed: %s', e.output)
        raise

def image_exists(registry, image, tag):
    try:
        run_cmd(f'docker manifest inspect {image}:{tag}')
        return True
    except Exception:
        return False

def retry(fn, attempts=RETRY_COUNT, delay=RETRY_DELAY):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            logger.warning('Attempt %d failed: %s', i+1, e)
            if i+1 == attempts:
                raise
            time.sleep(delay)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registry', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--strategy', required=True, choices=['latest','custom'])
    parser.add_argument('--tag1', default='')
    parser.add_argument('--tag2', default='')
    parser.add_argument('--dry-run', required=True)
    parser.add_argument('--ticket', default='')
    args = parser.parse_args()

    image = args.image
    registry = args.registry
    dry_run = str(args.dry_run).upper() == 'YES'

    if args.strategy == 'latest':
        if args.tag1:
            src_tag = args.tag1
            dest_tag = 'latest'
        else:
            src_tag = 'latest'
            dest_tag = 'stable'
    else:
        src_tag = args.tag1
        dest_tag = args.tag2

    logger.info('Processing %s: %s -> %s (dry_run=%s)', image, src_tag, dest_tag, dry_run)

    def validate():
        if not image_exists(registry, image, src_tag):
            raise Exception(f'Image {image}:{src_tag} not found in {registry}')
    retry(validate)

    def promote():
        if dry_run:
            logger.info('[DRY-RUN] Would pull %s:%s and tag as %s', image, src_tag, dest_tag)
            return
        run_cmd(f'docker pull {image}:{src_tag}')
        run_cmd(f'docker tag {image}:{src_tag} {image}:{dest_tag}')
        run_cmd(f'docker push {image}:{dest_tag}')

    retry(promote)
    logger.info('Completed %s', image)

if __name__ == '__main__':
    main()
