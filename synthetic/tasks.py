from enoslib.api import run_ansible, generate_inventory, emulate_network, validate_network
from enoslib.task import enostask
from enoslib.infra.enos_g5k.provider import G5k
from enoslib.infra.enos_vagrant.provider import Enos_vagrant
from qpid_generator.graph import generate
from qpid_generator.distribute import round_robin
from qpid_generator.configurations import get_conf

import os
import yaml

GRAPH_TYPE="complete_graph"
GRAPH_ARGS=[4]
BROKER="qdr"

tc = {
    "enable": True,
    "default_delay": "20ms",
    "default_rate": "1gbit",
}


# The two following tasks are exclusive either you choose to go with g5k or
# vagrant you can't mix the two of them in the future we might want to
# factorize it and have a switch on the command line to choose.
@enostask(new=True)
def g5k(env=None, broker=BROKER, force=False, **kwargs):
    with open("confs/g5k-%s.yaml" % broker) as f:
        g5k_config = yaml.load(f)
        provider = G5k(g5k_config)
        roles, networks = provider.init(force_deploy=force)
        env["roles"] = roles
        env["networks"] = networks


@enostask(new=True)
def vagrant(env=None, broker=BROKER, force=False, **kwargs):
    with open("confs/vagrant-%s.yaml" % broker) as f:
        vagrant_config = yaml.load(f)
        provider = Enos_vagrant(vagrant_config)
        roles, networks = provider.init(force_deploy=force)
        # saving the roles
        env["roles"] = roles
        env["networks"] = networks


@enostask()
def inventory(env=None, **kwargs):
    roles = env["roles"]
    networks = env["networks"]
    env["inventory"] = os.path.join(env["resultdir"], "hosts")
    generate_inventory(roles, networks, env["inventory"] , check_networks=True)


@enostask()
def prepare(env=None, broker=BROKER, **kwargs):
    # Generate inventory
    extra_vars = {
        "registry": {
            "type": "internal"
        },
        "broker": broker
    }
    # Preparing the installation of the bus under evaluation
    # Need to pass specific options
    if broker == "rabbitmq":
        # Nothing to do
        pass
    elif broker == "qdr":
        # Building the graph of routers
        roles = env["roles"]
        machines = [desc.alias for desc in roles["bus"]]
        graph = generate(GRAPH_TYPE, *GRAPH_ARGS)
        confs = get_conf(graph, machines, round_robin)
        qdr_confs = {"qdr_confs": confs.values()}
        extra_vars.update(qdr_confs)
        env.update(qdr_confs)
    else:
        raise Exception("Unknown broker chosen")

    # use deploy of each role
    extra_vars.update({"enos_action": "deploy"})

    run_ansible(["ansible/site.yml"], env["inventory"], extra_vars=extra_vars)
    env["broker"] = broker


@enostask()
def test_case_1(
    nbr_clients,
    nbr_servers,
    call_type,
    nbr_calls,
    pause,
    timeout,
    version,
    verbose=None,
    backup_dir="backup",
    env=None, **kwargs):

    iteration_id = str("-".join([
        "nbr_servers__%s" % nbr_servers,
        "nbr_clients__%s" % nbr_clients,
        "call_type__%s" % call_type,
        "nbr_calls__%s" % nbr_calls,
        "pause__%s" % pause]))

    # Create the backup dir for this experiment
    # NOTE(msimonin): We don't need to identify the backup dir
    # we could use a dedicated env name for that
    backup_dir = os.path.join(os.getcwd(), "current/%s" % backup_dir)
    os.system("mkdir -p %s" % backup_dir)
    # Global variables to the ombt deployment
    agent_log = "/home/ombt/ombt-data/client.log"
    extra_vars = {
        "backup_dir": backup_dir,
        "ombt_version": version,
        "agent_log": agent_log
    }


    def generate_agent_command(agent_type):
        """Build the command for the ombt agent [client|server]"""
        command = ""
        command += " --debug "
        command += " --timeout %s " % timeout
        # building the right url is delegated to ansible NOTE(msimonin): we
        # could do it on python side but this will require to save all the
        # facts
        command += " --control rabbit://{{ hostvars[groups['control-bus'][0]]['ansible_' + control_network]['ipv4']['address'] }}:{{ rabbitmq_port }} "
        command += " --url rabbit://{{ hostvars[groups['bus'][0]]['ansible_' + control_network]['ipv4']['address'] }}:{{ rabbitmq_port }} "
        command += " %s " % agent_type
        # TODO(msimonin) make this conditionnal
        if verbose:
            command += " --output %s " % agent_log
        return command


    def generate_controller_command(agent_type):
        """Build the command for the ombt agent [client|server]"""
        command = ""
        command += "--debug"
        # building the right url is delegated to ansible NOTE(msimonin): we
        # could do it on python side but this will require to save all the
        # facts
        command += " --control rabbit://{{ hostvars[groups['control-bus'][0]]['ansible_' + control_network]['ipv4']['address'] }}:{{ rabbitmq_port }} "
        command += " --url rabbit://{{ hostvars[groups['bus'][0]]['ansible_' + control_network]['ipv4']['address'] }}:{{ rabbitmq_port }} "
        command += " controller "
        command += " %s " % call_type
        command += " --calls %s " % nbr_calls
        command +=" --pause %s " % pause
        return command

    descs = [{
        "number": int(nbr_clients),
        "machines": env["roles"]["ombt-client"],
        "type": "rpc-client",
        "command_generator": generate_agent_command,
        "detach": True
    }, {
        "number": int(nbr_servers),
        "machines": env["roles"]["ombt-server"],
        "type": "rpc-server",
        "command_generator": generate_agent_command,
        "detach": True
    }, {
        "number": 1,
        "machines": env["roles"]["ombt-control"],
        "type": "controller",
        "command_generator": generate_controller_command,
        "detach": False
    }]

    # Below we build the specific variables for each client/server
    ombt_confs= []
    for agent_desc in descs:
        machines = agent_desc["machines"]
        for agent_index in range(agent_desc["number"]):
            agent_id = "%s-%s-%s" % (agent_desc["type"], agent_index, iteration_id)
            ombt_confs.append({
                "machine": machines[agent_index % len(machines)].alias,
                "command": agent_desc["command_generator"](agent_desc["type"]),
                "name": agent_id,
                "log": "%s.log" % agent_id,
                "detach": agent_desc["detach"]
            })
    extra_vars.update({"ombt_confs": ombt_confs})
    run_ansible(["ansible/test_case_1.yml"], env["inventory"], extra_vars=extra_vars)
    # saving the conf
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
def backup(env=None, **kwargs):
    extra_vars = {
        "enos_action": "backup",
        "backup_dir": os.path.join(os.getcwd(), "current")
    }
    run_ansible(["ansible/site.yml"], env["inventory"], extra_vars=extra_vars)


@enostask()
def destroy(env=None, **kwargs):
    extra_vars = {}
    # Call destroy on each component
    extra_vars.update({
        "enos_action": "destroy",
        "broker": env["broker"],
        "qdr_confs": env.get("qdr_confs")
    })
    run_ansible(["ansible/site.yml"], env["inventory"], extra_vars=extra_vars)
    run_ansible(["ansible/ombt.yml"], env["inventory"], extra_vars=extra_vars)

