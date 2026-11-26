---
type: Policy
title: shared-browser design decisions
description: Why the shared-browser plugin has three modes, binds only to 127.0.0.1, runs Chrome with --no-sandbox in the container, and registers its MCP server with a command instead of .mcp.json; read before changing plugins/shared-browser/.
tags: [shared-browser, chrome, novnc, cdp, docker, macos, security]
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-26T20:00:00Z }
status: draft
sources:
  - id: build-2026-11-26
    resource: ../plugins/shared-browser/README.md
    title: shared-browser 1.0.0 build and test session, 2026-11-26
---

# Decisions

* **Three modes, one CLI.** `systemd` runs on Linux servers. `container` runs on
  any host with Docker or Podman, including a headless Mac reached over SSH.
  `direct` runs on a desktop that the person sits at. `--host user@host`
  runs any of them on a remote host: it copies `scripts/` and `container/`
  to `~/.local/share/shared-browser/kit` there.[^build-2026-11-26]
* **The CLI is bash 3.2.** macOS ships `/bin/bash` 3.2, so the CLI uses no
  associative arrays, no `${var,,}`, and no `wait -n`. The container's
  `entrypoint.sh` runs on Debian's bash and may use them.
* **macOS keeps Google Chrome in `direct` mode.** Google publishes no Linux
  arm64 build of Chrome, so the container on Apple silicon uses Chromium, and
  Google may refuse to sign in on it. `direct` mode on macOS is a launchd
  agent (`dev.shared-browser.<name>`, `KeepAlive`, `LimitLoadToSessionType`
  Aqua) running the installed Chrome. The person views it through Screen
  Sharing.
* **Every port binds to 127.0.0.1.** CDP has no authentication. The container
  publishes with `-p 127.0.0.1:...` and runs on its own network
  `<name>-net`, so other containers cannot reach CDP. Inside the container,
  Chrome binds CDP to loopback port 9223, and `socat` forwards 0.0.0.0:9222
  to it, because a published port needs a non-loopback listener.
* **The container uses `--no-sandbox`.** Under Docker's default seccomp
  profile, Chrome's sandbox exits with "failed to move to new namespaces".
  The sandbox works with `--security-opt seccomp=unconfined`, but that weakens the
  container for every process. The container runs as UID 1000 with no added
  capabilities and is the isolation boundary.
* **The Dockerfile works with the legacy builder.** colima's Docker had no
  BuildKit, so the Dockerfile uses `RUN chmod` instead of `COPY --chmod`, and
  reads the architecture from `dpkg --print-architecture`, not `TARGETARCH`.
* **The orphan-relaunch fix.** After an update, Chrome can relaunch outside
  its unit's cgroup, and the unit then loops and opens blank tabs. The
  `chrome` unit runs `pkill -U %U -f -- --user-data-dir=<profile>` in
  `ExecStartPre` and sets `StartLimitBurst=10` and `StartLimitIntervalSec=120`.
  The macOS wrapper `run-browser.sh` does the same kill. The wrapper's own argv
  omits the profile path, so pkill spares it. A running Chrome 158 always moves its
  main process to `app-com.google.Chrome-<pid>.scope`. This move is normal, and
  systemd still tracks `MainPID`.
* **The MCP server is registered by a command, not `.mcp.json`.** A plugin
  `.mcp.json` would add a server for every user, even one with no browser
  running, and would clash with an existing `chrome` server. `shared-browser
  mcp` runs `claude mcp add --scope user` and `codex mcp add`, and leaves an
  existing server of the same name alone.
* **No published image.** `up` builds `shared-browser:<version>` locally, so
  the plugin has no registry to maintain and nothing to trust beyond Debian
  and Google's `.deb`.

[^build-2026-11-26]: shared-browser 1.0.0 build and test session, 2026-11-26
