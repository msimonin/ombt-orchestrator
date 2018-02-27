import os
from abc import ABCMeta, abstractmethod

import yaml
from enoslib.api import run_ansible, generate_inventory, emulate_network, validate_network
from enoslib.infra.enos_chameleonkvm.provider import Chameleonkvm
from enoslib.infra.enos_g5k.provider import G5k
from enoslib.infra.enos_vagrant.provider import Enos_vagrant
from enoslib.task import enostask

from qpid_dispatchgen import get_conf, generate, round_robin

# DEFAULT PARAMETERS
DRIVER = "rabbitmq"
NBR_CLIENTS = 1
NBR_SERVERS = 1
NBR_TOPICS = 1
CALL_TYPE = "rpc-call"
NBR_CALLS = 100
PAUSE = 0.0
TIMEOUT = 60
VERSION = "beyondtheclouds/ombt:latest"
BACKUP_DIR = "backup"
LENGTH = 1024
EXECUTOR = "threading"

tc = {
    "enable": True,
    "default_delay": "20ms",
    "default_rate": "1gbit",
}


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
        self.log = os.path.join("/tmp/ombt-data", "%s.log" % self.agent_id)
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


def load_config(path):
    """
    Read configuration from a file in YAML format.
    :param path: Path of the configuration file.
    :return:
    """
    with open(path) as f:
        configuration = yaml.safe_load(f)
    return configuration


def get_backup_directory(backup_dir):
    # Create the backup dir for an experiment
    # NOTE(msimonin): We don't need to identify the backup dir we could use a dedicated env name for that
    cwd = os.getcwd()
    # 'current' directory is constant because it depends on enoslib implementation
    current_directory = os.path.join(cwd, 'current')
    backup_dir = os.path.join(current_directory, backup_dir)
    # TODO remove sys call by python API
    os.system("mkdir -p %s" % backup_dir)
    return backup_dir


def get_topics(number):
    """Create a list of topic names.

    The names have the following format: topic_<id>. Where the id is a normalized number preceded by leading zeros.

    >>> get_topics(1)
    ['topic-0']
    >>> get_topics(2)
    ['topic-0', 'topic-1']
    >>> get_topics(0)
    []
    >>> get_topics(10)
    ['topic-0', 'topic-1', 'topic-2', 'topic-3', 'topic-4', 'topic-5', 'topic-6', 'topic-7', 'topic-8', 'topic-9']
    >>> (get_topics(11)
    ['topic-00', 'topic-01', 'topic-02', 'topic-03', 'topic-04', 'topic-05', 'topic-06', 'topic-07', 'topic-08', 'topic-09', 'topic-10']

    :param number: Number of topic names to generate.
    :return: A list of topic names.
    """
    length = len(str(number)) if number % 10 else len(str(number)) - 1
    sequence = ('{number:0{width}}'.format(number=n, width=length) for n in range(number))
    return ['topic-' + e for e in sequence]


# The two following tasks are exclusive either you choose to go with g5k or
# vagrant you can't mix the two of them in the future we might want to
# factorize it and have a switch on the command line to choose.
@enostask(new=True)
def g5k(force=False, config=None, env=None, **kwargs):
    init_provider(G5k, 'g5k', env=env, force=force, config=config, **kwargs)


@enostask(new=True)
def vagrant(force=False, config=None, env=None, **kwargs):
    init_provider(Enos_vagrant, 'vagrant', env=env, force=force, config=config, **kwargs)


@enostask(new=True)
def chameleon(force=False, config=None, env=None, **kwargs):
    init_provider(Chameleonkvm, 'chameleon', env=env, force=force, config=config, **kwargs)


def init_provider(provider, name, force=False, env=None, config=None, **kwargs):
    instance = provider(config[name])
    roles, networks = instance.init(force_deploy=force)
    env["config"] = config
    env["roles"] = roles
    env["networks"] = networks


PROVIDERS = {
    "g5k": g5k,
    "vagrant": vagrant,
    "chameleon": chameleon
}


@enostask()
def inventory(env=None, **kwargs):
    roles = env["roles"]
    networks = env["networks"]
    env["inventory"] = os.path.join(env["resultdir"], "hosts")
    generate_inventory(roles, networks, env["inventory"], check_networks=True)


def generate_bus_conf(config, machines):
    """Generate the bus configuration.

    Args:
        config(dict): Configuration of the bus (Mostly extracted from the global config)
        machines(list): machines on which the bus agents will be installed

    Returns:
        List of configurations to use for each machine.
    """
    if config["type"] == "rabbitmq":
        bus_conf = [{
            "port": 5672,
            "management_port": 15672,
            "machine": machine
        } for machine in machines]
        # saving the conf object
        bus_conf = [RabbitMQConf(c) for c in bus_conf]
    elif config["type"] == "qdr":
        # Building the graph of routers
        graph = generate(config["topology"], *config["args"])
        bus_conf = get_conf(graph, machines, round_robin)
        bus_conf = [QdrConf(c) for c in bus_conf.values()]
    else:
        raise TypeError("Unknown broker chosen")
    return bus_conf


@enostask()
def prepare(driver=DRIVER, env=None, **kwargs):
    # Generate inventory
    extra_vars = {
        "registry": env["config"]["registry"],
        "broker": env['config']['drivers'][driver]['type']
    }
    # Preparing the installation of the bus under evaluation
    # Need to pass specific options
    # We generate a configuration dict that captures the minimal set of
    # parameters of each agents of the bus
    # This configuration dict is used in subsequent test* tasks to configure the
    # ombt agents.

    roles = env['roles']
    # Get the config of the bus, inject the type
    config = env['config']['drivers'].get(driver)

    def generate_ansible_conf(configuration, role):
        machines = [desc.alias for desc in roles[role]]
        bus_conf = generate_bus_conf(configuration, machines)
        # the key for the 'control-bus' role is 'control_bus'
        key = '{}_conf'.format(role.replace('-', '_'))
        env.update({key: bus_conf})
        ansible_conf = {key: [b.to_dict() for b in bus_conf]}
        # inject the bus configuration taken from the configuration
        ansible_conf.update(configuration)
        return ansible_conf

    ansible_bus_conf = generate_ansible_conf(config, 'bus')
    # Note(msimonin): use an implicit rabbitmq broker for the control-bus
    rabbit_conf =  {
        "type": "rabbitmq"
    }
    ansible_control_bus_conf = generate_ansible_conf(rabbit_conf, 'control-bus')
    # use deploy of each role
    extra_vars.update({"enos_action": "deploy"})
    extra_vars.update(ansible_bus_conf)
    extra_vars.update(ansible_control_bus_conf)
    # finally let's give ansible the bus conf
    if config:
        extra_vars.update(config)

    run_ansible(["ansible/site.yml"], env["inventory"], extra_vars=extra_vars)
    env["broker"] = config['type']


@enostask()
def test_case_1(**kwargs):
    # enforcing topic proper value in case the topics are declared in campaign
    kwargs['nbr_topics'] = 1
    test_case(**kwargs)


@enostask()
def test_case_2(**kwargs):
    kwargs['nbr_clients'] = kwargs['nbr_topics']
    kwargs['nbr_servers'] = kwargs['nbr_topics']
    test_case(**kwargs)


@enostask()
def test_case_3(**kwargs):
    # enforcing topic proper value in case the topics are declared in campaign
    kwargs['nbr_topics'] = 1
    kwargs['call_type'] = 'rpc_cast'
    test_case(**kwargs)


@enostask()
def test_case_4(**kwargs):
    kwargs['nbr_clients'] = kwargs['nbr_topics'] * kwargs['nbr_clients']
    kwargs['nbr_servers'] = kwargs['nbr_topics'] * kwargs['nbr_servers']
    kwargs['call_type'] = 'rpc_cast'
    test_case(**kwargs)


def test_case(
        nbr_clients=NBR_CLIENTS,
        nbr_servers=NBR_SERVERS,
        nbr_topics=NBR_TOPICS,
        call_type=CALL_TYPE,
        nbr_calls=NBR_CALLS,
        pause=PAUSE,
        timeout=TIMEOUT,
        length=LENGTH,
        executor=EXECUTOR,
        version=VERSION,
        backup_dir=BACKUP_DIR,
        env=None, **kwargs):
    backup_dir = get_backup_directory(backup_dir)
    extra_vars = {
        "backup_dir": backup_dir,
        "ombt_version": version,
    }

    # description template of agents
    descs = [
        {
            "agent_type": "rpc-client",
            "number": int(nbr_clients),
            "machines": env["roles"]["ombt-client"],
            "klass": OmbtClient,
            "kwargs": {
                "timeout": timeout,
            }
        },
        {
            "agent_type": "rpc-server",
            "number": int(nbr_servers),
            "machines": env["roles"]["ombt-server"],
            "klass": OmbtServer,
            "kwargs": {
                "timeout": timeout,
                "executor": executor,
            }
        },
        {
            "agent_type": "controller",
            "number": int(nbr_topics),
            "machines": env["roles"]["ombt-control"],
            "klass": OmbtController,
            "kwargs": {
                "call_type": call_type,
                "nbr_calls": nbr_calls,
                "pause": pause,
                "timeout": timeout,
                "length": length,
            }
        }]

    iteration_id = str("-".join([
        "nbr_servers__%s" % nbr_servers,
        "nbr_clients__%s" % nbr_clients,
        "nbr_topics__%s" % nbr_topics,
        "call_type__%s" % call_type,
        "nbr_calls__%s" % nbr_calls,
        "pause__%s" % pause]))

    # build the specific variables for each client/server:
    # ombt_conf = {
    #   "machine01": [confs],
    #   ...
    # }
    ombt_confs = {}
    bus_conf = env["bus_conf"]
    control_bus_conf = env["control_bus_conf"]
    topics = get_topics(nbr_topics)
    for agent_desc in descs:
        machines = agent_desc["machines"]
        # make sure all the machines appears in the ombt_confs
        for machine in machines:
            ombt_confs.setdefault(machine.alias, [])

        for agent_index in range(agent_desc["number"]):
            # choose a topic
            topic = topics[agent_index % len(topics)]
            # choose a machine
            machine = machines[agent_index % len(machines)].alias
            # choose a bus agent
            bus_agent = bus_conf[agent_index % len(bus_conf)]
            agent_id = "%s-%s-%s-%s" % (agent_desc["agent_type"], agent_index, topic, iteration_id)
            control_agent = control_bus_conf[agent_index % len(control_bus_conf)]
            kwargs = agent_desc["kwargs"]
            kwargs.update({
                "agent_id": agent_id,
                "machine": machine,
                "bus_agents": [bus_agent],
                "topic": topic,
                "control_agents": [control_agent]  # TODO
            })
            ombt_confs[machine].append(agent_desc["klass"](**kwargs))

    ansible_ombt_confs = {}
    for m, confs in ombt_confs.items():
        ansible_ombt_confs[m] = [o.to_dict() for o in confs]

    extra_vars.update({'ombt_confs': ansible_ombt_confs})
    run_ansible(["ansible/test_case_1.yml"], env["inventory"], extra_vars=extra_vars)
    # save the conf
    env["ombt_confs"] = ombt_confs


@enostask()
def emulate(env=None, **kwargs):
    inventory = env["inventory"]
    roles = env["roles"]
    emulate_network(roles, inventory, tc)


@enostask()
def validate(env=None, **kwargs):
    inventory = env["inventory"]
    roles = env["roles"]
    validate_network(roles, inventory)


@enostask()
def backup(backup_dir=BACKUP_DIR,
           env=None, **kwargs):
    backup_dir = get_backup_directory(backup_dir)
    extra_vars = {
        "enos_action": "backup",
        "backup_dir": backup_dir
    }

    run_ansible(["ansible/site.yml"], env["inventory"], extra_vars=extra_vars)


@enostask()
def destroy(env=None, **kwargs):
    # Call destroy on each component
    extra_vars = {
        "enos_action": "destroy",
        "broker": env["broker"],
        "bus_conf": [o.to_dict() for o in env.get("bus_conf")]
    }

    run_ansible(["ansible/site.yml"], env["inventory"], extra_vars=extra_vars)
    run_ansible(["ansible/ombt.yml"], env["inventory"], extra_vars=extra_vars)
