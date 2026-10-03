#!/usr/bin/env python3
import os, pty, usb.core, usb.util, sys, time, threading

VID, PID = 0x067b, 0x2303
dev = usb.core.find(idVendor=VID, idProduct=PID)
if dev is None:
    print("❌ PL2303 not found"); sys.exit(1)

try:
    if dev.is_kernel_driver_active(0):
        dev.detach_kernel_driver(0)
except: pass

dev.set_configuration()

# Full PL2303 init sequence
def ctrl(rt, r, v, i, l):
    try: return dev.ctrl_transfer(rt, r, v, i, l)
    except: pass

ctrl(0xC0, 0x01, 0x8484, 0, 1)
ctrl(0x40, 0x01, 0x0404, 0, 0)
ctrl(0xC0, 0x01, 0x8484, 0, 1)
ctrl(0xC0, 0x01, 0x8383, 0, 1)
ctrl(0xC0, 0x01, 0x8484, 0, 1)
ctrl(0x40, 0x01, 0x0404, 1, 0)
ctrl(0xC0, 0x01, 0x8484, 0, 1)
ctrl(0xC0, 0x01, 0x8383, 0, 1)
ctrl(0x40, 0x01, 0, 1, 0)
ctrl(0x40, 0x01, 1, 0, 0)
ctrl(0x40, 0x01, 2, 0x44, 0)
# Set baud 115200: [0x00,0xC2,0x01,0x00] + 8N1
ctrl(0x21, 0x20, 0, 0, [0x00, 0xC2, 0x01, 0x00, 0x00, 0x00, 0x08])
ctrl(0x40, 0x01, 0x0505, 0x11, 0)
print("⚡ PL2303 init OK @ 115200")

# Find endpoints
cfg = dev.get_active_configuration()
intf = cfg[(0, 0)]
ep_out = usb.util.find_descriptor(intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
ep_in = usb.util.find_descriptor(intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
print(f"🎯 OUT endpoint: {hex(ep_out.bEndpointAddress)}")
print(f"🎯 IN endpoint:  {hex(ep_in.bEndpointAddress)}")

# PTY bridge
master, slave = pty.openpty()
slave_name = os.ttyname(slave)
if os.path.lexists('/dev/ttyUSB0'):
    os.remove('/dev/ttyUSB0')
os.symlink(slave_name, '/dev/ttyUSB0')
os.chmod(slave_name, 0o666)
print(f"📦 /dev/ttyUSB0 -> {slave_name}")

stop_flag = threading.Event()

# Anti-lag background reader thread
def reader_thread():
    while not stop_flag.is_set():
        try:
            response = dev.read(ep_in.bEndpointAddress, 64, timeout=50)
        except usb.core.USBTimeoutError:
            pass
        except usb.core.USBError:
            time.sleep(0.01)

threading.Thread(target=reader_thread, daemon=True).start()

print("🚀 Anti-Lag USB Bridge running...")
try:
    while True:
        try:
            data = os.read(master, 64)
            if data:
                dev.write(ep_out.bEndpointAddress, data, timeout=200)
        except OSError:
            time.sleep(0.001)
except KeyboardInterrupt:
    print("\nStopped.")
finally:
    stop_flag.set()
    if os.path.lexists('/dev/ttyUSB0'):
        os.remove('/dev/ttyUSB0')
