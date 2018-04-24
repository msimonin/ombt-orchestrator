from abc import ABCMeta, abstractmethod
from os import path


class BusConf(object):
    """Common class to modelize bus configuration."""

    __metaclass__ = ABCMeta

    def __init__(self, conf):
        self.conf = conf
        self.transport = self.get_transport()

    @abstractmethod
    def get_listener(self, conf):
        pass

    @abstractmethod
    def get_transport(self):
        pass

    def to_dict(self):
        return self.conf


class RabbitMQConf(BusConf):

    def __init__(self, conf):
        super(RabbitMQConf, self).__init__(conf)

    def get_listener(self, **kwargs):
        """Returns the listener for rabbitmq.
        :param kwargs:
        """
        return {
            "machine": self.conf["machine"],
            "port": self.conf["port"]
        }

    def get_transport(self):
        return "rabbit"


class QdrConf(BusConf):

    def __init__(self, conf):
        super(QdrConf, self).__init__(conf)
        self.transport = "amqp"

    def get_listener(self, **kwargs):
        """Returns the listener for qdr.

        This is where external client can connect to.
        The contract is that this kind of listener has the role "normal"
        and there is exactly one such listener per router
        :param kwargs:
        """
        listeners = self.conf["listeners"]
        listener = [l for l in listeners if l["role"] == "normal"]
        return {
            "machine": listener[0]["host"],
            "port": listener[0]["port"]
        }

    def get_transport(self):
        return "amqp"


class OmbtAgent(object):
    """Modelize an ombt agent."""

    __metaclass__ = ABCMeta

    def __init__(self, **kwargs):
        # NOTE(msimonin): maybe use __getattr__ at some point
        self.agent_id = kwargs["agent_id"]
        self.machine = kwargs["machine"]
        self.control_agents = kwargs["control_agents"]
        self.bus_agents = kwargs["bus_agents"]
        self.timeout = kwargs["timeout"]
        # generated
        self.agent_type = self.get_type()
        # docker
        self.detach = True
        self.topic = kwargs["topic"]
        # calculated attr
        self.name = self.agent_id
        # where to log inside the container
        self.docker_log = "/home/ombt/ombt-data/agent.log"
        # where to log outside the container (mount)
        self.log = path.join("/tmp/ombt-data", "%s.log" % self.agent_id)
        # the command to run
        self.command = self.get_command()

    def to_dict(self):
        d = self.__dict__
        d.update({
            "control_agents": [a.to_dict() for a in self.control_agents],
            "bus_agents": [a.to_dict() for a in self.bus_agents],
        })
        return d

    @abstractmethod
    def get_type(self):
        pass

    def generate_connections(self):
        connections = {}
        for agents, agent_type in zip([self.control_agents, self.bus_agents], ["control", "url"]):
            connection = []
            for agent in agents:
                listener = agent.get_listener()
                transport = agent.transport
                connection.append("{{ hostvars['%s']['ansible_' + control_network]['ipv4']['address'] }}:%s" %
                                  (listener["machine"], listener["port"]))
            connections[agent_type] = "%s://%s" % (transport, ",".join(connection))
        return "--control %s --url %s" % (connections["control"], connections["url"])

    def get_command(self):
        """Build the command for the ombt agent.
        """
        command = []
        command.append("--debug")
        command.append("--unique")
        command.append("--timeout %s " % self.timeout)
        command.append("--topic %s " % self.topic)
        command.append(self.generate_connections())
        command.append(self.get_type())
        # NOTE(msimonin): we don't use verbosity for client/server
        # if self.verbose:
        #    command.append("--output %s " % self.docker_log)
        return command


class OmbtClient(OmbtAgent):

    def get_type(self):
        return "rpc-client"


class OmbtServer(OmbtAgent):

    def __init__(self, **kwargs):
        self.executor = kwargs["executor"]
        super(OmbtServer, self).__init__(**kwargs)

    def get_command(self):
        """Build the command for the ombt server.
        """
        command = super(OmbtServer, self).get_command()
        command.append("--executor %s" % self.executor)
        return command

    def get_type(self):
        return "rpc-server"


class OmbtController(OmbtAgent):

    def __init__(self, **kwargs):
        self.timeout = kwargs["timeout"]
        self.call_type = kwargs["call_type"]
        self.nbr_calls = kwargs["nbr_calls"]
        self.pause = kwargs["pause"]
        self.length = kwargs["length"]
        super(OmbtController, self).__init__(**kwargs)

    def get_type(self):
        return "controller"

    def get_command(self):
        """Build the command for the ombt controller.
        """
        command = super(OmbtController, self).get_command()
        # We always dump stat per agents
        command.append("--output %s" % self.docker_log)
        command.append(self.call_type)
        command.append("--calls %s" % self.nbr_calls)
        command.append("--pause %s" % self.pause)
        command.append("--length %s" % self.length)
        return " ".join(command)
