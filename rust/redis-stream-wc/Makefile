.PHONY: client counter

client: REPLICAS := $(shell nproc --all)
client: REPEATS := 100
client:
	@seq 1 $(REPLICAS) | \
		xargs parallel -i -j $(REPLICAS) \
		env REPEATS=$(REPEATS) cargo run -q --release --bin $@ --

counter:
	@cargo run -q --release --bin $@

