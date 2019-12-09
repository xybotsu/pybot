import os, logging

hostname = os.environ['PING_URL']
response = os.system("ping -c 1 " + hostname)

if response == 0:
  logger.info('Ping!')
else:
  logger.warning('Could not ping server')
