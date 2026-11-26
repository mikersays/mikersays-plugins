# shared-browser

Run one persistent Chrome that you and your agent share. You view and drive it
through noVNC in your own browser, or on your own screen. The agent drives it
over the Chrome DevTools Protocol (CDP) through the
[Playwright MCP server](https://github.com/microsoft/playwright-mcp).

## Install

In Claude Code:

```
/plugin install shared-browser --marketplace mikersays/mikersays-plugins
```

Then run the skill:

```
/shared-browser
```

## Why

Google and some other sites refuse to sign in on a browser that Playwright
launches ("This browser or app may not be secure"), because Playwright adds
automation flags. This plugin runs an ordinary Chrome with no automation flags
and a profile of its own. You sign in by hand, and the agent attaches over CDP
and reuses your session. The profile persists, so logins survive restarts.

## Modes

| Mode | Runs on | What it runs | Starts at boot | You see it through |
|---|---|---|---|---|
| `systemd` | Linux with a systemd user session | Xvnc, Openbox, websockify with noVNC, and Chrome as four user units under one target | Yes, with linger | noVNC |
| `container` | Any host with Docker or Podman: Linux, or macOS with Docker Desktop, colima, or OrbStack | The same stack in one container; the profile on a named volume | Yes (`--restart unless-stopped`) | noVNC |
| `direct` | A Mac or Linux desktop | Your installed Chrome with a separate profile and CDP; a launchd agent on macOS | macOS: at login | Your screen, or macOS Screen Sharing |

Each mode works on the machine you sit at or on a remote host over SSH:
`shared-browser up --host user@host` copies the CLI to the host and runs it
there.

### macOS

- `container` gives the full noVNC setup and works on a headless Mac that you
  reach over SSH. On Apple silicon the image uses Chromium, because Google
  publishes no Linux arm64 build of Chrome. Google may refuse to sign in on
  Chromium.
- `direct` runs your installed Google Chrome as a launchd agent, so Google
  sign-in works. It needs a logged-in desktop session. To see it from another
  machine, turn on Screen Sharing and tunnel port 5900.
- The CLI runs on the stock `/bin/bash` 3.2.

## Requirements

- **All modes:** `curl`; Node.js 18+ (`npx`) for the MCP server.
- **`systemd`:** TigerVNC (`Xvnc`, `vncpasswd`), Openbox, websockify, noVNC, and
  Chrome or Chromium. On Debian and Ubuntu:
  `sudo apt-get install -y tigervnc-standalone-server tigervnc-tools openbox novnc websockify curl`,
  plus Chrome from google.com. `shared-browser doctor` prints the command for
  dnf, pacman, and zypper.
- **`container`:** Docker or Podman. The first `up` builds the image locally
  from `container/Dockerfile` (Debian 13), with BuildKit or the legacy builder.
  If your user cannot reach the Docker daemon, set
  `SHARED_BROWSER_DOCKER='sudo docker'` or `SHARED_BROWSER_DOCKER=podman`.
- **`direct`:** Google Chrome or Chromium.

## Quick start

On the machine that should run the browser (or add `--host user@host`):

```bash
shared-browser doctor          # which modes work here
shared-browser up              # picks a mode; or pass --mode systemd|container|direct
shared-browser password        # the VNC password
shared-browser mcp             # registers the "chrome" MCP server
```

From another machine:

```bash
shared-browser tunnel --host user@host
# then open http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

The skill finds the CLI at `scripts/shared-browser` in the installed plugin.
Run `shared-browser help` for every command and option. Use `--name` to run
more than one instance, with its own ports.

## Ports

| Port | Purpose | Binds to |
|---|---|---|
| 6080 | noVNC web viewer (`--web-port`) | 127.0.0.1 |
| 9222 | CDP (`--cdp-port`) | 127.0.0.1 |
| 5999 | Raw VNC, `systemd` mode only (`--vnc-port`) | 127.0.0.1 |

## Security

- **CDP has no authentication.** Anyone who can connect to the CDP port
  controls the browser and every account signed in to it. Every port binds to
  127.0.0.1, so from another machine SSH is the only way in. Other accounts on
  the same host can still reach 127.0.0.1, so run this only on a host whose
  local users you trust. Never publish the ports on a LAN, a VPN, or the
  internet.
- **The container runs on a Docker network of its own**, so other containers
  cannot reach its CDP port.
- **The container runs Chrome with `--no-sandbox`.** Docker's default seccomp
  profile blocks the namespaces that Chrome's sandbox needs. The container is
  the isolation boundary instead: it runs as an unprivileged user with no
  added capabilities.
- **The VNC password** is 8 random characters (VNC ignores anything longer).
  The password is stored with mode 600 in `~/.config/shared-browser/<name>/`
  (systemd) or in the container volume. noVNC traffic is not encrypted, so
  carry that traffic over SSH.
- **The X display** on Linux accepts any local user, the same trust boundary
  as CDP.

## Files

| Path | What |
|---|---|
| `~/.config/shared-browser/<name>/` | Instance settings and the VNC password |
| `~/.local/share/shared-browser/<name>/profile/` | Chrome profile (`systemd`, `direct`) |
| `~/.config/systemd/user/<name>*.service`, `<name>.target` | `systemd` units |
| `~/Library/LaunchAgents/dev.shared-browser.<name>.plist` | `direct` mode launchd agent (macOS) |
| Volume `<name>-data`, network `<name>-net`, image `shared-browser:<version>` | `container` mode |

`uninstall` removes the units, agent, or container and keeps the profile.
`uninstall --purge` also deletes the profile, the password, the volume, and
the image.

## Tested

Version 1.0.0 passed these checks on Ubuntu (x86_64, Chrome 158) and on macOS
26 (arm64, colima, Chromium 156):

- `systemd`: a CDP client and `@playwright/mcp` loaded a page and read its
  title, with `navigator.webdriver` false. A browser killed with SIGKILL came
  back. A Chrome left running on the profile outside the unit was cleared
  without a restart loop. `down` left no browser process.
- `container`, both architectures: the same CDP and MCP checks, and a noVNC
  login with the generated password showed the page that the agent had
  opened. On the remote Mac, every check ran through the SSH tunnel.
- `direct` on macOS: launchd restarted Chrome after a SIGKILL.
- From another machine on the LAN, the noVNC, CDP, and VNC ports were all
  closed.
