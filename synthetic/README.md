# Message bus evaluation framework

## Context

https://review.openstack.org/#/c/491818

## Installation

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt

```

## Deploys everything

```
# on g5k
./cli.py deploy --provider=g5k qdr

# on vagrant
./cli.py deploy --provider=vagrant qdr
```

## Help

List available actions:

```
./cli.py
```
