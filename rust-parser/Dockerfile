FROM rust:1.86

WORKDIR /app
COPY . .
RUN cargo build --release
CMD ["./target/release/php-ast-parser", "/workspace/code"]
