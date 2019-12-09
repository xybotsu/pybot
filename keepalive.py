import os, requests, logging

hostname = os.environ['PING_URL']
response = requests.get(hostname)
status = response.status_code

if status==200:
  logging.info('Ping!')
else:
  logging.warning('Ping failed with status: '+str(status))

