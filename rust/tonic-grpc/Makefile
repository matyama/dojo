.PHONY: client server test-server

BASE_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

client:
	@echo "Sending client message"
	@cargo run --bin helloworld-client

server:
	@echo "Starting server"
	@cargo run --bin helloworld-server

test-server:
	@grpcurl \
		-plaintext \
		-import-path $(BASE_DIR)/proto \
		-proto helloworld.proto \
		-d '{"name": "Tonic"}' \
		'[::]:50051' \
		helloworld.Greeter/SayHello \
	| jq -r '.message'

