# tag_utils.py - small helpers for retrying docker commands
import subprocess
import time


RETRY = 3
SLEEP = 5




def run_cmd(cmd):
print('CMD:', cmd)
return subprocess.call(cmd, shell=True)




def pull_with_retry(ref):
for i in range(RETRY):
rc = run_cmd(f"docker pull {ref}")
if rc == 0:
return True
time.sleep(SLEEP)
return False




def tag_image(src, dst):
rc = run_cmd(f"docker tag {src} {dst}")
if rc != 0:
raise RuntimeError('docker tag failed')




def push_with_retry(ref):
for i in range(RETRY):
rc = run_cmd(f"docker push {ref}")
if rc == 0:
return True
time.sleep(SLEEP)
raise RuntimeError('docker push failed')