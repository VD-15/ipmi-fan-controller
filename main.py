import os
import sys
import subprocess
from time import sleep
import threading

# Scan temps and update PWM every INTERVAL seconds.
INTERVAL = 10

# Check for root
current_user = subprocess.run(['whoami'], capture_output=True, text=True)

# Hex sequence to send to ipmitool to get it to change the fan speed.
# Sequences may differ per motherboard, the one provided below is for Supermicro X9 / X10 / X11 boards:
# https://forums.servethehome.com/index.php?resources/supermicro-x9-x10-x11-fan-speed-control.20/
IPMITOOL_PREFIX = ['0x30', '0x70', '0x66', '0x01']

# Fan zones to set speeds for. Most supermicro boards come with two fan zones.
IPMITOOL_ZONES  = ['0x01', '0x00']

# Need to be root to edit IPMI settings. Could also change with username and password.
if current_user.stdout != 'root\n':
    print('Need to be running as root to change system fan speeds', flush=True)
    print('Running as user: ' + str(current_user.stdout), flush=True)
    exit(-1)
else:
    print('Running as root.', flush=True)

# Set fan mode to 'full' so the IPMI doesn't change our fan speeds once set.
# The required hex sequence may change depending on your board.
subprocess.run(['ipmitool', 'raw', '0x30', '0x45', '0x01', '0x01'])

# Struct storing all the temperature values we're tracking.
temps = {}

# Monitors temperatures for NVidia GPUs via nvidia-smi.
def gpuwatch():
    # Wrap in a while true in case the subprocess dies
    while True:
        # Start nvidia-smi as a daemon to report GPU temps.
        proc = subprocess.Popen(['nvidia-smi', 'dmon', '-s', 'p', '-d', str(INTERVAL)], stdout=subprocess.PIPE, text=True)
        line = proc.stdout.readline()
      
        # daemon will print lines continuously.
        while line:
            try:
                s = line.split()
                # Some lines will be comment or error lines and not list a GPU.
                if s[0].isdigit():
                    temps['gpu' + s[0]] = float(s[2])
            except Exception as ex:
                print(str(ex), file=sys.stderr, flush=True)
            line = proc.stdout.readline()

# Monitor CPU and system temperatures using ipmitool.
def cpuwatch():
    while True:
        sensors = subprocess.run(['ipmitool', 'sensor'], capture_output=True, text=True)

        for line in sensors.stdout.splitlines():
            try:
                # Monitor CPU, System and Peripheral temps.
                vals = [l.strip() for l in line.split('|')]
                match vals[0]:
                    case 'CPU Temp':
                        temps['cpu'] = float(vals[1])
                    case 'System Temp':
                        temps['system'] = float(vals[1])
                    case 'Peripheral Temp':
                        temps['peripheral'] = float(vals[1])
                    case _:
                        pass
            except Exception as ex:
                print(str(ex), file=sys.stderr)
        sleep(INTERVAL)

# Start threads reading temps in background.
# Uncomment if monitoring NVidia GPU temperatures as well.
# g = threading.Thread(target=gpuwatch, daemon=True)
# g.start()
c = threading.Thread(target=cpuwatch, daemon=True)
c.start()

# Set fan speeds continuously
while True:
    if temps:
        try:
            # Make temperature decisions based on hottest component.
            m = max([temps[x] for x in temps])

            # Fan curve is (2x - 60)% this was suitable for my purposes.
            # Others may wish to modify depending on desired temperature range, but take care when doing so.
            fan_speed = (2 * m - 60)

            # IMPORTANT: clamp fan curve between 20% and 100%
            # Ensures a sensible minum and maximum fan speed
            clamp_speed = int(max(20, min(100, m)))

            # Convert fan speed to hex to pass to ipmitool.
            fan_hex = hex(int(fan_speed))

            # Print new fan speed and temperature to stdout.
            print('Temperature: ' + str(m) + ', fan speed: ' + str(fan_speed), ' (' + fan_hex + ')', flush=True)

            # Set fan speed of each zone.
            for zone in IPMITOOL_ZONES:
                subprocess.run(['ipmitool', 'raw', *IPMITOOL_PREFIX, zone, fan_hex], check=True, capture_output=True)
        except Exception as ex:
            print(str(ex), file=sys.stderr, flush=True)

    sleep(INTERVAL)
