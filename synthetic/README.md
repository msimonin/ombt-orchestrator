# Message bus evaluation framework

## Context

https://review.openstack.org/#/c/491818

## Installation

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt

```

## Workflow to run a test case

Example:

```
./cli.py deploy --provider=vagrant rabbitmq
./cli.py test_case_1 --nbr_clients 10 --nbr_servers 2
./cli.py destroy
./cli.py deploy --provider=vagrant rabbitmq
./cli.py test_case_1 --nbr_clients 20 --nbr_servers 2
```

> It's possible to force an experimentation dir with `--env mydir`
> Note also that scripting from python is also possible using the function defined in `task.py`

## Help

List available actions:

```
./cli.py
```
