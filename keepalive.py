from pythonping import ping
import os

hostname = os.environ['PING_URL']
response = ping(hostname, count=1, timeout=5, verbose=True)
