# TurtleBot4 Obstacle Avoidance (Fase 0 + Fase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `obstacle_avoidance.py`, a standalone script that reads LiDAR
scans from `lidar_server.py` (already running on the Pi, untouched) and
computes safe motion decisions using a sector-based reactive algorithm
(VFH-lite), starting in dry-run (print-only) mode before ever touching the
real robot.

**Architecture:** Pure, hardware-free functions (sectorization, blocked-sector
detection, heading choice, watchdog) covered by pytest, wired together at the
bottom of the file by a thin I/O loop that connects to the existing LiDAR TCP
socket — mirroring the connection pattern already used in `ver_lidar.py`. No
ROS2/ `rclpy` publishing happens until Task 8, and even then only behind an
explicit `--live` flag; default mode only prints decisions.

**Tech Stack:** Python 3, `pytest` for tests, standard library `socket`/`json`
for the LiDAR stream (same protocol as `ver_lidar.py`), `rclpy`/`geometry_msgs`
only in the final live-publish step.

**Reference spec:** `docs/superpowers/specs/2026-07-09-turtlebot4-sensor-fusion-design.md`, Fase 0 and Fase 1.

---

## Setup

- [ ] **Step 1: Confirm pytest is available (in WSL, where rclpy also lives)**

Run: `python3 -m pytest --version`
Expected: prints a pytest version. If missing: `pip install pytest`.

- [ ] **Step 2: Create the tests directory**

Run: `mkdir -p "C:\Users\mando\OneDrive\Desktop\turtleclaude4\tests"`

---

### Task 1: Fase 0 discovery — confirm Create3 topics (manual, blocking)

**Files:** none (this is a manual verification step, not code)

- [ ] **Step 1: With the Create3 powered on and the Pi reachable, run discovery commands inside WSL**

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list
ros2 topic info /odom
ros2 topic echo /odom --once
ros2 topic list | grep -i imu
```

- [ ] **Step 2: Record the results at the bottom of the spec file**

Open `docs/superpowers/specs/2026-07-09-turtlebot4-sensor-fusion-design.md`
and replace the "Pendiente de confirmar con el usuario más adelante" section
with the actual topic name/type for odometry (e.g. `/odom` —
`nav_msgs/msg/Odometry`) and whether IMU is available. This does not block
Task 2–7 below (those only need the LiDAR socket), but it blocks any future
Fase 3 (EKF) plan, so do not skip it.

- [ ] **Step 3: Commit the recorded discovery results**

```bash
git add docs/superpowers/specs/2026-07-09-turtlebot4-sensor-fusion-design.md
git commit -m "docs: record Fase 0 ROS2 topic discovery results"
```

(Skip this commit step if the project is still not a git repo — in that case just save the file.)

---

### Task 2: Parse LiDAR scan lines into points

**Files:**
- Create: `obstacle_avoidance.py`
- Test: `tests/test_obstacle_avoidance.py`

The LiDAR server (`lidar_server.py`, already running on the Pi, **do not
modify**) sends length-prefixed JSON: a 4-byte big-endian length header
followed by a JSON array of `[angle_deg, distance_mm]` pairs (see
`ver_lidar.py` for the existing consumer pattern — reused here, not copied
verbatim since this script has different needs).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_obstacle_avoidance.py
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from obstacle_avoidance import parse_scan_payload


def test_parse_scan_payload_returns_angle_distance_tuples():
    payload = json.dumps([[0.0, 1500.0], [90.0, 800.0], [180.0, 0.0]]).encode("utf-8")
    points = parse_scan_payload(payload)
    assert points == [(0.0, 1500.0), (90.0, 800.0), (180.0, 0.0)]


def test_parse_scan_payload_handles_empty_array():
    payload = json.dumps([]).encode("utf-8")
    assert parse_scan_payload(payload) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'obstacle_avoidance'`
(or `ImportError: cannot import name 'parse_scan_payload'` once the file exists but is empty).

- [ ] **Step 3: Write minimal implementation**

```python
"""
Evasion de obstaculos reactiva (Fase 1) para el TurtleBot4.

Lee escaneos del RPLidar A1M8 desde lidar_server.py (corriendo SIN CAMBIOS
en la Raspberry Pi, puerto 5001), calcula un histograma de sectores
angulares (VFH-lite) y decide una velocidad lineal/angular segura.

Por defecto corre en modo dry-run: solo imprime la decision, no publica a
ningun topico. Requiere pasar --live explicitamente para publicar de verdad
a /cmd_vel (ver Task 8).

No subir MAX_LINEAR / MAX_ANGULAR sin confirmacion explicita del usuario.
"""
import json
import socket
import struct


def parse_scan_payload(payload: bytes) -> list[tuple[float, float]]:
    raw = json.loads(payload.decode("utf-8"))
    return [(float(angle), float(distance)) for angle, distance in raw]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add obstacle_avoidance.py tests/test_obstacle_avoidance.py
git commit -m "feat: parse LiDAR scan payloads for obstacle avoidance"
```

---

### Task 3: Sector distance histogram

**Files:**
- Modify: `obstacle_avoidance.py`
- Test: `tests/test_obstacle_avoidance.py`

Divide the 360° circle into `num_sectors` equal-width sectors (default 36,
i.e. 10° each). For each sector, compute the minimum distance seen; a sector
with no readings gets `float("inf")` (treated as "unknown/free" downstream).
Zero-distance readings (invalid RPLidar samples) are discarded.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_obstacle_avoidance.py
from obstacle_avoidance import compute_sector_distances


def test_compute_sector_distances_bins_by_angle():
    points = [(5.0, 1000.0), (15.0, 2000.0), (355.0, 500.0)]
    distances = compute_sector_distances(points, num_sectors=36)
    assert len(distances) == 36
    assert distances[0] == 1000.0   # sector 0 covers [0,10) -> point at 5deg
    assert distances[1] == 2000.0   # sector 1 covers [10,20) -> point at 15deg
    assert distances[35] == 500.0   # sector 35 covers [350,360) -> point at 355deg


def test_compute_sector_distances_takes_minimum_per_sector():
    points = [(2.0, 900.0), (3.0, 300.0), (4.0, 1200.0)]
    distances = compute_sector_distances(points, num_sectors=36)
    assert distances[0] == 300.0


def test_compute_sector_distances_ignores_zero_readings():
    points = [(2.0, 0.0)]
    distances = compute_sector_distances(points, num_sectors=36)
    assert distances[0] == float("inf")


def test_compute_sector_distances_empty_sector_is_infinite():
    distances = compute_sector_distances([], num_sectors=36)
    assert all(d == float("inf") for d in distances)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: FAIL with `ImportError: cannot import name 'compute_sector_distances'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to obstacle_avoidance.py

def compute_sector_distances(
    points: list[tuple[float, float]], num_sectors: int = 36
) -> list[float]:
    sector_width_deg = 360.0 / num_sectors
    distances = [float("inf")] * num_sectors

    for angle_deg, distance_mm in points:
        if distance_mm <= 0.0:
            continue
        sector_index = int((angle_deg % 360.0) // sector_width_deg)
        sector_index = min(sector_index, num_sectors - 1)
        if distance_mm < distances[sector_index]:
            distances[sector_index] = distance_mm

    return distances
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add obstacle_avoidance.py tests/test_obstacle_avoidance.py
git commit -m "feat: compute per-sector minimum distance histogram"
```

---

### Task 4: Free-sector heading decision (VFH-lite)

**Files:**
- Modify: `obstacle_avoidance.py`
- Test: `tests/test_obstacle_avoidance.py`

Sector `0` is defined as straight ahead (robot heading). Sectors are indexed
`0..num_sectors-1` going counter-clockwise (matching the angle convention
from `compute_sector_distances`, where angle 0 = front). Given the sector
distances and a safety threshold in mm, decide:
- `"forward"` if the front sector (index 0) is clear.
- `"turn_left"` / `"turn_right"` with the target sector index if front is
  blocked but some sector within the search window is free — choosing the
  candidate with the smallest angular distance from the front (shortest
  turn wins; ties break toward the left/counter-clockwise sector since that
  matches the positive-angle convention used elsewhere in this module).
- `"stop_and_back"` if no sector within the search window is free.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_obstacle_avoidance.py
from obstacle_avoidance import decide_heading

SAFETY_MM = 400.0


def test_decide_heading_goes_forward_when_front_clear():
    distances = [float("inf")] * 36
    action, target_sector = decide_heading(distances, safety_threshold_mm=SAFETY_MM)
    assert action == "forward"
    assert target_sector == 0


def test_decide_heading_turns_to_nearest_free_sector_on_the_right():
    distances = [float("inf")] * 36
    distances[0] = 200.0   # front blocked
    distances[1] = 200.0   # 10 deg left blocked too
    distances[35] = 5000.0  # 10 deg right (counter-clockwise index 35) is free
    action, target_sector = decide_heading(distances, safety_threshold_mm=SAFETY_MM)
    assert action == "turn_right"
    assert target_sector == 35


def test_decide_heading_turns_to_nearest_free_sector_on_the_left():
    distances = [float("inf")] * 36
    distances[0] = 200.0    # front blocked
    distances[1] = 5000.0   # 10 deg left is free
    distances[35] = 200.0   # 10 deg right blocked too
    action, target_sector = decide_heading(distances, safety_threshold_mm=SAFETY_MM)
    assert action == "turn_left"
    assert target_sector == 1


def test_decide_heading_stops_and_backs_when_all_blocked():
    distances = [200.0] * 36
    action, target_sector = decide_heading(distances, safety_threshold_mm=SAFETY_MM)
    assert action == "stop_and_back"
    assert target_sector is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: FAIL with `ImportError: cannot import name 'decide_heading'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to obstacle_avoidance.py

FRONT_SEARCH_WINDOW_DEG = 60.0  # search +-60 deg around the front for a free sector


def decide_heading(
    sector_distances: list[float],
    safety_threshold_mm: float,
) -> tuple[str, int | None]:
    num_sectors = len(sector_distances)
    sector_width_deg = 360.0 / num_sectors

    def is_free(index: int) -> bool:
        return sector_distances[index] >= safety_threshold_mm

    if is_free(0):
        return "forward", 0

    max_steps = int(FRONT_SEARCH_WINDOW_DEG // sector_width_deg)
    for step in range(1, max_steps + 1):
        left_index = step % num_sectors
        right_index = (-step) % num_sectors

        left_free = is_free(left_index)
        right_free = is_free(right_index)

        if left_free and right_free:
            return "turn_left", left_index
        if left_free:
            return "turn_left", left_index
        if right_free:
            return "turn_right", right_index

    return "stop_and_back", None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add obstacle_avoidance.py tests/test_obstacle_avoidance.py
git commit -m "feat: add VFH-lite free-sector heading decision"
```

---

### Task 5: Translate heading decision into a safe Twist

**Files:**
- Modify: `obstacle_avoidance.py`
- Test: `tests/test_obstacle_avoidance.py`

Convert the `(action, target_sector)` decision into `(linear, angular)`
velocity values, clamped to explicit limits. Turning never moves forward
(pure rotate-in-place, matching the "gira y evalua de nuevo" behavior from
the spec). `stop_and_back` moves straight back at reduced speed with zero
angular velocity.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_obstacle_avoidance.py
from obstacle_avoidance import twist_for_decision

MAX_LINEAR = 0.15
MAX_ANGULAR = 1.0


def test_twist_for_forward_moves_straight():
    linear, angular = twist_for_decision("forward", 0, num_sectors=36, max_linear=MAX_LINEAR, max_angular=MAX_ANGULAR)
    assert linear == MAX_LINEAR
    assert angular == 0.0


def test_twist_for_turn_left_rotates_in_place():
    linear, angular = twist_for_decision("turn_left", 1, num_sectors=36, max_linear=MAX_LINEAR, max_angular=MAX_ANGULAR)
    assert linear == 0.0
    assert angular == MAX_ANGULAR


def test_twist_for_turn_right_rotates_in_place():
    linear, angular = twist_for_decision("turn_right", 35, num_sectors=36, max_linear=MAX_LINEAR, max_angular=MAX_ANGULAR)
    assert linear == 0.0
    assert angular == -MAX_ANGULAR


def test_twist_for_stop_and_back_reverses_slowly():
    linear, angular = twist_for_decision("stop_and_back", None, num_sectors=36, max_linear=MAX_LINEAR, max_angular=MAX_ANGULAR)
    assert linear == -MAX_LINEAR / 2
    assert angular == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: FAIL with `ImportError: cannot import name 'twist_for_decision'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to obstacle_avoidance.py

def twist_for_decision(
    action: str,
    target_sector: int | None,
    num_sectors: int,
    max_linear: float,
    max_angular: float,
) -> tuple[float, float]:
    if action == "forward":
        return max_linear, 0.0

    if action == "turn_left":
        return 0.0, max_angular

    if action == "turn_right":
        return 0.0, -max_angular

    if action == "stop_and_back":
        return -max_linear / 2, 0.0

    raise ValueError(f"unknown action: {action}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add obstacle_avoidance.py tests/test_obstacle_avoidance.py
git commit -m "feat: translate heading decisions into clamped Twist values"
```

---

### Task 6: Watchdog for stale LiDAR data

**Files:**
- Modify: `obstacle_avoidance.py`
- Test: `tests/test_obstacle_avoidance.py`

If no new scan has arrived within `WATCHDOG_TIMEOUT_S` seconds, the caller
must stop the robot. This is a pure time-comparison function so the live loop
(Task 7) can call it without needing real sockets/clocks in tests.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_obstacle_avoidance.py
from obstacle_avoidance import is_watchdog_tripped

WATCHDOG_TIMEOUT_S = 0.5


def test_watchdog_not_tripped_within_timeout():
    assert is_watchdog_tripped(last_scan_time=10.0, now=10.3, timeout_s=WATCHDOG_TIMEOUT_S) is False


def test_watchdog_tripped_after_timeout():
    assert is_watchdog_tripped(last_scan_time=10.0, now=10.6, timeout_s=WATCHDOG_TIMEOUT_S) is True


def test_watchdog_tripped_exactly_at_timeout_boundary():
    assert is_watchdog_tripped(last_scan_time=10.0, now=10.5, timeout_s=WATCHDOG_TIMEOUT_S) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: FAIL with `ImportError: cannot import name 'is_watchdog_tripped'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to obstacle_avoidance.py

def is_watchdog_tripped(last_scan_time: float, now: float, timeout_s: float) -> bool:
    return (now - last_scan_time) >= timeout_s
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: PASS (17 tests)

- [ ] **Step 5: Commit**

```bash
git add obstacle_avoidance.py tests/test_obstacle_avoidance.py
git commit -m "feat: add watchdog timeout check for stale LiDAR data"
```

---

### Task 7: Dry-run live loop (prints decisions, publishes nothing)

**Files:**
- Modify: `obstacle_avoidance.py`

Wire the pure functions above into a loop that connects to the LiDAR TCP
socket (same protocol `ver_lidar.py` already uses successfully) and prints
each decision. No `rclpy` import yet, no robot movement yet — this step is
purely about validating the algorithm against real LiDAR data safely.

- [ ] **Step 1: Add constants and the socket reader at the top of `obstacle_avoidance.py`**

```python
# add near the top of obstacle_avoidance.py, below the imports

PI_IP = "10.39.220.138"  # actualizar si cambia la IP de la Pi
LIDAR_PORT = 5001

NUM_SECTORS = 36
SAFETY_THRESHOLD_MM = 400.0
MAX_LINEAR = 0.15
MAX_ANGULAR = 1.0
WATCHDOG_TIMEOUT_S = 0.5


def read_scans(sock: socket.socket):
    """Yields raw scan payloads (bytes) from lidar_server.py's length-prefixed protocol."""
    buf = b""
    while True:
        while len(buf) < 4:
            chunk = sock.recv(65536)
            if not chunk:
                return
            buf += chunk
        (length,) = struct.unpack(">I", buf[:4])
        buf = buf[4:]
        while len(buf) < length:
            chunk = sock.recv(65536)
            if not chunk:
                return
            buf += chunk
        payload, buf = buf[:length], buf[length:]
        yield payload
```

- [ ] **Step 2: Add the dry-run main loop at the bottom of `obstacle_avoidance.py`**

```python
# append to obstacle_avoidance.py

def run_dry_run():
    import time

    sock = socket.socket()
    sock.connect((PI_IP, LIDAR_PORT))
    print(f"Conectado al lidar en {PI_IP}:{LIDAR_PORT}, modo DRY-RUN (no publica nada)")

    last_scan_time = time.monotonic()

    try:
        for payload in read_scans(sock):
            now = time.monotonic()
            last_scan_time = now

            points = parse_scan_payload(payload)
            distances = compute_sector_distances(points, num_sectors=NUM_SECTORS)
            action, target_sector = decide_heading(distances, safety_threshold_mm=SAFETY_THRESHOLD_MM)
            linear, angular = twist_for_decision(
                action, target_sector, NUM_SECTORS, MAX_LINEAR, MAX_ANGULAR
            )

            print(f"action={action:15s} linear={linear:+.2f} angular={angular:+.2f}")
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    run_dry_run()
```

- [ ] **Step 3: Run the pure-function test suite once more to confirm nothing broke**

Run: `python3 -m pytest tests/test_obstacle_avoidance.py -v`
Expected: PASS (17 tests) — Step 1/2 added no new pure functions, so the
count should not change.

- [ ] **Step 4: Manual validation against the real LiDAR (Pi untouched, robot not moving)**

In WSL, with `lidar_server.py` already running on the Pi (unchanged):
```bash
python3 obstacle_avoidance.py
```
Wave a hand/object in front of the sensor and confirm the printed `action`
switches between `forward`, `turn_left`/`turn_right`, and `stop_and_back` as
expected, with no crashes and no `rclpy` involved at all yet.

- [ ] **Step 5: Commit**

```bash
git add obstacle_avoidance.py
git commit -m "feat: add dry-run live loop for obstacle avoidance against real LiDAR"
```

---

### Task 8: Live mode — publish to the real Create3 (only after explicit go-ahead)

**Files:**
- Modify: `obstacle_avoidance.py`

**Do not implement this task until the user has validated Task 7's dry-run
output on the real robot and explicitly says to go live.** This task adds
`rclpy` publishing behind a `--live` CLI flag; default behavior stays
dry-run. The exact `cmd_vel` topic name must come from the Fase 0 discovery
results recorded in Task 1 — do not assume `/cmd_vel` without confirming it
against the recorded topic list first (the Create3 may namespace it, e.g.
`/turtlebot4/cmd_vel`, depending on the discovery output).

- [ ] **Step 1: Read the confirmed cmd_vel topic name from the spec's discovery section**

Open `docs/superpowers/specs/2026-07-09-turtlebot4-sensor-fusion-design.md`
and copy the exact topic name recorded in Task 1 into a `CMD_VEL_TOPIC`
constant in `obstacle_avoidance.py`.

- [ ] **Step 2: Add `--live` argument parsing and an `rclpy` publisher path**

```python
# modify the bottom of obstacle_avoidance.py

import argparse

from rclpy.node import Node
from geometry_msgs.msg import Twist
import rclpy


class ObstacleAvoidanceNode(Node):
    def __init__(self):
        super().__init__("obstacle_avoidance")
        self.pub = self.create_publisher(Twist, CMD_VEL_TOPIC, 10)

    def publish(self, linear: float, angular: float):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self.pub.publish(msg)


def run_live():
    import time

    rclpy.init()
    node = ObstacleAvoidanceNode()

    sock = socket.socket()
    sock.connect((PI_IP, LIDAR_PORT))
    print(f"Conectado al lidar en {PI_IP}:{LIDAR_PORT}, modo LIVE — publicando a {CMD_VEL_TOPIC}")

    last_scan_time = time.monotonic()

    try:
        for payload in read_scans(sock):
            now = time.monotonic()
            last_scan_time = now

            points = parse_scan_payload(payload)
            distances = compute_sector_distances(points, num_sectors=NUM_SECTORS)
            action, target_sector = decide_heading(distances, safety_threshold_mm=SAFETY_THRESHOLD_MM)
            linear, angular = twist_for_decision(
                action, target_sector, NUM_SECTORS, MAX_LINEAR, MAX_ANGULAR
            )

            if is_watchdog_tripped(last_scan_time, time.monotonic(), WATCHDOG_TIMEOUT_S):
                linear, angular = 0.0, 0.0

            node.publish(linear, angular)
            print(f"action={action:15s} linear={linear:+.2f} angular={angular:+.2f}")
    except KeyboardInterrupt:
        pass
    finally:
        node.publish(0.0, 0.0)
        sock.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="publica de verdad al Create3 real")
    args = parser.parse_args()

    if args.live:
        run_live()
    else:
        run_dry_run()
```

Remove the old `if __name__ == "__main__": run_dry_run()` block from Task 7
Step 2 since it is replaced by the argument-parsing block above.

- [ ] **Step 3: Manual validation — robot lifted off the ground first**

With the Create3 physically lifted so wheels can spin freely without moving
the robot, run:
```bash
python3 obstacle_avoidance.py --live
```
Confirm wheels respond correctly to a hand-waved obstacle (turn away, stop,
back off) before ever testing on the floor. Only after this passes, retest
on the floor in an open, obstacle-padded area.

- [ ] **Step 4: Commit**

```bash
git add obstacle_avoidance.py
git commit -m "feat: add --live mode to publish obstacle avoidance to the real Create3"
```

---

## Self-Review Notes

- **Spec coverage:** Fase 0 (Task 1) and Fase 1 (Tasks 2–8: parsing, sectorization, VFH-lite heading, Twist limits, watchdog, dry-run validation, live publish) are covered. Fases 2–5 (camera fusion, EKF, visited grid, QR/signs) are intentionally out of scope for this plan — they get their own plans once Fase 1 is validated on hardware, since the spec explicitly calls out obstacle avoidance as the first thing to implement and validate.
- **Placeholder scan:** no TBD/TODO; every step has real code or a concrete manual command with expected output.
- **Type consistency:** `sector_distances: list[float]`, `(action: str, target_sector: int | None)`, and `(linear: float, angular: float)` signatures are used identically across Tasks 3–8.
- **Pi untouched:** every task reads from the existing `lidar_server.py` socket as-is; no task creates or modifies any file on the Raspberry Pi.
