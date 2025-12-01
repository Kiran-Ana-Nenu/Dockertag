# fabfile.py - fabric style CLI (we implement as regular python CLI to avoid fabric runtime issues)
# Responsibilities:
# - Validate images
# - Pull/tag/push with retries
# - Respect --dry-run
# - Log per-image entries to /var/log/jenkins/docker_tagging.log


import argparse
import subprocess
import sys
import time
import logging
from tag_utils import pull_with_retry, tag_image, push_with_retry


LOGFILE = '/var/log/jenkins/docker_tagging.log'


logging.basicConfig(filename=LOGFILE, level=logging.INFO,
format='%(asctime)s %(levelname)s %(message)s')


parser = argparse.ArgumentParser()
parser.add_argument('--image', required=True)
parser.add_argument('--mode', choices=['LATEST_PROMOTE','CUSTOM_TAGS'], required=True)
parser.add_argument('--custom1', default='')
parser.add_argument('--custom2', default='')
parser.add_argument('--registry', required=True)
parser.add_argument('--dry-run', choices=['YES','NO'], default='NO')
parser.add_argument('--logfile', default=LOGFILE)
args = parser.parse_args()


IMAGE = args.image
DRY_RUN = args.dry_run == 'YES'


def main():
logging.info(f"Start processing {IMAGE} mode={args.mode} dry_run={DRY_RUN}")


try:
if args.mode == 'LATEST_PROMOTE':
# Example: change latest -> stable
src_tag = 'latest'
dst_tag = 'stable'
# Pull verify
if not pull_with_retry(f"{IMAGE}:{src_tag}"):
logging.error(f"Image {IMAGE}:{src_tag} not available")
sys.exit(2)
# Tag
tag_image(f"{IMAGE}:{src_tag}", f"{IMAGE}:{dst_tag}")
# Push
if not DRY_RUN:
push_with_retry(f"{args.registry}/{IMAGE}:{dst_tag}")


elif args.mode == 'CUSTOM_TAGS':
t1 = args.custom1.strip()
t2 = args.custom2.strip()
if not t1 or not t2:
logging.error('CUSTOM tags missing')
sys.exit(3)
# Pull source (choose t1) and retag to t2
if not pull_with_retry(f"{IMAGE}:{t1}"):
logging.error(f"Image {IMAGE}:{t1} not available")
sys.exit(4)
tag_image(f"{IMAGE}:{t1}", f"{args.registry}/{IMAGE}:{t2}")
if not DRY_RUN:
push_with_retry(f"{args.registry}/{IMAGE}:{t2}")
main()