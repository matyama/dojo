# ZeroMQ fan-in example
This example shows a simple *fan-in* architecture using
[ZeroMQ](https://zeromq.org/) with *n* producers `PUSH`ing messages to
single `PULL`ing sink.

## Dependencies
Notably, this example is based on the [TMQ](https://crates.io/crates/tmq)
library. That is, it's based on
 - [`tokio`](https://github.com/tokio-rs/tokio)
 - [`zmq`](https://crates.io/crates/zmq)

The outputs are displayed using
[`pretty_env_logger`](https://crates.io/crates/pretty_env_logger).

## Build
```bash
cargo build --features="vendored-zmq"
```

Note that `--features="vendored-zmq"` can be omitted if `libzmq3-dev` is
installed, see [here](https://github.com/erickt/rust-zmq#installation).

## Run the example
First, make sure environment is set up:
```bash
direnv allow .
```
This sources env vars from the local `.envrc` file.

Start the collector:
```bash
cargo run --bin sink --features="vendored-zmq"
```

Start some producers, each identified by some 'producer ID' (here `P1`
and `P2`):
```bash
cargo run --bin producer --features="vendored-zmq" P1
cargo run --bin producer --features="vendored-zmq" P2
```

## Docker Swarm

### Setup
Setup docker swarm with registry using `make`. This does roughly the
following:
```bash
# Initialize swarm mode
docker swarm init

# Create local registry service
docker service create \
	--name registry \
	--publish published=5000,target=5000 \
	registry:2
```

### Build & deploy
Once set up an in swarm mode, one can deploy services via `make install`:
```bash
# Build Docker images
docker-compose build

# Push images to the local registry
docker-compose push

# Deploy everything to the swarm
docker stack deploy -c docker-compose.yml zmq-fan-in
```

### Inspect & scale
There are some handy commands to interact with the swarm:
 - `docker service ls` lists services, displays replicas
 - `docker service scale zmq-fan-in_producer=10` will scale the number
	 of producers to 10
 - `docker service logs -f zmq-fan-in_sink` will attack and follow logs
	 of the sink service

### Shutdown services
Finally, terminate and cleanup using `make clean`:
```bash
# Shutdown services
docker stack rm zmq-fan-in
docker service rm registry

# Leave swarm mode
docker swarm leave --force
```
