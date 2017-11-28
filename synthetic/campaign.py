#!/usr/bin/env python

from execo_engine import sweep, ParamSweeper
import tasks as t
import os

PARAMETERS = {
    "nbr_clients": [1, 10],
    "nbr_servers": range(1, 11),
    "call_type": ["rpc-cast", "rpc-call"],
    "nbr_calls": ["500000"],
    "pause": 0,
    "timeout": 3600,
    "version": "2.1.0"
}

BROKER="rabbitmq"

if __name__ == "__main__":
    # We probably want to force the experimentation directory
    # t.vagrant(broker=BROKER, env="test_case_1")
    t.vagrant(broker=BROKER)
    t.inventory()
    t.prepare(broker=BROKER)

    sweeps = sweep(PARAMETERS)
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
        print(params)
        sweeper.done(params)
        # t.test_case_1(<fill with the right params>)
        # Note that if we use keywords arguments for test_case_1
        # we could just use **PARAMETERS here :)

        #t.destroy()

        # only reapplying the prepare phase *should* be fine
        # but don't forget to change the backup directory
        # since everything will be under the same xp directory
        # t.prepare()
        params = sweeper.get_next()
