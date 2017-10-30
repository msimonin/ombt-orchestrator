import click
import logging
import tasks as t

logging.basicConfig(level=logging.DEBUG)

## cli part
@click.group()
def cli():
    pass


@cli.command()
@click.argument('broker')
@click.option("--provider",
    default="vagrant",
    help="Deploy with the given provider")
@click.option("--force",
    is_flag=True)
def deploy(broker, provider, force):
    providers = {
        "g5k": t.g5k,
        "vagrant": t.vagrant
    }
    brokers = {
        "qpidd": t.qpidd,
        "rabbitmq": t.rabbitmq
    }
    p = providers[provider]
    b = brokers[broker]
    if not b:
        raise Exception("Broker not found, should be [qpidd|rabbitmq]")
    if not p:
        raise Exception("Provider not supported, should be [g5k|vagrant]")
    p(broker=broker, force=force)
    t.inventory()
    t.prepare()
    b()


@cli.command()
@click.option("--force", is_flag=True, help="force redeploy")
def g5k(force):
    t.g5k(force)


@cli.command()
@click.option("--force",is_flag=True, help="force redeploy")
def vagrant(force):
    t.vagrant(force)


@cli.command()
def inventory():
    t.inventory()


@cli.command()
def prepare():
    t.prepare()

@cli.command()
def qpidd():
    t.qpidd()

@cli.command()
def rabbitmq():
    t.rabbitmq()

@cli.command()
def test_case_1():
    t.test_case_1()

@cli.command()
def destroy():
    t.destroy()


if __name__ == "__main__":
    cli()
