from __future__ import generators

import functools
import itertools
import json
import operator
import string
import time
import traceback
from os import path

import execo_engine
from enoslib.errors import EnosError
from execo_engine import ParamSweeper, HashableDict

import orchestrator.tasks as t


def filter_1(condition, parameters):
    if not condition:
        condition = (lambda x: x["nbr_servers"] <= x["nbr_clients"])
    return filter_params(parameters, condition=condition)


def filter_2(condition, parameters):
    # condition is not use but it is required because of functools.partial in campaign
    return filter_params(parameters, key="nbr_topics")


def filter_3(condition, parameters):
    # condition is not use but it is required because of functools.partial in campaign
    return filter_params(parameters, key="nbr_servers")


def filter_params(parameters, key="nbr_clients",
                  condition=lambda unused: True):
    filtered_parameters = (p for p in parameters if condition(p))
    return sort_parameters(filtered_parameters, key)


def sort_parameters(parameters, key):
    """
    Sort a list of parameters containing dictionaries.

    This kind of sort is performed to dictionaries containing at least elements with keys 'driver'
    and 'call_type'. It may also include other provided key as item for grouping by.

    >>> parameters = [
    ... {'other': 6, 'driver': 'router', 'call_type': 'rpc_cast', 'topic':'topic-1', 'nbr_clients': 60},
    ... {'other': 5, 'driver': 'router', 'call_type': 'rpc_cast', 'topic':'topic-2', 'nbr_clients': 40},
    ... {'other': 4, 'driver': 'router', 'call_type': 'rpc_call', 'topic':'topic-3', 'nbr_clients': 50},
    ... {'other': 3, 'driver': 'broker', 'call_type': 'rpc_cast', 'topic':'topic-4', 'nbr_clients': 30},
    ... {'other': 2, 'driver': 'broker', 'call_type': 'rpc_call', 'topic':'topic-5', 'nbr_clients': 20},
    ... {'other': 1, 'driver': 'router', 'call_type': 'rpc_cast', 'topic':'topic-6', 'nbr_clients': 70}]
    >>> sort_parameters(parameters, 'nbr_clients')
    [\
{'topic': 'topic-5', 'nbr_clients': 20, 'other': 2, 'driver': 'broker', 'call_type': 'rpc_call'}, \
{'topic': 'topic-4', 'nbr_clients': 30, 'other': 3, 'driver': 'broker', 'call_type': 'rpc_cast'}, \
{'topic': 'topic-3', 'nbr_clients': 50, 'other': 4, 'driver': 'router', 'call_type': 'rpc_call'}, \
{'topic': 'topic-2', 'nbr_clients': 40, 'other': 5, 'driver': 'router', 'call_type': 'rpc_cast'}, \
{'topic': 'topic-1', 'nbr_clients': 60, 'other': 6, 'driver': 'router', 'call_type': 'rpc_cast'}, \
{'topic': 'topic-6', 'nbr_clients': 70, 'other': 1, 'driver': 'router', 'call_type': 'rpc_cast'}]
    >>> sort_parameters(parameters, key='topic')
    [\
{'topic': 'topic-5', 'nbr_clients': 20, 'other': 2, 'driver': 'broker', 'call_type': 'rpc_call'}, \
{'topic': 'topic-4', 'nbr_clients': 30, 'other': 3, 'driver': 'broker', 'call_type': 'rpc_cast'}, \
{'topic': 'topic-3', 'nbr_clients': 50, 'other': 4, 'driver': 'router', 'call_type': 'rpc_call'}, \
{'topic': 'topic-1', 'nbr_clients': 60, 'other': 6, 'driver': 'router', 'call_type': 'rpc_cast'}, \
{'topic': 'topic-2', 'nbr_clients': 40, 'other': 5, 'driver': 'router', 'call_type': 'rpc_cast'}, \
{'topic': 'topic-6', 'nbr_clients': 70, 'other': 1, 'driver': 'router', 'call_type': 'rpc_cast'}]
    >>> sort_parameters(parameters, 'other')
    [\
{'topic': 'topic-5', 'nbr_clients': 20, 'other': 2, 'driver': 'broker', 'call_type': 'rpc_call'}, \
{'topic': 'topic-4', 'nbr_clients': 30, 'other': 3, 'driver': 'broker', 'call_type': 'rpc_cast'}, \
{'topic': 'topic-3', 'nbr_clients': 50, 'other': 4, 'driver': 'router', 'call_type': 'rpc_call'}, \
{'topic': 'topic-6', 'nbr_clients': 70, 'other': 1, 'driver': 'router', 'call_type': 'rpc_cast'}, \
{'topic': 'topic-2', 'nbr_clients': 40, 'other': 5, 'driver': 'router', 'call_type': 'rpc_cast'}, \
{'topic': 'topic-1', 'nbr_clients': 60, 'other': 6, 'driver': 'router', 'call_type': 'rpc_cast'}]

    :param parameters: a list of sub-dictionaries containing 'driver' and 'call_type' keys
    :param key:
    :return:
    """
    return sorted(parameters, key=operator.itemgetter("driver", "call_type", key))


def get_current_values(params, current, keys):
    """Infers the previous value for key in params regarding the current value.

    >>> # Single key
    >>> get_current_values({'key1': [1, 2, 3]}, {'key1': 1}, ['key1'])
    ([0], [1])
    >>> get_current_values({'key1': [1, 2, 3]}, {'key1': 2}, ['key1'])
    ([1], [2])
    >>> # Several keys
    >>> get_current_values({'key1': [1, 2, 3], 'key2': [4, 5, 6]}, {'key1': 2, 'key2': 5}, ['key1', 'key2'])
    ([1, 4], [2, 5])
    >>> # This allows to deal with constant values
    >>> get_current_values({'key1': [1, 2, 3], 'key2': [4, 4, 4]}, {'key1': 1, 'key2': 4}, ['key1', 'key2'])
    ([0, 0], [1, 4])
    >>> get_current_values({'key1': [1, 2, 3], 'key2': [4, 4, 4]}, {'key1': 2, 'key2': 4}, ['key1', 'key2'])
    ([1, 4], [2, 4])
    """
    plists = [params.get(key) for key in keys]
    states = [current.get(key) for key in keys]
    plists = list(zip(*plists))
    index = plists.index(tuple(states))
    return ([0] * len(states), states) if index == 0 else (plists[index - 1], states)


def fix_1(parameters, current_parameters):
    """
    >>> import pprint
    >>> parameters = {'nbr_clients': [1, 2, 3], 'nbr_servers': [4, 5, 6]}
    >>> current_parameters = {'nbr_clients': 1, 'nbr_servers': 4}
    >>> fix_1(parameters, current_parameters)
    >>> pprint.pprint(current_parameters)
    {'nbr_clients': 1, 'nbr_servers': 4, 'topics': ['topic-0']}

    >>> parameters = {'nbr_clients': [1, 2, 3], 'nbr_servers': [4, 5, 6]}
    >>> current_parameters = {'nbr_clients': 2, 'nbr_servers': 5}
    >>> fix_1(parameters, current_parameters)
    >>> pprint.pprint(current_parameters)
    {'nbr_clients': 1, 'nbr_servers': 1, 'topics': ['topic-0']}

    >>> # Allowing nbr_servers to be constants
    >>> parameters = {'nbr_clients': [1, 2, 3], 'nbr_servers': [4, 4, 4]}
    >>> current_parameters = {'nbr_clients': 2, 'nbr_servers': 4}
    >>> fix_1(parameters, current_parameters)
    >>> pprint.pprint(current_parameters)
    {'nbr_clients': 1, 'nbr_servers': 0, 'topics': ['topic-0']}

    >>> # Allowing nbr_servers to be constants
    >>> parameters = {'nbr_clients': [1, 2, 3], 'nbr_servers': [4, 4, 4]}
    >>> current_parameters = {'nbr_clients': 1, 'nbr_servers': 4}
    >>> fix_1(parameters, current_parameters)
    >>> pprint.pprint(current_parameters)
    {'nbr_clients': 1, 'nbr_servers': 4, 'topics': ['topic-0']}
    """
    # Note(msimonin): We may want to extend the get_current_value to all 'zip' elements
    [p_clients, p_servers], [c_clients, c_servers] = get_current_values(
        parameters, current_parameters, ["nbr_clients", "nbr_servers"])
    current_parameters.update({"topics": ["topic-0"]})
    current_parameters.update({"nbr_clients": c_clients - p_clients})
    current_parameters.update({"nbr_servers": c_servers - p_servers})


def fix_2(parameters, current_parameters):
    """
    >>> import pprint
    >>> parameters = {'nbr_topics': [1, 2, 3]}
    >>> current_parameters = {'nbr_topics': 1}
    >>> fix_2(parameters, current_parameters)
    >>> pprint.pprint(current_parameters)
    {'nbr_clients': 1, 'nbr_servers': 1, 'nbr_topics': 1, 'topics': ['topic-0']}

    >>> parameters = {'nbr_topics': [1, 2, 3]}
    >>> current_parameters = {'nbr_topics': 2}
    >>> fix_2(parameters, current_parameters)
    >>> pprint.pprint(current_parameters)
    {'nbr_clients': 1, 'nbr_servers': 1, 'nbr_topics': 2, 'topics': ['topic-1']}
    """
    topics_list = parameters["nbr_topics"]
    max_topics = max(topics_list)
    all_topics = t.get_topics(max_topics)
    [previous_nbr_topics], [nbr_topics] = get_current_values(
        parameters, current_parameters, ["nbr_topics"])
    current_topics = all_topics[previous_nbr_topics:nbr_topics]
    current_parameters.update({"topics": current_topics})
    current_parameters.update({"nbr_clients": len(current_topics)})
    current_parameters.update({"nbr_servers": len(current_topics)})


def fix_3(parameters, current_parameters):
    """
    >>> import pprint
    >>> parameters = {'nbr_servers': [4, 5, 6]}
    >>> current_parameters = {'nbr_servers': 4}
    >>> fix_3(parameters, current_parameters)
    >>> pprint.pprint(current_parameters)
    {'nbr_clients': 1, 'nbr_servers': 4, 'topics': ['topic-0']}

    >>> parameters = {'nbr_servers': [4, 5, 6]}
    >>> current_parameters = {'nbr_servers': 5}
    >>> fix_3(parameters, current_parameters)
    >>> pprint.pprint(current_parameters)
    {'nbr_clients': 0, 'nbr_servers': 1, 'topics': ['topic-0']}
    """

    [previous_servers], [current_servers] = get_current_values(
        parameters, current_parameters, ["nbr_servers"])
    if previous_servers:
        nbr_clients = 0

    else:
        nbr_clients = 1

    current_parameters.update({"topics": ["topic-0"]})
    current_parameters.update({"nbr_clients": nbr_clients})
    current_parameters.update({"nbr_servers": current_servers - previous_servers})


TEST_CASES = {
    "test_case_1": {"defn": t.test_case_1,
                    "filtr": filter_1,
                    "fixp": fix_1,
                    "key": "nbr_clients",
                    "zip": ["nbr_servers", "nbr_clients",
                            "nbr_calls", "pause"]},
    "test_case_2": {"defn": t.test_case_2,
                    "filtr": filter_2,
                    "fixp": fix_2,
                    "key": "nbr_topics",
                    "zip": ["nbr_topics", "nbr_calls", "pause"]},
    "test_case_3": {"defn": t.test_case_3,
                    "filtr": filter_3,
                    "fixp": fix_3,
                    "zip": ["nbr_servers", "nbr_calls", "pause"],
                    "key": "nbr_servers"},
    # TODO complete fixp and zip values
    "test_case_4": {"defn": t.test_case_4,
                    "filtr": filter_2,  # same as tc2
                    "key": "nbr_topics"}
}


def dump_parameters(directory, params):
    """Dump each parameter set in the backup directory.

    All parameters are dumped in the file <test>/params.json.
    If previous are found new ones are appended.

    :param directory: working directory
    :param params: JSON parameters to dump
    """
    json_params = path.join(directory, "params.json")
    if not path.exists(json_params):
        with open(json_params, "w") as f:
            json.dump([], f)
    # Add current parameters

    with open(json_params, "r") as f:
        all_params = json.load(f)

    all_params.append(params)
    with open(json_params, "w") as f:
        json.dump(all_params, f)


def generate_id(params):
    """Generate a unique ID based on the provided parameters.

        :param params: JSON parameters of an execution.
        :return: A unique ID.
        """

    def replace(s):
        return str(s).replace("/", "_sl_").replace(":", "_sc_")

    return "-".join(["%s__%s" % (replace(k), replace(v))
                     for k, v in sorted(params.items())])


def get_filter_function(name, flag):
    filter_function = TEST_CASES[name]["filtr"]
    predicate = (lambda x: True) if flag else None
    return functools.partial(filter_function, predicate)


def campaign(test, provider, unfiltered, force, config, env):
    parameters = config["campaign"][test]
    sweeps = execo_engine.sweep(parameters)
    env_dir = env if env else test
    sweeper = ParamSweeper(persistence_dir=path.join(env_dir, "sweeps"),
                           sweeps=sweeps, save_sweeps=True, name=test)
    t.PROVIDERS[provider](force=force, config=config, env=env_dir)
    t.inventory(env=env_dir)
    filter_function = get_filter_function(test, unfiltered)
    current_parameters = sweeper.get_next(filter_function)
    while current_parameters:
        try:
            delay = current_parameters.get("delay", None)
            if delay:
                traffic = current_parameters["traffic"]
                t.emulate(constraints=traffic, env=env_dir, override=delay)

            backup_directory = generate_id(current_parameters)
            current_parameters.update({"backup_dir": backup_directory})
            t.validate(env=env_dir, directory=backup_directory)
            t.prepare(driver=current_parameters["driver"], env=env_dir)
            TEST_CASES[test]["defn"](**current_parameters)
            t.backup(backup_dir=backup_directory, env=env_dir)
            sweeper.done(current_parameters)
            dump_parameters(env_dir, current_parameters)

        except (AttributeError, EnosError, RuntimeError,
                ValueError, KeyError, OSError) as error:
            sweeper.skip(current_parameters)
            traceback.print_exc()

        finally:
            t.reset(env=env_dir)
            t.destroy(env=env_dir)
            current_parameters = sweeper.get_next(filter_function)


def zip_parameters(parameters, arguments):
    """
    Select elements from a dictionary and group them as a list of
    sub-dictionaries preserving the original keys.

    The selected elements are defined in a list of arguments. That list is
    not validated against the keys of the original dictionary raising a
    'KeyError' exception if an element is not found in the dictionary. The
    elements are grouped using a 'zip' operation in a list of sub-dictionaries.
    In other words the zip performs a cross product between the key and each
    element of the value-list and a dot product between the results of the
    cross product of each argument.

    >>> parameters = {
    ... 'other': [6],
    ... 'nbr_servers': [1, 2, 3],
    ... 'call_type': ['rpc-call', 'rpc_cast'],
    ... 'topic':['topic-1', 'topic-2', 'topic-3', 'topic-4', 'topic-5'],
    ... 'pause': [0.1, 0.3, 0.5],
    ... 'nbr_clients': [10, 20, 30]}
    >>> arguments = ['nbr_servers', 'nbr_clients', 'pause']
    >>> zip_parameters(parameters, arguments)
    [\
{'nbr_servers': 1, 'pause': 0.1, 'nbr_clients': 10}, \
{'nbr_servers': 2, 'pause': 0.3, 'nbr_clients': 20}, \
{'nbr_servers': 3, 'pause': 0.5, 'nbr_clients': 30}]
    >>> arguments = ['topic', 'pause']
    >>> zip_parameters(parameters, arguments)
    [\
{'topic': 'topic-1', 'pause': 0.1}, \
{'topic': 'topic-2', 'pause': 0.3}, \
{'topic': 'topic-3', 'pause': 0.5}]
    >>> arguments = ['topic', 'call_type','other']
    >>> zip_parameters(parameters, arguments)
    [{'topic': 'topic-1', 'other': 6, 'call_type': 'rpc-call'}]
    >>> arguments = ['call_type']
    >>> zip_parameters(parameters, arguments)
    [{'call_type': 'rpc-call'}, {'call_type': 'rpc_cast'}]
    >>> arguments = []
    >>> zip_parameters(parameters, arguments)
    []
    >>> arguments = ['nonexistent']
    >>> zip_parameters(parameters, arguments) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ...
    KeyError:

    :param parameters: dictionary containing 'key:<list of values>' elements
    :param arguments: list of keys of the elements in the dictionary to zip
    :return: a list containing sub-dictionaries of zipped arguments
    """
    tuples = zip(*[[(k, v) for v in parameters[k]] for k in arguments])
    return [dict(z) for z in tuples]


def sweep_with_lists(parameters, arguments):
    # pack arguments to zip in lists to avoid sweep over them
    parameters = {k: ([v] if k in arguments else v)
                  for k, v in parameters.items()}
    sweeps = execo_engine.sweep(parameters)
    # transform list to immutable object
    sweeps = ({k: (tuple(v) if k in arguments else v)
               for k, v in l.items()} for l in sweeps)
    # transform dictionaries to hashable objects
    return [HashableDict(d) for d in sweeps]


def incremental_campaign(test, provider, pause, unfiltered, force, config, env):
    """Execute a test incrementally (reusing deployment).

    :param test: name of the test to execute
    :param provider: target infrastructure
    :param unfiltered: flag to set or avoid filter for sweeps
    :param pause: break between iterations in seconds
    :param force: override deployment configuration
    :param config: orchestration configuration
    :param env: directory containing the environment configuration
    """
    parameters = config["campaign"][test]
    arguments = TEST_CASES[test]["zip"]
    sweeps = sweep_with_lists(parameters, arguments)
    env_dir = env if env else "{}-incremental".format(test)
    sweeper = ParamSweeper(persistence_dir=path.join(env_dir, "sweeps"),
                           sweeps=sweeps, save_sweeps=True, name=test)
    t.PROVIDERS[provider](force=force, config=config, env=env_dir)
    t.inventory(env=env_dir)
    filter_function = get_filter_function(test, unfiltered)
    current_group = sweeper.get_next(filter_function)
    # use uppercase letters to identify groups
    groups = itertools.cycle(string.ascii_uppercase)
    while current_group:
        group_id = next(groups)
        # use numbers (incremental) to identify iterations by group
        iterations = itertools.count()
        try:
            current_driver = current_group["driver"]
            t.prepare(driver=current_driver, env=env_dir)
            for fixed_parameters in zip_parameters(current_group, arguments):
                current_parameters = current_group.copy()
                current_parameters.update(fixed_parameters)
                iteration = next(iterations)
                iteration_id = "{}-{}".format(group_id, iteration)
                current_delay = current_parameters.get("delay", None)
                if current_delay:
                    current_traffic = current_parameters["traffic"]
                    t.emulate(constraints=current_traffic, env=env_dir,
                              override=current_delay)

                backup_directory = generate_id(current_parameters)
                t.validate(env=env_dir, directory=backup_directory)
                current_parameters.update({"iteration_id": iteration_id})
                current_parameters.update({"backup_dir": backup_directory})
                # fix number of clients and servers (or topics) to deploy
                TEST_CASES[test]["fixp"](parameters, current_parameters)
                TEST_CASES[test]["defn"](**current_parameters)
                t.backup(backup_dir=backup_directory, env=env_dir)
                dump_parameters(env_dir, current_parameters)
                t.reset(env=env_dir)
                time.sleep(pause)
            sweeper.done(current_group)

        except (AttributeError, EnosError, RuntimeError,
                ValueError, KeyError, OSError) as error:
            sweeper.skip(current_group)
            traceback.print_exc()

        finally:
            t.destroy(env=env_dir)
            current_group = sweeper.get_next(filter_function)
