from fabric import Connection

def cleanup_remote(host, user='ubuntu'):
    c = Connection(f"{user}@{host}")
    c.run('docker system prune -af')
