# ipmi-fan-controller

This is a python script to monitor various system temperatures reported by [ipmitool](https://codeberg.org/IPMITool/ipmitool) and adjust PWM fan speeds according to a predefined fan curve. This script was tested on a Supermicro H11SSL-I. Will likely work on other motherboards with minimal adjustments. **Please ensure the script is suitable for your system before running.**

The script can optionally monitor temperatures of NVidia GPUs via the `nvidia-smi` utility. See the script itself for more details.

## Systemd Service File

Provided below is an example systemd unit file to run the script on startup. Change the `ExecStart` location to wherever you cloned the repo to.

```
Description=IPMI-based fan speed controller
After=network.target

[Service]
Type=exec
Restart=always
User=root
ExecStartPre=ipmitool raw 0x30 0x45 0x01 0x01
ExecStopPost=ipmitool raw 0x30 0x45 0x01 0x01
StandardOutput=journal
StandardError=journal

ExecStart=/usr/bin/python /path-to-git-repo/main.py

[Install]
WantedBy=default.target
```
