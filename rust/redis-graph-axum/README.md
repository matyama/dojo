# D&D dungeon crawler

This crate contains a toy [*Axum*](https://github.com/tokio-rs/axum)
server for generating and crawling an imaginary D&D dungeon.

The server is backed by a
[*RedisGraph*](https://redis.io/docs/stack/graph/) database.

Both the idea and parts of implementation is based on
[this talk](https://youtu.be/HqwY_TyxeJw) on *RedisGraph*.


## Running the example
First start Redis services from docker compose
```console
docker-compose up -d
```

Then run the server using cargo:
```console
cargo run --bin server --release
```

### Environment
Note that there are few environment variables that control the server
(all with sensible defaults):
 - `SERVER_PORT` is the port the server will accept connections at
 - `REDIS__URL` is the URL of the Redis instance
 - `RUST_LOG` configures event tracing (logger)

All these are pre-configured in `.envrc` which can be set up with tools
such as `direnv`.

## Endpoints
For convenience, one can request server endpoints using `make`. Note
that it requires [`xh`](https://github.com/ducaale/xh) to be installed
(replicating it with either `HTTPie` or `curl` should be trivial).

### Healthcheck
The default `make` target pings the *health* endpoint of the server and
returns 

### Generate random dungeon
The `dungeon` endpoint clears the database and generates new (random)
graph. The graph structure can be influenced by few simple parameters
like the `SIZE` or treasure count.

Request with:
```console
make SIZE=14 MAXGP=50 TREASURES=4 dungeon
```

Note that the resulting graph will always be connected and corridors can
be traversed in both directions.

### Plan a path to the largest treasure
The `crawl` endpoint searches the graph (dungeon) for the largest
treasure and finds a path from the entrance room (`id=1`) to the max.
treasure room.

Request with:
```console
make crawl
```

## Known limitations
 - `crawl` endpoint returns raw path which is not parsed / interpreted
 - `crawl` does not compute total treasure value along the path
 - `crawl` always starts from node with `id=1`, there's not yet a notion
   of dungeon entrance (or a feature like start being a query param)
 - Connection pooling is not set up (due to issue with trait bounds on
   pooled vs driver connections)
 - Server is not dockerized

