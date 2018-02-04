VERSION=1.0.0
FLAGS=--no-cache
FLAGS=

all: $(VERSION)-qdr $(VERSION)-qdrc $(VERSION)-qdrg

%-qdr:
	cd ${@:-qdr=} && docker build $(FLAGS) -t msimonin/qdrouterd:${@:-qdr=} -f Dockerfile-qdrouterd .

%-qdrc:
	cd ${@:-qdrc=} && docker build $(FLAGS) -t msimonin/qdrouterd-collectd:${@:-qdrc=} -f Dockerfile-qdrouterd-collectd ..

%-qdrg:
	cd ${@:-qdrg=} && docker build $(FLAGS) -t msimonin/qdrouterd-gui:${@:-qdrg=} -f Dockerfile-qdrouterd-gui .

ws:
	docker build -t msimonin/websockify -f Dockerfile-websockify

r: $(VERSION)-rqdr $(VERSION)-rqdrc $(VERSION)-rqdrg

%-rqdr:
	ref=$$(docker run -ti msimonin/qdrouterd:${@:-rqdr=} sh -c 'cd /opt/qpid-dispatch/ && git rev-parse --short HEAD' | tr '\r' ' ') &&\
			docker tag msimonin/qdrouterd:${@:-rqdr=} msimonin/qdrouterd:$$ref &&\
			docker push msimonin/qdrouterd:$$ref
	docker push msimonin/qdrouterd:${@:-rqdr=}

%-rqdrc:
	# In the following we have set an entrypoint
	ref=$$(docker run -ti --entrypoint=sh msimonin/qdrouterd-collectd:${@:-rqdrc=} -c 'cd /opt/qpid-dispatch/ && git rev-parse --short HEAD' | tr '\r' ' ') &&\
			docker tag msimonin/qdrouterd-collectd:${@:-rqdrc=} msimonin/qdrouterd-collectd:$$ref &&\
			docker push msimonin/qdrouterd-collectd:$$ref
	docker push msimonin/qdrouterd-collectd:${@:-rqdrc=}

%-rqdrg:
	ref=$$(docker run -ti msimonin/qdrouterd-gui:${@:-rqdrg=} sh -c 'cd /opt/qpid-dispatch/ && git rev-parse --short HEAD' | tr '\r' ' ') &&\
			docker tag msimonin/qdrouterd-gui:${@:-rqdrg=} msimonin/qdrouterd-gui:$$ref &&\
			docker push msimonin/qdrouterd-gui:$$ref
	docker push msimonin/qdrouterd-gui:${@:-rqdrg=}
