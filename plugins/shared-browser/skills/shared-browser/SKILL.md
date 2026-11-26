---
name: shared-browser
description: Set up, start, check, or remove a persistent Chrome that a person views and drives through noVNC (or on their own screen) while the agent drives it over the Chrome DevTools Protocol through a Playwright MCP server. Runs as systemd user units on Linux, as a Docker or Podman container on any host including macOS, or as a launchd-managed Chrome on a Mac desktop, on this machine or on a remote host over SSH. Trigger on "shared browser", "set up a browser we can both use", "noVNC browser", "a browser I can log in to for you", "Google says this browser is not secure", "browser on my server", or "CDP browser".
argument-hint: "[up|status|down|password|tunnel|uninstall] [--host user@host]"
allowed-tools: Bash, Read
---

# shared-browser: a Chrome that the person and the agent share

Sites such as Google refuse to sign in on a browser that Playwright launches,
because Playwright adds automation flags. This skill runs an ordinary Chrome
with no automation flags and a profile of its own. The person signs in by
hand, and the agent attaches over CDP and reuses the session. The profile
persists, so logins survive restarts.

## Locate the CLI

```bash
SB="${CLAUDE_PLUGIN_ROOT:-}/scripts/shared-browser"
[ -x "$SB" ] || SB="$(find ~/.claude/plugins ~/.codex/plugins -type f -path '*/shared-browser/scripts/shared-browser' -print -quit 2>/dev/null)"
[ -x "$SB" ] && echo "cli: $SB" || echo "shared-browser CLI not found"
```

If this prints "not found", report that the plugin is not installed where
expected, and stop. Run `"$SB" help` for every option.

## 1. Pick the mode and the host

Ask the person only what the context does not already answer:

- **Where does the browser run?** On this machine, or on a remote host that
  the person reaches over SSH (`--host user@host`)?
- **Can the person see that machine's screen?**

Then pick the mode from this table:

| Situation | Mode | The person sees the browser through |
|---|---|---|
| Linux server or VM, reached over SSH | `systemd` | noVNC in their own browser, through an SSH tunnel |
| macOS, or Linux without the packages, reached over SSH, with Docker, Podman, colima, or OrbStack | `container` | noVNC, through an SSH tunnel |
| Any laptop or desktop with Docker, where the browser should stay isolated | `container` | noVNC at `http://localhost:6080` |
| A Mac or Linux desktop that the person sits at | `direct` | an ordinary Chrome window on their screen |
| A Mac reached over SSH, logged in to its desktop, where Google sign-in matters | `direct` | macOS Screen Sharing, through an SSH tunnel |

Run `"$SB" doctor` (add `--host user@host` for a remote host) to see which
modes the machine supports. Without `--mode`, `up` picks one: `systemd` when
it can, then `container`, then `direct` on macOS.

Know these limits before you choose:

- **Google sign-in on arm64.** Google publishes no Linux arm64 build of
  Chrome, so the container uses Chromium on Apple silicon and other arm64
  hosts. Google may refuse to sign in on Chromium. If the person needs Google
  sign-in on a Mac, use `direct`.
- **The container runs Chrome with `--no-sandbox`.** Docker's default seccomp
  profile blocks the namespaces that Chrome's sandbox needs, and Chrome then
  exits with "failed to move to new namespaces". The container is the
  isolation boundary instead. Chrome shows an infobar about the flag.
- **`direct` mode on Linux** does not start at boot. On macOS it is a launchd
  agent that starts at login and restarts Chrome if it exits, but it needs a
  logged-in desktop session.

## 2. Start it

```bash
"$SB" up --mode <mode>                      # on this machine
"$SB" up --mode <mode> --host user@host     # on a remote host
```

- `systemd` mode lists any missing packages with the install command for the
  host's package manager. Ask before you run `sudo`.
- `container` mode builds the image on the first run, which takes a few
  minutes. If the container CLI cannot reach its daemon, the error says how to
  fix it (for example `colima start`, or `SHARED_BROWSER_DOCKER='sudo docker'`).
- If a port or display is in use, for example by another shared browser, pass
  `--name`, `--web-port`, `--cdp-port`, and, in systemd mode, `--vnc-port` and
  `--display`. Later commands for that instance need the same `--name`.

`up` waits for CDP, checks noVNC, and prints the URLs. It fails loudly if a
check does not pass. In that case, show the person the output of `"$SB" logs`.

## 3. Connect the person

- **Same machine:** open `http://localhost:6080/vnc.html?autoconnect=1&resize=remote`.
- **Remote host:** on the person's machine, run
  `shared-browser tunnel --host user@host` (or the `ssh -N -L ...` line that
  `up` prints), then open the same URL. VS Code Remote-SSH users can forward
  the port from the **Ports** panel instead.
- **VNC password:** `"$SB" password` prints it. Give it to the person in the
  conversation only if they ask, and never write it to a file in a
  repository. `"$SB" password --reset` makes a new one. Xvnc reads the new
  password on the next connection.
- **`direct` mode on a remote Mac:** the person turns on Screen Sharing, runs
  the `ssh -L 5901:127.0.0.1:5900` line that `up` prints, and opens
  `vnc://localhost:5901`.

## 4. Connect the agent

```bash
"$SB" mcp                   # registers MCP server "chrome" with Claude Code and Codex CLI
```

This runs `claude mcp add --scope user chrome -- npx -y @playwright/mcp@latest --cdp-endpoint http://127.0.0.1:<cdp-port>`
(and the Codex equivalent). It leaves an existing server of the same name
alone; pass `--mcp-name` to pick another name. The person must start a new
session to load the server.

If the browser runs on a remote host and the agent runs here, keep the tunnel
open: it forwards the CDP port too.

## 5. Use it safely

- **CDP has no authentication.** Anyone who can open a connection to the CDP
  port controls the browser and every account signed in to it. Every port
  binds to 127.0.0.1. The container publishes only on 127.0.0.1 and runs on a
  Docker network of its own. From another machine, SSH is the only way in.
  Any other account on the same host can still reach 127.0.0.1. Never
  publish these ports on a LAN, a VPN such as Tailscale, or the internet.
- **Never take an accessibility snapshot of a login page.** Snapshots include
  autofilled field values, and the MCP server writes them to disk. Read the
  page's visible text instead.
- **Never type a password that the person did not give you for that purpose.**
  The person signs in by hand in noVNC.

## 6. Operate

| Task | Command |
|---|---|
| Check every part, CDP, and noVNC | `"$SB" status` |
| Stop, keeping the profile and logins | `"$SB" down` |
| Restart | `"$SB" restart` |
| Recent logs | `"$SB" logs` |
| Change the screen size or ports (container) | `"$SB" up --geometry 1920x1080` (recreates the container; the profile volume stays) |
| Update the browser in the container | `"$SB" up --rebuild` |
| Remove, keeping the profile | `"$SB" uninstall` |
| Remove everything, including logins | `"$SB" uninstall --purge` (ask first) |

Add `--host user@host` and `--name NAME` to any of these as needed.

### Known failure: a systemd restart loop that opens blank tabs

After an update, Chrome can relaunch itself outside its systemd unit. The
unit then restarts every few seconds, and each start opens a blank tab in the
orphaned Chrome. The units this skill writes prevent this: before each
start, they kill any browser on the instance's profile, and they stop after 10
starts in 120 seconds. `status` warns when it finds an orphan. `restart`
fixes the orphan.

## Report

Tell the person the mode, the host, the noVNC URL, the CDP port, and the
tunnel command if one applies. Report the result of `status` as it printed,
including any check that failed.
