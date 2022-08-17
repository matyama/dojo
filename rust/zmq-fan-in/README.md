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

