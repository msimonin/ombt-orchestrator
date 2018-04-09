import os

OO_PATH = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

ANSIBLE_DIR = os.path.join(OO_PATH, "ansible")
# default app configuration
CONF = os.path.join(os.getcwd(), "conf.yaml")
# default driver type
DRIVER_NAME = "broker"
# default number of clients
NBR_CLIENTS = 1
# default number of servers
NBR_SERVERS = 1
# default number topics
NBR_TOPICS = 1
# default call type
CALL_TYPE = "rpc-call"
# default number of calls
NBR_CALLS = 100
# default pause between calls
PAUSE = 0.0
# default timeout
TIMEOUT = 60
# default version of ombt container
VERSION = "msimonin/ombt:singleton"
# default backup directory name
BACKUP_DIR = "backup"
# default length of messages
LENGTH = 1024
# default type of ombt executor
EXECUTOR = "threading"
# default pause between iterations (seconds)
ITERATION_PAUSE = 1.0

DRIVER = {'type': 'rabbitmq',
          'mode': 'standalone'}
