import subprocess
import os
import time
import curses
from lxc_tui.core import log_debug, safe_addstr

def get_lxc_column(column_name):
    try:
        with open(os.devnull, 'w') as devnull:
            proc = subprocess.Popen(["lxc-ls", "--fancy", f"--fancy-format={column_name}"],
                                    stdout=subprocess.PIPE, stderr=devnull, text=True, encoding='utf-8', start_new_session=True)
            lines = [line.strip() for line in proc.stdout if line.strip()]
            proc.wait(timeout=5)
            return lines[1:] if lines else []
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        log_debug(f"Error in get_lxc_column for column {column_name}: {e}")
        return []
    except Exception as e:
        log_debug(f"Unexpected error in get_lxc_column: {e}")
        return []

def get_lxc_info(include_stopped=False):
    try:
        names = get_lxc_column("NAME")
        states = get_lxc_column("STATE")
        ipv4s = get_lxc_column("IPV4")
        ipv6s = get_lxc_column("IPV6")
        unprivilegeds = get_lxc_column("UNPRIVILEGED")

        min_length = min(len(names), len(states), len(ipv4s), len(ipv6s), len(unprivilegeds))
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
            config_info = dict(line.strip().split(":", 1) for line in conf_file if ":" in line)
    return config_info

def execute_lxc_command(stdscr, command, operation_done_event):
    try:
        log_debug(f"Executing command: {' '.join(command)}")
        with open(os.devnull, 'w') as devnull:
            proc = subprocess.Popen(command, start_new_session=True, stdout=devnull, stderr=devnull)
            animation = ['|', '/', '-', '\\']
            idx = 0
            start_time = time.time()
            while proc.poll() is None and (time.time() - start_time) < 15:
                safe_addstr(stdscr, curses.LINES - 2, 0, f"Executing {command[0]} {command[-1]} {animation[idx % 4]}", curses.color_pair(4))
                stdscr.refresh()
                time.sleep(0.1)
                idx += 1
            proc.wait(timeout=15 - (time.time() - start_time))
        log_debug(f"Command completed with return code {proc.returncode}")
        return proc.returncode == 0
    except subprocess.TimeoutExpired as e:
        log_debug(f"Command timed out: {e}")
        proc.kill()
        safe_addstr(stdscr, curses.LINES - 2, 0, f"Command {command[0]} {command[-1]} timed out", curses.color_pair(2))
        stdscr.refresh()
        time.sleep(2)
        return False
    except Exception as e:
        log_debug(f"Error executing command: {e}")
        safe_addstr(stdscr, curses.LINES - 2, 0, f"Error executing {command[0]} {command[-1]}: {e}", curses.color_pair(2))
        stdscr.refresh()
        time.sleep(2)
        return False

def refresh_lxc_info(lxc_info, stop_event, pause_event, show_stopped):
    while not stop_event.is_set():
        if not pause_event.is_set():
            new_lxc_info = get_lxc_info(show_stopped)
            if new_lxc_info != lxc_info:
                lxc_info[:] = new_lxc_info
                log_debug("LXC info refreshed")
        time.sleep(0.5)