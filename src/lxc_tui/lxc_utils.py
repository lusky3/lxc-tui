import subprocess
import os
import time
import curses
from lxc_tui.core import log_debug, safe_addstr

def get_lxc_column(column_name):
    try:
        proc = subprocess.run(
            ["lxc-ls", "--fancy", f"--fancy-format={column_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=True,
        )
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        log_debug(f"lxc-ls for {column_name} stderr: {proc.stderr}")
        return lines[1:] if lines else []
    except subprocess.TimeoutExpired:
        log_debug(f"Timeout in get_lxc_column for column {column_name}")
        return []
    except subprocess.CalledProcessError as e:
        log_debug(f"Error in get_lxc_column for column {column_name}: {e.stderr}")
        return []
    except Exception as e:
        log_debug(f"Unexpected error in get_lxc_column: {e}")
        return []

def get_lxc_info(include_stopped=False):
    try:
        start_time = time.time()
        names = get_lxc_column("NAME")
        states = get_lxc_column("STATE")
        ipv4s = get_lxc_column("IPV4")
        ipv6s = get_lxc_column("IPV6")
        unprivilegeds = get_lxc_column("UNPRIVILEGED")
        log_debug(f"get_lxc_info took {time.time() - start_time:.2f}s")

        min_length = min(
            len(names), len(states), len(ipv4s), len(ipv6s), len(unprivilegeds)
        )
        if min_length == 0:
            return []

        lxc_info = []
        for idx in range(min_length):
            lxc_id = names[idx].strip()
            status = states[idx].strip()
            ipv4 = ipv4s[idx].strip()
            ipv6 = ipv6s[idx].strip()
            unprivileged = unprivilegeds[idx].strip()

            if not include_stopped and status == "STOPPED":
                continue

            ipv4_addresses = ipv4.split(", ") if ipv4 != "-" else []
            ipv6_addresses = ipv6.split(", ") if ipv6 != "-" else []
            ip_addresses = ", ".join(filter(None, ipv4_addresses + ipv6_addresses))

            config_file = f"/etc/pve/lxc/{lxc_id}.conf"
            hostname = "Unknown"
            if os.path.exists(config_file):
                with open(config_file) as f:
                    for config_line in f:
                        if "hostname" in config_line:
                            hostname = config_line.split(":")[1].strip()
                            break

            lxc_info.append((lxc_id, hostname, status, ip_addresses, unprivileged))

        return lxc_info
    except Exception as e:
        log_debug(f"Error getting LXC info: {e}")
        return []

def get_lxc_config(lxc_id):
    config_file = f"/etc/pve/lxc/{lxc_id}.conf"
    config_info = {}
    if os.path.exists(config_file):
        with open(config_file) as conf_file:
            config_info = dict(
                line.strip().split(":", 1) for line in conf_file if ":" in line
            )
    return config_info

def execute_lxc_command(stdscr, command, operation_done_event):
    try:
        log_debug(f"Executing command: {' '.join(command)}")
        start_time = time.time()
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,  # Reduced to 2s
            check=False
        )
        elapsed = time.time() - start_time
        if result.returncode != 0:
            log_debug(f"Command failed after {elapsed:.2f}s: {result.stderr}")
            return False
        log_debug(f"Command completed after {elapsed:.2f}s with return code {result.returncode}")
        return True
    except subprocess.TimeoutExpired:
        log_debug(f"Command {command} timed out after 2s")
        return False
    except Exception as e:
        log_debug(f"Error executing command {command}: {e}")
        return False

def refresh_lxc_info(lxc_info, stop_event, pause_event, show_stopped):
    while not stop_event.is_set():
        if not pause_event.is_set():
            new_lxc_info = get_lxc_info(show_stopped)
            if new_lxc_info != lxc_info:
                lxc_info[:] = new_lxc_info
                log_debug("LXC info refreshed")
        time.sleep(30)  # Increased to 30s