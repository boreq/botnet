FROM ghcr.io/astral-sh/uv:latest
WORKDIR /botnet
ADD . .
CMD ["/bin/sh", "-c", "uv run botnet --verbosity=debug run /data/config.json >> /data/log.txt 2>&1"]