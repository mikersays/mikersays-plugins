# shared-browser container: Xvnc + Openbox + noVNC + a browser with CDP.
#
# Build: docker build -t shared-browser:1.0.0 .
# Run:   use `shared-browser up --mode container`, which publishes the ports
#        on 127.0.0.1 only and keeps the profile on a named volume.
#
# BROWSER=auto installs Google Chrome on amd64 and Chromium elsewhere,
# because Google publishes no Linux arm64 build of Chrome. BROWSER=chromium
# forces Chromium on every architecture.
FROM debian:13-slim

ARG BROWSER=auto
ARG DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl tini socat procps tzdata \
      tigervnc-standalone-server tigervnc-tools openbox novnc websockify \
      fonts-liberation fonts-noto-core fonts-noto-color-emoji fonts-noto-cjk \
 && arch="$(dpkg --print-architecture)" \
 && if [ "$BROWSER" = auto ] && [ "$arch" = amd64 ]; then \
      curl -fsSL -o /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
      && apt-get install -y --no-install-recommends /tmp/chrome.deb \
      && rm /tmp/chrome.deb \
      && ln -s /usr/bin/google-chrome-stable /usr/local/bin/sb-browser; \
    else \
      apt-get install -y --no-install-recommends chromium \
      && ln -s /usr/bin/chromium /usr/local/bin/sb-browser; \
    fi \
 && rm -rf /var/lib/apt/lists/*

# COPY --chmod needs BuildKit; a separate chmod also works with the legacy
# builder (for example Docker under colima without buildx).
COPY entrypoint.sh sb-password /usr/local/bin/
RUN chmod 755 /usr/local/bin/entrypoint.sh /usr/local/bin/sb-password \
 && useradd --create-home --uid 1000 --shell /bin/bash browser \
 && mkdir /data && chown browser:browser /data

USER 1000:1000
ENV HOME=/home/browser GEOMETRY=1600x1000
WORKDIR /home/browser
VOLUME /data
EXPOSE 6080 9222

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD ["curl", "-fsS", "-o", "/dev/null", "http://127.0.0.1:9223/json/version"]

ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/entrypoint.sh"]
