* Build the qdrouterd image:

```
$) docker build -t msimonin/qdrouterd:0.8.0 -f Dockerfile-qdrouterd-0.8.0 .
```

* Build the qdrouterd with collectd:
```
$) docker build -t msimonin/qdrouterd-collectd:0.8.0 -f Dockerfile-qdrouterd-collectd-0.8.0 .
```


## Local tests

* Enable log to stdout in collectd conf (plugin logfile)
* Create the plugin file under /etc/collectd/collectd.conf.d/qdrouterd.conf
