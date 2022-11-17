ARG RUST_TAG=1.65-slim
FROM rust:${RUST_TAG} AS chef 
RUN apt-get update -qq && rm -rf /var/lib/apt/lists/*
RUN cargo install cargo-chef 
WORKDIR app

FROM chef AS planner
COPY . .
RUN cargo chef prepare  --recipe-path recipe.json

FROM chef AS builder
COPY --from=planner /app/recipe.json recipe.json
# Build and cache dependencies
RUN cargo chef cook --release --recipe-path recipe.json
# Build application
COPY . .
RUN cargo build --release --bins

# Build runtime image without the Rust toolchain and additional dependencies
FROM debian:buster-slim AS runtime
ENV RUST_LOG INFO
ENV REDIS__URL redis://redis:6379
ENV SERVER_PORT 3000
WORKDIR app
COPY --from=builder /app/target/release/server /usr/local/bin/
CMD server
