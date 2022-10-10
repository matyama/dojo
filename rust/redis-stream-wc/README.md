# Redis Streams Word-Count Example

## Start Redis services
```console
docker-compose up -d
```

Redis structures:
 - `state` - map of `word:count` pairs
 - `version` - checkpoint version, incremented on client disconnect
 - `counter` (modifiable via `$STREAM_ID`) - stream to which clients
   post messages (JSON-serialized under key `msg`), consumed by counter

## Start counter
```console
make counter
```

Note: Counter always starts from the 0th offset in the stream, so it
might be necessary to manually `FLUSHDB` to reset Redis.

## Start multiple clients
```console
make REPLICAS=20 REPEATS=1000 client
```

Configuration:
 - `REPLICAS` - number of client processes (default: number of cores)
 - `REPEATS` - number of published messages (per client, default: 100)

Note: Client processes are executed in parallel with job limit equal to
`REPLICAS`.

