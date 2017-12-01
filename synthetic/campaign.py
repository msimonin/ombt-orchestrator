#!/usr/bin/env python

from execo_engine import sweep, ParamSweeper
import tasks as t
import os
import logging

PARAMETERS = {
    #"nbr_clients": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50],
    "nbr_clients": [1, 5],
    # "nbr_servers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "nbr_servers": [1],
    "call_type": ["rpc-cast", "rpc-call"],
    "nbr_calls": [10],
    "pause": [0],
    "timeout": [8000],
    "version": ["avankemp/ombt:avk_8dc7f42"]
}

BROKER = "rabbitmq"

BROKER="rabbitmq"
TEST_DIR = "tc1"

def generate_id(params):
    return "-".join([
        "%s__%s" % (k, v) for k, v in sorted(params.items())
    ])

def accept(params):
    call_ratio_max = 3
    cast_ratio_max = 3
    call_type = params["call_type"]
    if call_type == "rpc-call":
        if not params["pause"]:
            # maximum rate
            return call_ratio_max * params["nbr_servers"] >=  params["nbr_clients"]
        else:
            # we can afford more clients
            # based on our estimation a client sends 200msgs at full rate
            return call_ratio_max * params["nbr_servers"] >= params["nbr_clients"] * 200 * params["pause"]
    else:
        if not params["pause"]:
            # maximum rate
            return cast_ratio_max * params["nbr_servers"] >=  params["nbr_clients"]
        else:
            # we can afford more clients
            # based on our estimation a client sends 200msgs at full rate
            return cast_ratio_max * params["nbr_servers"] >= params["nbr_clients"] * 1000 * params["pause"]


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    initial_sweep = sweep(PARAMETERS)
    sweeps = sorted(initial_sweep, key=lambda k: k['nbr_clients'])

    sweeper = ParamSweeper(
        # Maybe puts the sweeper under the experimentation directory
        # This should be current/sweeps
        persistence_dir=os.path.join("%s/sweeps" % TEST_DIR),
        sweeps=sweeps,
        save_sweeps=True,
        name="test_case_1"
    )

    params = sweeper.get_next()
    while params:
        if not accept(params):
            # skipping element
            # Note that the semantic of sweeper.skip is different
            sweeper.done(params)
            params = sweeper.get_next()
            continue
        # cleaning old backup_dir
        params.pop("backup_dir", None)
        params.update({
            "backup_dir": generate_id(params)
        })
        t.vagrant(broker=BROKER, env=TEST_DIR)
        t.inventory()
        t.prepare(broker=BROKER)
        print(params)
        t.test_case_1(**params)
        sweeper.done(params)
        params = sweeper.get_next()
        t.destroy()

