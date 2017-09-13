from utils.enoslib_task import enostask, _set_resultdir
from deploy5k.api import Resources
from qpid_generator.graph import generate
from qpid_generator.distribute import round_robin
from qpid_generator.configurations import get_conf
from utils.enoslib_ansible import run_ansible, generate_inventory

GRAPH_TYPE="complete_graph"
GRAPH_ARGS=[5]

cluster = "parasilo"
resources = {
    "machines":[{
        "roles": ["router", "cadvisor", "collectd"],
        "cluster": cluster,
        "nodes": 1,
        "primary_network": "n1",
        "secondary_networks": ["n2"]
    },{
        "roles": [
            "control",
            "registry",
            "grafana",
            "influx",
            "cadvisor",
            "collectd"
        ],
        "cluster": cluster,
        "nodes": 1,
        "primary_network": "n1",
        "secondary_networks": ["n2"]
    }],
    "networks": [{
        "id": "n1",
        "roles": ["control_network"],
        "type": "prod",
        "site": "rennes"
    },{
        "id": "n2",
        "roles": ["internal_network"],
        "type": "kavlan-local",
        "site": "rennes"
    }]
}

options = {
    "walltime": "02:40:00",
    "dhcp": True,
#    "force_deploy": "yes",
}

@enostask(new=True)
def launch(env=None, **kwargs):
    r = Resources(resources)

    r.launch(**options)
    roles = r.get_roles()
    env["roles"] = roles

@enostask()
def prepare(env=None, **kwargs):
    # Generate inventory
    roles = env["roles"]
    inventory = generate_inventory(roles)
    with open("ansible/hosts", "w") as f:
        f.write(inventory)

    extra_vars = {
        "registry": {
            "type": "internal"
        }
    }

    extra_vars = {
        "registry": {
            "type": "internal"
        }
    }

    # Deploys the monitoring stack and some common stuffs
    run_ansible(["ansible/prepare.yml"], "ansible/hosts", extra_vars=extra_vars)

@enostask()
def qpidd(env=None, *kwargs):
    roles = env["roles"]
    machines = [desc["host"] for desc in roles["router"]]
    graph = generate(GRAPH_TYPE, *GRAPH_ARGS)
    confs = get_conf(graph, machines, round_robin)
    qpidd_confs = {"qpidd_confs": confs.values()}
    env.update(qpidd_confs)
    run_ansible(["ansible/qpidd.yml"], "ansible/hosts", extra_vars=qpidd_confs)

@enostask()
def destroy(env=None, *kwargs):
    run_ansible(["ansible/destroy.yml"], "ansible/hosts")

