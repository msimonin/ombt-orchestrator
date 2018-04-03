import networkx as nx


def get_conf(graph, machines, distribution):
    ntm, mtn = distribution(graph, machines)
    confs = {}
    router_idx = 0
    # a connector correspond to TCP connections
    # but will be used in both directions
    # Edge in the graph should correspond to a single
    # connection. So we keep track of the already created
    # connections.
    connections = []
    for node, nbrdict in graph.adjacency():
        confs.setdefault(node, {})
        machine = ntm[node]
        idx = mtn[machine].index(node)

        router_id = "router%s" % router_idx

        confs[node].update({
            'machine': machine,
            'router_id': router_id})

        confs[node].update({
            'listeners': [
                {
                    'host': machine,
                    'port': 6000 + idx,
                    'role': 'inter-router'
                },
                {
                    'host': machine,
                    'port': 5000 + idx,
                    'role': 'normal',

                    # use an extra field for the remaining options
                    'authenticatePeer': 'no',
                    'saslMechanisms': 'ANONYMOUS'
                }
            ]
        })

        # outgoing links
        connectors = []
        for out in nbrdict.keys():
            conn = sorted([node, out])
            if conn in connections:
                continue
            connections.append(conn)
            out_machine = ntm[out]
            out_idx = mtn[out_machine].index(out)

            connectors.append({
                'host': out_machine,
                'port': 6000 + out_idx,  # same rule as above
                'role': 'inter-router'
            })

        confs[node].update({'connectors': connectors})
        router_idx = router_idx + 1

    return confs


def round_robin(graph, machines):
    nodes_to_machines = {}
    machines_to_nodes = {}
    i = 0
    for node in graph.nodes():
        nodes_to_machines.update({node: machines[i]})
        machines_to_nodes.setdefault(machines[i], [])
        machines_to_nodes[machines[i]].append(node)
        i = (i + 1) % len(machines)
    return nodes_to_machines, machines_to_nodes


def generate(func_name, *args):
    return getattr(nx, func_name)(*args)
