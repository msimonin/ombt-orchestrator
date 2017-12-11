#!/usr/bin/env python

from execo_engine import sweep, ParamSweeper
import tasks as t
import os
import logging

PARAMETERS = {
    # "nbr_servers": [1, 5, 10, 50, 100, 200, 300, 400, 500],
    "nbr_servers": [1, 5, 10],
    # "nbr_clients": [1, 10, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
    "nbr_clients": [1],
    "call_type": ["rpc-cast", "rpc-call"],
    "nbr_calls": [100],
    "pause": [0],
    "timeout": [8000],
    "version": ["avankemp/ombt:TestResults_todict_fixed"],
    "length": [6000000]
}

BROKER = "rabbitmq"
TEST_DIR = "tc1"


def generate_id(params):
    def clean(s):
        return str(s).replace("/", "_sl_") \
            .replace(":", "_sc_")

    return "-".join([
        "%s__%s" % (clean(k), clean(v)) for k, v in sorted(params.items())
    ])


def accept(params):
    call_ratio_max = 3
    cast_ratio_max = 3
    call_type = params["call_type"]
    if call_type == "rpc-call":
        if not params["pause"]:
            # maximum rate
            return call_ratio_max * params["nbr_servers"] >= params["nbr_clients"]
        else:
            # we can afford more clients
            # based on our estimation a client sends 200msgs at full rate
            return call_ratio_max * params["nbr_servers"] >= params["nbr_clients"] * 200 * params["pause"]
    else:
        if not params["pause"]:
            # maximum rate
            return cast_ratio_max * params["nbr_servers"] >= params["nbr_clients"]
        else:
            # we can afford more clients
            # based on our estimation a client sends 200msgs at full rate
            return cast_ratio_max * params["nbr_servers"] >= params["nbr_clients"] * 1000 * params["pause"]


# Function to pass in parameter to ParamSweeper.get_next()
# Give the illusion that the Set of params is sorted by nbr_clients
def sort_params_by_nbr_clients(set):
    return sorted((list(set)), key=lambda k: k['nbr_clients'])


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sweeps = sweep(PARAMETERS)
    filtered_sweeps = [param for param in sweeps if accept(param)]
    sweeper = ParamSweeper(
        # Maybe puts the sweeper under the experimentation directory
        # This should be current/sweeps
        persistence_dir=os.path.join("%s/sweeps" % TEST_DIR),
        sweeps=filtered_sweeps,
        save_sweeps=True,
        name="test_case_1"
    )

    # Get the next parameter in the set of all remaining params
    # This set is temporary viewed as sorted List with this filter function.
    params = sweeper.get_next(sort_params_by_nbr_clients)
    t.vagrant(broker=BROKER, env=TEST_DIR)
    t.inventory()
    
    while params:
        params.pop("backup_dir", None)
        params.update({
            "backup_dir": generate_id(params)
        })
        t.prepare(broker=BROKER)
        print(params)
        t.test_case_1(**params)
        sweeper.done(params)
        params = sweeper.get_next(sort_params_by_nbr_clients)
        t.destroy()
