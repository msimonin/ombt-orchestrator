#!/usr/bin/env python

from deploy5k.api import Resources
from utils.enoslib_ansible import run_ansible, generate_inventory

from qpid_generator.graph import generate
from qpid_generator.distribute import round_robin
from qpid_generator.configurations import get_conf

import logging

logging.basicConfig(level=logging.DEBUG)

resources = {
    "machines":[{
        "roles": ["router", "cadvisor", "collectd"],
        "cluster": "paravance",
        "nodes": 1,
        "primary_network": "control_network",
        "secondary_networks": ["internal_network"]
    },{
        "roles": [
            "control",
            "registry",
            "grafana",
            "influx",
            "cadvisor",
            "collectd"
        ],
        "cluster": "paravance",
        "nodes": 1,
        "primary_network": "control_network",
        "secondary_networks": ["internal_network"]
    }],
    "networks": [{
        "role": "control_network",
        "type": "prod",
        "site": "rennes"
    },{
        "role": "internal_network",
        "type": "kavlan-local",
        "site": "rennes"
    }]
}

options = {
    "walltime": "02:40:00",
    "dhcp": True,
#    "force_deploy": "yes",
}


if __name__ == "__main__":
    r = Resources(resources)

    r.launch(**options)
    roles = r.get_roles()

    # Generate inventory
    inventory = generate_inventory(roles)
    with open("ansible/hosts", "w") as f:
        f.write(inventory)

    extra_vars = {
        "registry": {
            "type": "internal"
        }
    }

    # Deploys the monitoring stack and some common stuffs
    run_ansible(["ansible/site.yml"], "ansible/hosts", extra_vars=extra_vars)

    graph_type = "complete_graph"
    machines = [desc["host"] for desc in roles["router"]]
    graph = generate(graph_type, len(machines))

    confs = get_conf(graph, machines, round_robin)
    print(confs)
