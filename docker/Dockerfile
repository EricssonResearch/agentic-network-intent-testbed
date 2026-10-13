# 6G intent-execution testbed -- headless experiment image (revision campaign)
# Build from the repository root:  docker/build.sh   (stages engine + map into docker/assets first)
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-numpy python3-scipy ca-certificates curl tini \
    && rm -rf /var/lib/apt/lists/*
# Engine (statically linked spring-headless + base content) and the map
COPY docker/assets/engine /opt/recoil
COPY docker/assets/maps   /opt/bar/base/maps
COPY docker/assets/springsettings.cfg /opt/bar/base/springsettings.cfg
# Game content = this repository (see .dockerignore for what is excluded)
COPY . /opt/bar/base/games/bar.sdd
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /opt/bar/base/games/bar.sdd/agent/run_episode.sh \
    && mkdir -p /data /results
ENV BAR_WRITE_DIR=/opt/bar/base \
    BAR_ENGINE_DIR=/opt/recoil \
    RESULTS_DIR=/results \
    BAR_COMMIT=unknown
VOLUME ["/results"]
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["--help"]
