# Message bus evaluation framework

## Context

EnOSlib is a framework to benchmark the communication middleware supported by [oslo.messaging](https://docs.openstack.org/oslo.messaging/latest/). It's primary goal is to address the evaluation of https://docs.openstack.org/performance-docs/latest/test_plans/massively_distribute_rpc/plan.html.

It is build on top of: 

- [EnOSlib](https://github.com/beyondtheclouds/enoslib). This library helps to describe the experimental workflow and enforce it : from the deployment to the performance metrics analysis.
- [ombt](https://github.com/kgiusti/ombt). This will coordinate the benchmark once all the agents are up and running.

From a high level point of view the framework is able to deploy

* a communication bus (e.g RabbitMQ, qdr aka qpid-dispatch-router), 
* a set of client/server that will communicate
* start a benchmark while gathering metrics


A typical test consists in the following components:

```
Client 1---------+      +----------------------+     +-----> Server 1
                 |      |                      |     |
                 +----> |  Communication       | ----+-----> Server 2
Client 2--------------> |  Middleware          |     |
                 +----> |  (e.g qdr, rabbitms) |     |
...              |      |                      |     |
                 |      +----------------------+     +------> Server n
Client n---------+              |                             /
  \                                                         /
    \                           |                         / 
      \  --  --  --  --  -- Monitoring --  --  --  --  --
```

## Installation

* Clone the repository: 

```
git clone https://github.com/msimonin/qpid-dispatch-xp
cd qpid-dispatch-xp/synthetic
```

* Install the dependencies

```
virtualenv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

> On Grid'5000 you can launch this command from any frontend.

## Configuration

All the confs are currently under the `confs` folder.

## Command line interface

```
$)./cli.py
Usage: cli.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  backup       Backup the environment
  deploy       Claim resources from a provider and configure...
  destroy      Destroy all the running dockers (not...
  g5k          Claim resources on Grid'5000 (from a...
  inventory    Generate the Ansible inventory file.
  prepare      Configure the resources.[after g5k,vagrant...
  test_case_1  Runs the test case 1 : one single large...
  vagrant      Claim resources on vagrant (local machine)
```

## Workflow to run a test case


* Deploying and launching the benchmark.


```
# confs/vagrant-rabbitmq.yaml will be read
./cli.py deploy --provider=vagrant rabbitmq

# Launch the one benchmark
./cli.py test_case_1 --nbr_clients 10 --nbr_servers 2
```

> Adapt to the relevant provider (e.g `g5k`)

* Real-time metrics visualisation

Grafana is available on the port 3000 of the control node (check the inventory file).

* Backuping the environment

```
./cli.py backup
```

> The files retrieved by this action are located in `current/backup` dir by default.

* Some cleaning and preparation for the next run

```
# Preparing the next run by cleaning the environment
./cli.py destroy
./cli.py deploy --provider=vagrant rabbitmq

# Next run
./cli.py test_case_1 --nbr_clients 20 --nbr_servers 2
```

> It's possible to force an experimentation dir with `--env mydir`

> Note also that scripting from python is also possible using the function defined in `task.py`
