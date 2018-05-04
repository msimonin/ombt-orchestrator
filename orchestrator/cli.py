import logging

import click
import yaml

import orchestrator.campaign as c
import orchestrator.tasks as t
from orchestrator.constants import TIMEOUT, PAUSE, NBR_CALLS, EXECUTOR, \
    LENGTH, ITERATION_PAUSE, CONF, BACKUP_DIR, NBR_CLIENTS, NBR_SERVERS, \
    CALL_TYPE, VERSION, NBR_TOPICS, DRIVER_NAME

logging.basicConfig(level=logging.DEBUG)


def load_config(file_path):
    """
    Read configuration from a file in YAML format.
    :param file_path: Path of the configuration file.
    :return:
    """
    with open(file_path) as f:
        configuration = yaml.safe_load(f)
    return configuration


@click.group()
def cli():
    pass


@cli.command(help="Claim resources from a PROVIDER and configure them.")
@click.argument("provider")
@click.option("--driver",
              default=DRIVER_NAME,
              help="communication bus driver")
@click.option("--constraints",
              help="network constraints")
@click.option("--force",
              is_flag=True,
              help="force redeployment")
@click.option("--conf",
              default=CONF,
              help="alternative configuration file")
@click.option("--env",
              help="alternative environment directory")
def deploy(provider, driver, constraints, force, conf, env):
    config = load_config(conf)
    t.PROVIDERS[provider](force=force, config=config, env=env)
    t.inventory()
    if constraints:
        t.emulate(constraints=constraints, env=env)

    t.prepare(driver=driver, env=env)


@cli.command(help="Claim resources on Grid'5000 (frontend).")
@click.option("--constraints",
              help="network constraints")
@click.option("--force",
              is_flag=True,
              help="force redeployment")
@click.option("--conf",
              default=CONF,
              help="alternative configuration file")
@click.option("--env",
              help="alternative environment directory")
def g5k(constraints, force, conf, env):
    config = load_config(conf)
    t.g5k(force=force, config=config, env=env)
    if constraints:
        t.inventory()
        t.emulate(constraints=constraints, env=env)


@cli.command(help="Claim resources on vagrant (localhost).")
@click.option("--constraints",
              help="network constraints")
@click.option("--force",
              is_flag=True,
              help="force redeployment")
@click.option("--conf",
              default=CONF,
              help="alternative configuration file")
@click.option("--env",
              help="alternative environment directory")
def vagrant(constraints, force, conf, env):
    config = load_config(conf)
    t.vagrant(force=force, config=config, env=env)
    if constraints:
        t.inventory()
        t.emulate(constraints=constraints, env=env)


@cli.command(help="Use static ressoures")
@click.option("--constraints",
              help="network constraints")
@click.option("--force",
              is_flag=True,
              help="force redeployment")
@click.option("--conf",
              default=CONF,
              help="alternative configuration file")
@click.option("--env",
              help="alternative environment directory")
def static(constraints, force, conf, env):
    config = load_config(conf)
    t.static(force=force, config=config, env=env)
    if constraints:
        t.inventory()
        t.emulate(constraints=constraints, env=env)


@cli.command(help="Generate the Ansible inventory [after g5k or vagrant].")
@click.option("--env",
              help="alternative environment directory")
def inventory(env):
    t.inventory(env=env)


# TODO declare in the doc that driver and TC are configured on the yaml file
@cli.command(help="Configure available resources [after deploy, inventory or destroy].")
@click.option("--driver",
              default=DRIVER_NAME,
              help="communication bus driver")
@click.option("--env",
              help="alternative environment directory")
def prepare(driver, env):
    t.prepare(driver=driver, env=env)


@cli.command(help="Destroy all the running containers (keeping deployed resources).")
@click.option("--env",
              help="alternative environment directory")
def destroy(env):
    t.destroy(env=env)


@cli.command(help="Set network configuration constraints [after deploy, inventory or destroy]")
@click.option("--constraints",
              help="network constraints")
@click.option("--validate",
              is_flag=True,
              help="validate constraints")
@click.option("--reset",
              is_flag=True,
              help="reset constraints")
@click.option("--env",
              help="alternative environment directory")
def traffic(constraints, validate, reset, env):
    if constraints:
        t.emulate(constraints=constraints, env=env)

    elif validate:
        t.validate(env=env)

    elif reset:
        t.reset(env=env)


@cli.command("backup", help="Backup environment logs [after test_case_*].")
@click.option("--backup",
              default=BACKUP_DIR,
              help="alternative backup directory")
@click.option("--env",
              help="alternative environment directory")
def perform_backup(backup, env):
    t.backup(backup_dir=backup, env=env)


@cli.command(help="Run the test case 1: one single large (distributed) target.")
@click.option("--nbr_clients",
              default=NBR_CLIENTS,
              help="number of clients")
@click.option("--nbr_servers",
              default=NBR_SERVERS,
              help="number of servers")
@click.option("--call_type",
              default=CALL_TYPE,
              type=click.Choice(["rpc-call", "rpc-cast", "rpc-fanout"]),
              help="call type (client): rpc_call (blocking), rpc_cast (non-blocking), or rpc-fanout (broadcast)")
@click.option("--nbr_calls",
              default=NBR_CALLS,
              help="number of execution calls (client)")
@click.option("--pause",
              default=PAUSE,
              help="pause between calls in seconds (client)")
@click.option("--timeout",
              default=TIMEOUT,
              help="max allowed time for benchmark in second (controller)")
@click.option("--length",
              default=LENGTH,
              help="size of payload in bytes")
@click.option("--executor",
              default=EXECUTOR,
              type=click.Choice(["eventlet", "threading"]),
              help="executor type (server): evenlet or threading")
@click.option("--version",
              default=VERSION,
              help="ombt version as a docker tag")
@click.option("--env",
              default=None,
              help="alternative environment directory")
def test_case_1(nbr_clients, nbr_servers, call_type, nbr_calls,
                pause, timeout, length, executor, version, env):
    t.test_case_1(nbr_clients=nbr_clients,
                  nbr_servers=nbr_servers,
                  call_type=call_type,
                  nbr_calls=nbr_calls,
                  pause=pause,
                  timeout=timeout,
                  length=length,
                  executor=executor,
                  version=version,
                  env=env)


@cli.command(help="Run the test case 2: multiple distributed targets.")
@click.option("--nbr_topics",
              default=NBR_TOPICS,
              help="number of topics")
@click.option("--call_type",
              default=CALL_TYPE,
              type=click.Choice(["rpc-call", "rpc-cast", "rpc-fanout"]),
              help="call type (client): rpc_call (blocking), rpc_cast (non-blocking), or rpc-fanout (broadcast)")
@click.option("--nbr_calls",
              default=NBR_CALLS,
              help="number of execution calls (client)")
@click.option("--pause",
              default=PAUSE,
              help="pause between calls in seconds (client)")
@click.option("--timeout",
              default=TIMEOUT,
              help="max allowed time for benchmark in second (controller)")
@click.option("--length",
              default=LENGTH,
              help="size of payload in bytes")
@click.option("--executor",
              default=EXECUTOR,
              type=click.Choice(["eventlet", "threading"]),
              help="executor type (server): evenlet or threading")
@click.option("--version",
              default=VERSION,
              help="ombt version as a docker tag")
@click.option("--env",
              default=None,
              help="alternative environment directory")
def test_case_2(nbr_topics, call_type, nbr_calls, pause,
                timeout, length, executor, version, env):
    t.test_case_2(nbr_topics=nbr_topics,
                  call_type=call_type,
                  nbr_calls=nbr_calls,
                  pause=pause,
                  timeout=timeout,
                  length=length,
                  executor=executor,
                  version=version,
                  env=env)


@cli.command(help="Run the test case 3: one single large distributed fanout.")
@click.option("--nbr_clients",
              default=NBR_CLIENTS,
              help="number of clients")
@click.option("--nbr_servers",
              default=NBR_SERVERS,
              help="Number of servers that will be deployed")
@click.option("--nbr_calls",
              default=NBR_CALLS,
              help="Number of calls/cast to execute [client]")
@click.option("--pause",
              default=PAUSE,
              help="pause between calls in seconds (client)")
@click.option("--timeout",
              default=TIMEOUT,
              help="max allowed time for benchmark in seconds (controller)")
@click.option("--length",
              default=LENGTH,
              help="size of payload in bytes")
@click.option("--executor",
              default=EXECUTOR,
              type=click.Choice(["eventlet", "threading"]),
              help="executor type (server): evenlet or threading")
@click.option("--version",
              default=VERSION,
              help="ombt version as a docker tag")
@click.option("--env",
              default=None,
              help="alternative environment directory")
def test_case_3(nbr_clients, nbr_servers, nbr_calls, pause,
                timeout, length, executor, version, env):
    t.test_case_3(nbr_clients=nbr_clients,
                  nbr_servers=nbr_servers,
                  nbr_calls=nbr_calls,
                  pause=pause,
                  timeout=timeout,
                  length=length,
                  executor=executor,
                  version=version,
                  env=env)


@cli.command(help="Run the test case 4: multiple distributed fanouts")
@click.option("--nbr_clients",
              default=NBR_CLIENTS,
              help="number of clients per topic")
@click.option("--nbr_servers",
              default=NBR_SERVERS,
              help="number of servers per topic")
@click.option("--nbr_topics",
              default=NBR_TOPICS,
              help="number of topics")
@click.option("--nbr_calls",
              default=NBR_CALLS,
              help="number of execution calls (client)")
@click.option("--pause",
              default=PAUSE,
              help="pause between calls in seconds (client)")
@click.option("--timeout",
              default=TIMEOUT,
              help="max allowed time for benchmark in seconds (controller)")
@click.option("--length",
              default=LENGTH,
              help="size of payload in bytes")
@click.option("--executor",
              default=EXECUTOR,
              type=click.Choice(["eventlet", "threading"]),
              help="executor type (server): evenlet or threading")
@click.option("--version",
              default=VERSION,
              help="ombt version as a docker tag")
@click.option("--env",
              default=None,
              help="alternative environment directory")
def test_case_4(nbr_clients, nbr_servers, nbr_topics, nbr_calls,
                pause, timeout, length, executor, version, env):
    t.test_case_4(nbr_clients=nbr_clients,
                  nbr_servers=nbr_servers,
                  nbr_topics=nbr_topics,
                  nbr_calls=nbr_calls,
                  pause=pause,
                  timeout=timeout,
                  length=length,
                  executor=executor,
                  version=version,
                  env=env)


@cli.command(help="Perform a TEST according to the (swept) parameters described in configuration.")
@click.argument("test")
@click.option("--provider",
              default="vagrant",
              help="target deployment infrastructure")
@click.option("--incremental",
              is_flag=True,
              help="reuse of resources in next iteration")
@click.option("--pause",
              default=ITERATION_PAUSE,
              help="break between iterations in seconds (only incremental)")
@click.option("--unfiltered",
              is_flag=True,
              help="Sweep configuration values without filter")
@click.option("--force",
              is_flag=True,
              help="force initial redeployment")
@click.option("--conf",
              default=CONF,
              help="alternative configuration file")
@click.option("--env",
              default=None,
              help="alternative environment directory")
def campaign(test, provider, incremental, pause, unfiltered, force, conf, env):
    config = load_config(conf)
    if incremental:
        c.incremental_campaign(test=test,
                               provider=provider,
                               pause=pause,
                               unfiltered=unfiltered,
                               force=force,
                               config=config,
                               env=env)

    else:
        c.campaign(test=test,
                   provider=provider,
                   unfiltered=unfiltered,
                   force=force,
                   config=config,
                   env=env)

@cli.command(help="List a curated version of the environment")
@click.option("--env",
              default=None,
              help="alternative environment directory")
def info(env):
    t.info(env=env)
