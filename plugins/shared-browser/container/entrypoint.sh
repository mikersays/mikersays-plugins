#!/usr/bin/env bash
# Start the display, window manager, noVNC, and the browser, then supervise
# them. If the display, Openbox, or noVNC exits, the container exits and the
# restart policy starts it again. The browser restarts on its own, so closing
# its window in noVNC does not stop the container.
#
# Inside the container:
#   Xvnc        :1, VNC on 127.0.0.1:5900 (not published)
#   websockify  0.0.0.0:6080 -> 127.0.0.1:5900, serving noVNC
#   browser     CDP on 127.0.0.1:9223
#   socat       0.0.0.0:9222 -> 127.0.0.1:9223, because Chrome binds CDP to
#               loopback only and a published port needs 0.0.0.0
set -euo pipefail

DISPLAY_NUM=1
export DISPLAY=":$DISPLAY_NUM"
PROFILE=/data/profile
GEOMETRY="${GEOMETRY:-1600x1000}"

mkdir -p "$PROFILE"
sb-password --init

# Each container start may get a new hostname, and Chrome refuses a profile
# that another host has locked. This container is the only user of the
# profile, so the old locks are stale.
rm -f "$PROFILE"/SingletonLock "$PROFILE"/SingletonSocket "$PROFILE"/SingletonCookie
rm -f "/tmp/.X$DISPLAY_NUM-lock" "/tmp/.X11-unix/X$DISPLAY_NUM"

Xvnc "$DISPLAY" -geometry "$GEOMETRY" -depth 24 -localhost=1 -nolisten tcp \
  -rfbport 5900 -SecurityTypes VncAuth -PasswordFile /data/vncpasswd \
  -AlwaysShared -AcceptSetDesktopSize=1 &

for _ in $(seq 1 100); do
  [ -S "/tmp/.X11-unix/X$DISPLAY_NUM" ] && break
  sleep 0.1
done
[ -S "/tmp/.X11-unix/X$DISPLAY_NUM" ] || { echo "Xvnc did not start" >&2; exit 1; }

openbox &
websockify --web /usr/share/novnc 0.0.0.0:6080 127.0.0.1:5900 &
socat TCP-LISTEN:9222,fork,reuseaddr,bind=0.0.0.0 TCP:127.0.0.1:9223 &

# --no-sandbox: Docker's default seccomp and AppArmor profiles block the
# namespaces that Chrome's sandbox needs. The container is the isolation
# boundary instead.
(
  while true; do
    sb-browser --user-data-dir="$PROFILE" --remote-debugging-port=9223 \
      --no-first-run --no-default-browser-check --start-maximized \
      --password-store=basic --no-sandbox --disable-dev-shm-usage || true
    echo "browser exited; restarting in 2 s" >&2
    sleep 2
  done
) &

echo "shared-browser ready: noVNC :6080, CDP :9222 (published on the host's 127.0.0.1)"
wait -n
echo "a core process exited; stopping the container" >&2
exit 1
