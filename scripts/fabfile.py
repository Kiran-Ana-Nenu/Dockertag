#!/usr/bin/env python3
import argparse
import sys
import os
import time
from tag_utils import pull_image, tag_image, push_image

LOGFILE = "/var/log/jenkins/docker_tagging.log"

# Argument parser
parser = argparse.ArgumentParser(description="Docker Image Tagging Script")
parser.add_argument('--registry', required=True, help='Docker registry')
parser.add_argument('--image', required=True, help='Image name')
parser.add_argument('--mode', required=True, choices=['OPTION_A', 'OPTION_B'], help='Tagging mode')
parser.add_argument('--custom1', default='', help='Custom tag1 / Particular tag')
parser.add_argument('--custom2', default='', help='Custom tag2 / Latest to stable')
parser.add_argument('--dry-run', choices=['YES','NO'], default='YES', help='Dry run mode')

args = parser.parse_args()

# Logger
def log(msg):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open(LOGFILE, 'a') as f:
        f.write(entry + "\n")

# Main function
def main():
    image_full = f"{args.registry}/{args.image}"
    log(f"Starting processing image: {image_full} Mode: {args.mode} Dry-run: {args.dry_run}")

    # Determine source and destination tags based on mode
    if args.mode == 'OPTION_A':
        src_tag = args.custom1  # Particular → Latest
        dst_tag = args.custom2  # Latest → Stable
    else:
        src_tag = args.custom1
        dst_tag = args.custom2

    src_image = f"{image_full}:{src_tag}"
    dst_image = f"{image_full}:{dst_tag}"

    log(f"Source image: {src_image}")
    log(f"Destination image: {dst_image}")

    try:
        if args.dry_run == 'YES':
            log(f"[DRY-RUN] Would pull {src_image}, tag {dst_image}, push {dst_image}")
        else:
            pull_image(src_image)
            tag_image(src_image, dst_image)
            push_image(dst_image)
            log(f"Successfully tagged and pushed: {dst_image}")

        # Return summary for email
        summary = {
            'image': args.image,
            'src_tag': src_tag,
            'dst_tag': dst_tag,
            'status': 'SUCCESS' if args.dry_run=='NO' else 'DRY-RUN'
        }
        print(summary)
        return summary

    except Exception as e:
        log(f"Error processing {args.image}: {e}")
        summary = {
            'image': args.image,
            'src_tag': src_tag,
            'dst_tag': dst_tag,
            'status': 'FAILED'
        }
        print(summary)
        sys.exit(1)

if __name__ == "__main__":
    main()
