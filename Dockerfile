FROM ghcr.io/astral-sh/uv:alpine
RUN apk add --no-cache git gcc musl-dev
WORKDIR /botnet
ADD . .
CMD ["/bin/sh", "-c", "uv run botnet --verbosity=debug run /data/config.json >> /data/log.txt 2>&1"]