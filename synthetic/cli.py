#!/usr/bin/env python
import click
import logging
import tasks as t

logging.basicConfig(level=logging.DEBUG)

## cli part
@click.group()
def cli():
    pass


@cli.command(help="Claim resources from a provider and configure them")
@click.argument('broker')
@click.option("--provider",
    default="vagrant",
    help="Deploy with the given provider")
@click.option("--force",
    is_flag=True)
@click.option("--env",
    help="Use this environment directory instead of the default one")
def deploy(broker, provider, force, env):
    providers = {
        "g5k": t.g5k,
        "vagrant": t.vagrant
    }
    p = providers[provider]

    p(broker=broker, force=force, env=env)
    t.inventory()
    t.prepare(broker=broker)


@cli.command(help="Claim resources on Grid'5000 (from a frontend)")
@click.option("--force", is_flag=True, help="force redeploy")
def g5k(force):
    t.g5k(force)


@cli.command(help="Claim resources on vagrant (local machine)")
@click.option("--force",is_flag=True, help="force redeploy")
def vagrant(force):
    t.vagrant(force)


@cli.command(help="Generate the Ansible inventory file. [after g5k,vagrant]")
def inventory():
    t.inventory()


@cli.command(help="Configure the resources.[after g5k,vagrant and inventory]")
def prepare():
    t.prepare()


@cli.command(help="""
    Runs the test case 1 : one single large (distributed) target.
    """)
@click.option("--nbr_clients",
    default=t.NBR_CLIENTS,
    help="Number of clients that will de deployed")
@click.option("--nbr_servers",
    default=t.NBR_SERVERS,
    help="Number of servers that will de deployed")
@click.option("--call_type",
    default=t.CALL_TYPE,
    type=click.Choice(["rpc-call", "rpc-cast", "rpc-fanout"]),
    help="Rpc_call (blocking) or rpc_cast (non blocking) [client] ")
@click.option("--nbr_calls",
    default=t.NBR_CALLS,
    help="Number of calls/cast to execute [client]")
@click.option("--pause",
    default=t.PAUSE,
    help="Pause in second between each call [client]")
@click.option("--timeout",
    default=t.TIMEOUT,
    help="Total time in second of the benchmark [controller]")
@click.option("--length",
    default=t.LENGTH,
    help="The size of the payload in bytes")
@click.option("--version",
    default=t.VERSION,
    help="Version of ombt to use as a docker tag (will use beyondtheclouds:'vesion')")
@click.option("--verbose",
    is_flag=True,
    help="Verbose mode will log every single message stat [client|server]")
def test_case_1(nbr_clients, nbr_servers, call_type, nbr_calls, pause, timeout, version, verbose, length):
    t.test_case_1(nbr_clients=nbr_clients,
                  nbr_servers=nbr_servers,
                  call_type=call_type,
                  nbr_calls=nbr_calls,
                  pause=pause,
                  timeout=timeout,
                  version=version,
                  verbose=verbose,
                  length=length)

@cli.command(help="Destroy all the running dockers (not destroying the resources)")
def destroy():
    t.destroy()

@cli.command(help="Backup the environment")
def backup():
    t.backup()


if __name__ == "__main__":
    cli()
