#!/usr/bin/env python3
"""
Joystick -> Bluetooth (rfcomm) controller for mapping mode.
**CONFIGURED VERSION with 135° CW rotation**

This version applies a 135° clockwise coordinate transformation to fix the
front direction mismatch. The joystick forward now correctly maps to the 
robot's actual forward direction.

Packet format is IDENTICAL to vel.py:   <x,y,w>\n
    x = lateral   (ROS linear.y,  left  +)   -> 127 = stop
    y = forward   (ROS linear.x,  front +)   -> 127 = stop
    w = rotation  (ROS angular.z, CCW   +)   -> 127 = stop
Each field is 0..255 with centre 127, same as vel.py.

Controls:
    Left stick        : forward/back (Y) and strafe (X)
    B6 / B7           : rotate left (CCW) / rotate right (CW)
    Hold B4 (deadman) : robot only moves while held (set REQUIRE_DEADMAN=False to disable)
    Release B4 / lose focus / joystick unplugged / BT lost -> sends <127,127,127>

Do NOT run this at the same time as vel.py (both would use the same port).
"""

import glob
import math
import tkinter as tk
from tkinter import ttk

import pygame
import serial
import serial.tools.list_ports

# ── SETTINGS ─────────────────────────────────────────────────────────────
RFCOMM_BAUD = 115200
SEND_PERIOD_MS = 50          # 20 Hz

NEUTRAL = 127                # same centre as vel.py
SPEED_SCALE = 0.5            # 1.0 = full range (127 +/- 127). Applies to translation
ROT_SCALE = 0.5              # rotation strength for B6/B7 (same idea as ANGULAR_GAIN in vel.py)
STICK_DEADZONE = 0.12        # ignore small stick drift

# ═══════════════════════════════════════════════════════════════════════════
# COORDINATE ROTATION: 135° Clockwise
# ═══════════════════════════════════════════════════════════════════════════
# To rotate a vector (x, y) by angle θ clockwise:
#   x' = x·cos(θ) + y·sin(θ)
#   y' = -x·sin(θ) + y·cos(θ)
# For 135° CW (or equivalently -135° CCW, or +225° CCW):
ROTATION_ANGLE_DEG = 135  # clockwise
ROTATION_ANGLE_RAD = math.radians(-ROTATION_ANGLE_DEG)  # negative for CW
COS_THETA = math.cos(ROTATION_ANGLE_RAD)  # cos(-135°) = -√2/2
SIN_THETA = math.sin(ROTATION_ANGLE_RAD)  # sin(-135°) = -√2/2

# Joystick mapping (check the numbers shown in the GUI and change if needed)
AXIS_X = 0                   # left stick horizontal (right = +)
AXIS_Y = 1                   # left stick vertical   (down  = +)
BTN_ROT_LEFT = 6             # CCW
BTN_ROT_RIGHT = 7            # CW
BTN_DEADMAN = 4              # hold to enable motion
REQUIRE_DEADMAN = True

# Flip these if the robot moves the wrong way (applied AFTER rotation)
INVERT_FORWARD = False
INVERT_LATERAL = False
INVERT_ROTATION = False
# ─────────────────────────────────────────────────────────────────────────

pygame.init()
pygame.joystick.init()

joystick = None
connected = False
ser = None
axis_labels, button_labels = [], []
left_stick_dot = right_stick_dot = None
last_packet = f"<{NEUTRAL},{NEUTRAL},{NEUTRAL}>"


# ── Helpers ──────────────────────────────────────────────────────────────
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def deadzone(v, dz=STICK_DEADZONE):
    if abs(v) < dz:
        return 0.0
    # rescale so output starts smoothly from 0 after the deadzone
    return math.copysign((abs(v) - dz) / (1.0 - dz), v)


def to_byte(cmd):
    """cmd in [-1, 1] -> 0..255 with centre 127 (same mapping style as vel.py)."""
    return int(clamp(round(NEUTRAL + cmd * 127.5), 0, 255))


def rotate_coordinates(x, y):
    """
    Apply 135° clockwise rotation to coordinate system.
    
    Args:
        x: lateral input (joystick convention: left = -)
        y: forward input (joystick convention: forward = -)
    
    Returns:
        (x_rotated, y_rotated): coordinates in robot's frame
    """
    x_rot = x * COS_THETA - y * SIN_THETA
    y_rot = x * SIN_THETA + y * COS_THETA
    return x_rot, y_rot


def build_packet(axes, buttons):
    """Convert joystick state to ROS-convention values, then to the <x,y,w> packet."""
    def btn(i):
        return buttons[i] if 0 <= i < len(buttons) else 0

    if REQUIRE_DEADMAN and not btn(BTN_DEADMAN):
        return f"<{NEUTRAL},{NEUTRAL},{NEUTRAL}>\n"

    raw_x = axes[AXIS_X] if AXIS_X < len(axes) else 0.0
    raw_y = axes[AXIS_Y] if AXIS_Y < len(axes) else 0.0

    # pygame: right = +x, down = +y  ->  convert to: left = +lateral, forward = +forward
    # Step 1: Apply deadzone and invert to match ROS convention (before rotation)
    lateral_input = -deadzone(raw_x)   # right stick = negative lateral (left is +)
    forward_input = -deadzone(raw_y)   # down stick = negative forward (forward is +)
    
    # Step 2: Apply 135° CW coordinate rotation
    lateral, forward = rotate_coordinates(lateral_input, forward_input)
    
    # Step 3: Apply speed scaling
    lateral *= SPEED_SCALE
    forward *= SPEED_SCALE
    
    # Step 4: Rotation is independent of coordinate frame
    rotation = (btn(BTN_ROT_LEFT) - btn(BTN_ROT_RIGHT)) * ROT_SCALE   # CCW = +

    # Step 5: Apply optional inversions (if needed after testing)
    if INVERT_FORWARD:
        forward = -forward
    if INVERT_LATERAL:
        lateral = -lateral
    if INVERT_ROTATION:
        rotation = -rotation

    # Same order as vel.py: x=lateral, y=forward, w=rotation
    return f"<{to_byte(lateral)},{to_byte(forward)},{to_byte(rotation)}>\n"


def neutral_packet():
    return f"<{NEUTRAL},{NEUTRAL},{NEUTRAL}>\n"


def send(packet):
    """Write to Bluetooth. Returns False if the link is lost."""
    global ser
    if ser and ser.is_open:
        try:
            ser.write(packet.encode("utf-8"))
            return True
        except (serial.SerialException, OSError):
            return False
    return True


# ── Bluetooth ────────────────────────────────────────────────────────────
def get_available_ports():
    devices = list(glob.glob("/dev/rfcomm*"))
    for p in serial.tools.list_ports.comports():
        if "rfcomm" in p.device and p.device not in devices:
            devices.append(p.device)
    return devices


def close_serial(msg="Bluetooth: Disconnected"):
    global ser
    if ser:
        try:
            if ser.is_open:
                ser.write(neutral_packet().encode("utf-8"))
                ser.close()
        except Exception:
            pass
    ser = None
    connect_button.config(text="Connect", state=tk.NORMAL)
    status_serial.set(msg)


def connect_serial():
    global ser
    if ser and ser.is_open:
        close_serial()
        return

    port = port_var.get()
    if not port or port == "Pilih Port":
        status_serial.set("Bluetooth: rfcomm belum ada.\n"
                          "sudo rfcomm bind /dev/rfcomm0 <MAC_ESP32> 1")
        return

    connect_button.config(state=tk.DISABLED)
    status_serial.set(f"Bluetooth: Connecting to {port}...")
    root.update_idletasks()
    try:
        ser = serial.Serial(port, RFCOMM_BAUD, timeout=0.05, write_timeout=0.2)
        connect_button.config(text="Disconnect", state=tk.NORMAL)
        status_serial.set(f"Bluetooth: Connected to {port} [135° CW rotation active]")
    except serial.SerialException as e:
        ser = None
        connect_button.config(text="Connect", state=tk.NORMAL)
        status_serial.set(f"Bluetooth: FAILED! ({e})")


def refresh_ports():
    ports = get_available_ports()
    port_combobox["values"] = ports
    if ports:
        port_var.set(ports[0])
        status_serial.set(f"Bluetooth: Found {ports[0]}. Ready.")
    else:
        port_var.set("Pilih Port")
        status_serial.set("Bluetooth: rfcomm belum ada.\n"
                          "sudo rfcomm bind /dev/rfcomm0 <MAC_ESP32> 1")


# ── Joystick detect / GUI build ──────────────────────────────────────────
def update_joystick():
    global connected, joystick, left_stick_dot, right_stick_dot

    if pygame.joystick.get_count() > 0:
        if not connected:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            connected = True
            status_var.set(f"Controller connected: {joystick.get_name()}")

            for lbl in axis_labels + button_labels:
                lbl.destroy()
            axis_labels.clear()
            button_labels.clear()

            for i in range(joystick.get_numaxes()):
                lbl = tk.Label(axis_frame, text=f"Axis {i}: 0.000", width=15, anchor="w")
                lbl.pack(anchor="w")
                axis_labels.append(lbl)

            n = joystick.get_numbuttons()
            split = math.ceil(n / 2.0)
            for i in range(n):
                parent = button_frame_row1 if i < split else button_frame_row2
                lbl = tk.Label(parent, text=f"B{i}: 0", width=8, anchor="w")
                lbl.pack(side="left")
                button_labels.append(lbl)

            left_canvas.delete("all")
            right_canvas.delete("all")
            left_canvas.create_oval(10, 10, 90, 90, outline="grey", width=2)
            right_canvas.create_oval(10, 10, 90, 90, outline="grey", width=2)
            left_stick_dot = left_canvas.create_oval(45, 45, 55, 55, fill="blue", outline="blue")
            right_stick_dot = right_canvas.create_oval(45, 45, 55, 55, fill="blue", outline="blue")
    else:
        if connected:
            connected = False
            joystick = None
            status_var.set("Controller disconnected")
            for lbl in axis_labels + button_labels:
                lbl.destroy()
            axis_labels.clear()
            button_labels.clear()
            left_canvas.delete("all")
            right_canvas.delete("all")
            left_stick_dot = right_stick_dot = None


def check_connection():
    update_joystick()
    root.after(2000, check_connection)


# ── Main loop ────────────────────────────────────────────────────────────
def read_input():
    global last_packet
    pygame.event.pump()
    packet = neutral_packet()   # default = STOP

    if connected and joystick:
        try:
            axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
            buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]

            # GUI update
            for i, v in enumerate(axes):
                if i < len(axis_labels):
                    axis_labels[i].config(text=f"Axis {i}: {v:+.3f}")
            if len(axes) >= 2 and left_stick_dot:
                x, y = 50 + axes[0] * 40, 50 + axes[1] * 40
                left_canvas.coords(left_stick_dot, x - 5, y - 5, x + 5, y + 5)
            if len(axes) >= 4 and right_stick_dot:
                x, y = 50 + axes[2] * 40, 50 + axes[3] * 40
                right_canvas.coords(right_stick_dot, x - 5, y - 5, x + 5, y + 5)
            for i, v in enumerate(buttons):
                if i < len(button_labels):
                    button_labels[i].config(text=f"B{i}: {v}")

            # Stop if the window lost focus
            if root.focus_displayof() is not None:
                packet = build_packet(axes, buttons)
        except pygame.error:
            pass

    if packet.strip() != last_packet:
        last_packet = packet.strip()
        print(last_packet)

    if ser and ser.is_open and not send(packet):
        close_serial("Bluetooth: Lost connection!")

    root.after(SEND_PERIOD_MS, read_input)


# ── GUI setup ────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("Controller Monitor (Bluetooth Control) [135° CW Configured]")

serial_control_frame = tk.Frame(root)
serial_control_frame.pack(fill="x", padx=10, pady=5)

tk.Label(serial_control_frame, text="BT DEVICE:").pack(side="left", padx=(0, 5))
port_var = tk.StringVar(root, value="Pilih Port")
port_combobox = ttk.Combobox(serial_control_frame, textvariable=port_var, width=18, state="readonly")
port_combobox.pack(side="left", padx=(0, 15))

tk.Button(serial_control_frame, text="Refresh", command=refresh_ports).pack(side="left", padx=5)
connect_button = tk.Button(serial_control_frame, text="Connect", command=connect_serial)
connect_button.pack(side="left", padx=5)

status_serial = tk.StringVar(root, value="Bluetooth: Ready")
tk.Label(serial_control_frame, textvariable=status_serial, fg="blue").pack(side="left", padx=(15, 0))

status_var = tk.StringVar(value="Waiting for controller...")
tk.Label(root, textvariable=status_var, font=("Consolas", 10)).pack(pady=5, fill="x")

# Add rotation indicator
rotation_info_frame = tk.Frame(root, bg="#FFE5B4", relief="ridge", borderwidth=2)
rotation_info_frame.pack(fill="x", padx=10, pady=5)
tk.Label(rotation_info_frame, text="🔄 COORDINATE ROTATION: 135° Clockwise Applied", 
         font=("Consolas", 10, "bold"), bg="#FFE5B4", fg="#D2691E").pack(pady=5)

main_content_frame = tk.Frame(root)
main_content_frame.pack(fill="both", expand=True, padx=10, pady=10)

axis_frame = tk.Frame(main_content_frame, borderwidth=1, relief="sunken")
axis_frame.pack(side="left", fill="y", padx=5)
tk.Label(axis_frame, text="AXES", font=("Consolas", 10, "bold")).pack(anchor="w")

button_container_frame = tk.Frame(main_content_frame, borderwidth=1, relief="sunken")
button_container_frame.pack(side="left", fill="y", padx=5)
tk.Label(button_container_frame, text="BUTTONS", font=("Consolas", 10, "bold")).pack(anchor="w")
button_frame_row1 = tk.Frame(button_container_frame)
button_frame_row1.pack(anchor="w")
button_frame_row2 = tk.Frame(button_container_frame)
button_frame_row2.pack(anchor="w")

viz_frame = tk.Frame(main_content_frame, borderwidth=1, relief="sunken")
viz_frame.pack(side="left", fill="both", expand=True, padx=5)
tk.Label(viz_frame, text="ANALOG STICKS", font=("Consolas", 10, "bold")).pack()
stick_canvas_frame = tk.Frame(viz_frame)
stick_canvas_frame.pack(pady=10)

left_stick_frame = tk.Frame(stick_canvas_frame)
left_stick_frame.pack(side="left", padx=10, anchor="n")
tk.Label(left_stick_frame, text="Left").pack()
left_canvas = tk.Canvas(left_stick_frame, width=100, height=100, bg="white")
left_canvas.pack()

right_stick_frame = tk.Frame(stick_canvas_frame)
right_stick_frame.pack(side="left", padx=10, anchor="n")
tk.Label(right_stick_frame, text="Right").pack()
right_canvas = tk.Canvas(right_stick_frame, width=100, height=100, bg="white")
right_canvas.pack()

tk.Label(root, text=f"Hold B{BTN_DEADMAN} to move | Left stick: move/strafe | "
                    f"B{BTN_ROT_LEFT}/B{BTN_ROT_RIGHT}: rotate",
         font=("Consolas", 9)).pack(pady=(0, 5))


def on_close():
    close_serial()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

refresh_ports()
check_connection()
read_input()
root.mainloop()

close_serial()
pygame.quit()

