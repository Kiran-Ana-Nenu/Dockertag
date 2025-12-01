#!/usr/bin/env python3
import argparse
from tag_utils import pull_image, tag_image, push_image
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--registry', required=True)
parser.add_argument('--image', required=True)
parser.add_argument('--mode', required=True)
parser.add_argument('--custom1', default='')
parser.add_argument('--custom2', default='')
parser.add_argument('--dry-run', choices=['YES','NO'], default='YES')
args = parser.parse_args()

def main():
    image_full = f"{args.registry}/{args.image}"
    print(f"Processing {image_full} with mode {args.mode}")

    if args.mode == 'LATEST_PROMOTE':
        src = f"{image_full}:latest"
        dst = f"{image_full}:stable"
    else:
        src = f"{image_full}:{args.custom1}"
        dst = f"{image_full}:{args.custom2}"

    if args.dry_run == 'YES':
        print(f"[DRY-RUN] Would pull {src}, tag {dst}, push {dst}")
        return

    pull_image(src)
    tag_image(src, dst)
    push_image(dst)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
