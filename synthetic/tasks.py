from enoslib.api import run_ansible, generate_inventory, emulate_network, validate_network
from enoslib.task import enostask
from enoslib.infra.enos_g5k.provider import G5k
from enoslib.infra.enos_vagrant.provider import Enos_vagrant
from qpid_generator.graph import generate
from qpid_generator.distribute import round_robin
from qpid_generator.configurations import get_conf
from utils.roles import to_enos_roles

import os
import yaml

GRAPH_TYPE="complete_graph"
GRAPH_ARGS=[5]
BROKER="qpidd"

tc = {
    "enable": True,
    "default_delay": "20ms",
    "default_rate": "1gbit",
    "groups": ["router-client", "router-server"]
}


# The two following tasks are exclusive either you choose to go with g5k or
# vagrant you can't mix the two of them in the future we might want to
# factorize it and have a switch on the command line to choose.
@enostask(new=True)
def g5k(broker=BROKER, force=False, env=None, **kwargs):
    with open("confs/g5k-%s.yaml" % broker) as f:
        g5k_config = yaml.load(f)
        provider = G5k(g5k_config)
        roles, networks = provider.init(force_deploy=force)
        env["roles"] = roles
        env["networks"] = networks


@enostask(new=True)
def vagrant(broker=BROKER, force=False, env=None, **kwargs):
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
def prepare(env=None, **kwargs):
    # Generate inventory
    extra_vars = {
        "registry": {
            "type": "internal"
        }
    }
    # Deploys the monitoring stack and some common stuffs
    run_ansible(["ansible/prepare.yml"], env["inventory"], extra_vars=extra_vars)


@enostask()
def qpidd(env=None, *kwargs):
    roles = env["roles"]
    machines = [desc.alias for desc in roles["router"]]
    graph = generate(GRAPH_TYPE, *GRAPH_ARGS)
    confs = get_conf(graph, machines, round_robin)
    qpidd_confs = {"qpidd_confs": confs.values()}
    env.update(qpidd_confs)
    run_ansible(["ansible/qpidd.yml"], env["inventory"], extra_vars=qpidd_confs)


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
def destroy(env=None, *kwargs):
    run_ansible(["ansible/destroy.yml"], env["inventory"])

