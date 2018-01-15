* Build the qdrouterd image:

```
$) docker build -t msimonin/qdrouterd:0.8.0 -f Dockerfile-qdrouterd .
```

* Build the qdrouterd with collectd:
```
$) docker build -t msimonin/qdrouterd-collectd:0.8.0 -f Dockerfile-qdrouterd-collectd .
```
