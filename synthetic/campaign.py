#!/usr/bin/env python

from execo_engine import sweep, ParamSweeper
import tasks as t
import os
import logging

PARAMETERS = {
    "nbr_clients": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50],
    "nbr_servers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "call_type": ["rpc-cast", "rpc-call"],
    "nbr_calls": [100000],
    "pause": [0],
    "timeout": [8000],
    "version": ["avk_8dc7f42"]
}

BROKER = "rabbitmq"

if __name__ == "__main__":
    # We probably want to force the experimentation directory
    # t.vagrant(broker=BROKER, env="test_case_1")
    logging.basicConfig(level=logging.DEBUG)
    initial_sweep = sweep(PARAMETERS)
    sweeps = sorted(initial_sweep, key=lambda k: k['nbr_clients'])

    t.g5k(broker=BROKER)
    t.inventory()
    t.prepare(broker=BROKER)

    sweeper = ParamSweeper(
        # Maybe puts the sweeper under the experimentation directory
        # This should be current/sweeps
        persistence_dir=os.path.join("sweeps"),
        sweeps=sweeps,
        save_sweeps=True,
        name="test_case_1"
    )
    params = sweeper.get_next()
    while params:
        t.test_case_1(params["nbr_clients"], params["nbr_servers"], params["call_type"], params["nbr_calls"],
                      params["pause"], params["timeout"], params["version"], verbose=False, backup_dir="backup_dir")
        sweeper.done(params)
        t.destroy()

        t.g5k(broker=BROKER)
        t.inventory()
        t.prepare(broker=BROKER)
        # t.test_case_1(<fill with the right params>)
        # Note that if we use keywords arguments for test_case_1
        # we could just use **PARAMETERS here :)
        #t.destroy()

        # only reapplying the prepare phase *should* be fine
        # but don't forget to change the backup directory
        # since everything will be under the same xp directory
        # t.prepare()
        params = sweeper.get_next()

        # "nbr_clients": [1, 10, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        # "nbr_servers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 50, 100],
        # "call_type": ["rpc-cast", "rpc-call"],
        # "nbr_calls": [500000],
        # "pause": [0],
        # "timeout": [3600],
        # "version": ["avk_8dc7f42"]

