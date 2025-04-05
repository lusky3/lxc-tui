# LXC-TUI
# Author: Cody (lusky3)
# Usage: python lxc-tui.py
# Description: A terminal user interface for LXC containers on Proxmox.
# License: MIT
# Version: 0.1

import curses
import subprocess
import os
import time
import threading

screen_lock = threading.Lock()

def safe_addstr(stdscr, y, x, str, attr=0):
    with screen_lock:
        if 0 <= y < curses.LINES and 0 <= x < curses.COLS and len(str) <= curses.COLS - x:
            try:
                stdscr.addstr(y, x, str, attr)
            except curses.error as e:
                with open("debug_log.txt", "a") as debug_file:
                    debug_file.write(f"Error in safe_addstr at ({y}, {x}): {e}\n")

def get_lxc_column(column_name):
    try:
        with subprocess.Popen(["lxc-ls", "--fancy", f"--fancy-format={column_name}"],
                              stdout=subprocess.PIPE, text=True, encoding='utf-8') as proc:
            return [line.strip() for line in proc.stdout if line.strip()][1:]  
    except subprocess.CalledProcessError as e:
        with open("debug_log.txt", "a") as debug_file:
            debug_file.write(f"Error in get_lxc_column for column {column_name}: {e}\n")
        return []

def get_lxc_info(include_stopped=False):
    try:
        names = get_lxc_column("NAME")
        states = get_lxc_column("STATE")
        ipv4s = get_lxc_column("IPV4")
        ipv6s = get_lxc_column("IPV6")
        unprivilegeds = get_lxc_column("UNPRIVILEGED")

        lxc_info = []

        for idx in range(len(names)):
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

            # Read hostname from config file
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
        with open("debug_log.txt", "a") as debug_file:
            debug_file.write(f"Error getting LXC info: {e}\n")
        return []

def get_lxc_config(lxc_id):
    config_file = f"/etc/pve/lxc/{lxc_id}.conf"
    config_info = {}
    if os.path.exists(config_file):
        with open(config_file) as conf_file:
            config_info = dict(line.strip().split(":", 1) for line in conf_file if ":" in line)
    return config_info

def show_panel(stdscr, lines, color_pair):
    try:
        panel_height = len(lines) + 4
        panel_width = max(len(line) for line in lines) + 4

        # Ensure panel fits within screen
        if panel_width > curses.COLS or panel_height > curses.LINES:
            panel_width = min(panel_width, curses.COLS - 4)
            panel_height = min(panel_height, curses.LINES - 4)

        start_y = max(0, (curses.LINES - panel_height) // 2)
        start_x = max(0, (curses.COLS - panel_width) // 2)

        stdscr.attron(color_pair)
        safe_addstr(stdscr, start_y, start_x, f'┌{"─" * (panel_width - 2)}┐')
        for y in range(1, panel_height - 1):
            safe_addstr(stdscr, start_y + y, start_x, f'│{" " * (panel_width - 2)}│')
        safe_addstr(stdscr, start_y + panel_height - 1, start_x, f'└{"─" * (panel_width - 2)}┘')
        stdscr.attroff(color_pair)

        for idx, line in enumerate(lines):
            if start_y + 1 + idx < curses.LINES and start_x + 2 < curses.COLS:
                safe_addstr(stdscr, start_y + 1 + idx, start_x + 2, line[:curses.COLS - start_x - 2])

        stdscr.refresh()
    except curses.error as e:
        with open("debug_log.txt", "a") as debug_file:
            debug_file.write(f"Error in show_panel: {e}, LINES={curses.LINES}, COLS={curses.COLS}, panel_width={panel_width}, panel_height={panel_height}\n")

def show_help(stdscr, show_stopped):
    help_lines = [
        "Help Menu",
        "",
        "Available Commands:",
        "  - Up/Down arrows: Navigate the list",
        "  - Enter/Space: Attach to the selected LXC container",
        "  - i: Show detailed container info",
        "  - x: Stop the selected running container",
        "  - r: Restart the selected container",
        f"  - s: {'Show' if not show_stopped else 'Hide'} Stopped containers",
        "  - q: Quit the TUI",
        "  - h: Show this help window",
        "",
        "Press any key to return..."
    ]
    show_panel(stdscr, help_lines, curses.color_pair(4))

def show_info(stdscr, lxc_id):
    config_info = get_lxc_config(lxc_id)

    info_lines = [
        f"LXC Information (ID: {lxc_id})",
        f"{'Property':<20}{'Value':<30}",
        "-" * 50
    ]

    for key, value in config_info.items():
        info_lines.append(f"{key.capitalize():<20}{value:<30}")

    show_panel(stdscr, info_lines, curses.color_pair(4))

def animate_indicator(stdscr, operation_done_event):
    indicator_chars = ['|', '/', '-', '\\']
    i = 0
    while not operation_done_event.is_set():
        with screen_lock:
            safe_addstr(stdscr, curses.LINES - 2, 0, indicator_chars[i % len(indicator_chars)], curses.A_BOLD)
            stdscr.refresh()
        i += 1
        time.sleep(0.05)

def refresh_lxc_info(refresh_event, stop_event):
    global lxc_info, show_stopped
    lxc_info_set = set()
    while not stop_event.is_set():
        new_lxc_info = get_lxc_info(show_stopped)
        if new_lxc_info != lxc_info:
            lxc_info = new_lxc_info
            lxc_info_set = set(lxc_info)
            with screen_lock:
                refresh_event.set()
        time.sleep(0.5)  # Refresh interval

def main(stdscr):
    if curses.LINES < 10 or curses.COLS < 80:  # Adjust thresholds as needed
        safe_addstr(stdscr, 0, 0, "Terminal too small. Please enlarge the terminal.")
        stdscr.refresh()
        stdscr.getch()
        return

    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(100)

    global show_stopped, lxc_info
    show_stopped = False
    lxc_info = []
    invalid_key_timeout = None
    operation_done_event = threading.Event()
    refresh_event = threading.Event()
    stop_event = threading.Event()

    try:
        lxc_info = get_lxc_info(show_stopped)
    except Exception as e:
        with open("debug_log.txt", "a") as debug_file:
            debug_file.write(f"Error in main: {e}\n")
        safe_addstr(stdscr, 0, 0, f"Error getting LXC info: {e}")
        stdscr.refresh()
        stdscr.getch()
        return

    refresh_thread = threading.Thread(target=refresh_lxc_info, args=(refresh_event, stop_event))
    refresh_thread.start()

    # Adding color pairs
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Green border for help and info panels

    current_row = 0

    def display_navigation_bar():
        show_stopped_label = "Show Stopped" if not show_stopped else "Hide Stopped"
        safe_addstr(stdscr, curses.LINES - 1, 0, f"Commands: Up/Down - Navigate | Enter/Space - Attach | i - Info | x - Stop | r - Restart | s - {show_stopped_label} | q - Quit | h - Help", curses.A_BOLD)
        stdscr.refresh()

    def display_screen():
        stdscr.clear()
        display_navigation_bar()
        safe_addstr(stdscr, 0, 0, f"{'ID':<5} {'HOSTNAME':<20} {'STATE':<10} {'IP ADDRESSES':<50} {'UNPRIVILEGED'}", curses.A_BOLD)

        for idx, container in enumerate(lxc_info):
            lxc_id, hostname, status, ip_addresses, unprivileged = container
            if idx == current_row:
                stdscr.attron(curses.color_pair(3))
                safe_addstr(stdscr, idx + 1, 0, f"{lxc_id:<5} {hostname:<20} {status:<10} {ip_addresses:<50} {unprivileged}")
                stdscr.attroff(curses.color_pair(3))
            else:
                color = curses.color_pair(1) if status == "RUNNING" else curses.color_pair(2)
                safe_addstr(stdscr, idx + 1, 0, f"{lxc_id:<5} {hostname:<20} {status:<10} {ip_addresses:<50} {unprivileged}", color)

        stdscr.refresh()

    display_screen()

    def periodic_refresh():
        global lxc_info
        while True:
            time.sleep(0.1)  # Refresh interval
            new_lxc_info = get_lxc_info(show_stopped)
            if new_lxc_info != lxc_info:
                lxc_info = new_lxc_info
                display_screen()

    # Starting the periodic refresh in a separate thread
    periodic_refresh_thread = threading.Thread(target=periodic_refresh)
    periodic_refresh_thread.daemon = True
    periodic_refresh_thread.start()

    while True:
        key = stdscr.getch()

        if invalid_key_timeout and time.time() > invalid_key_timeout:
            safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
            invalid_key_timeout = None
            display_screen()

        if key == -1:
            continue

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
            invalid_key_timeout = None
            display_screen()
        elif key == curses.KEY_DOWN and current_row < len(lxc_info) - 1:
            current_row += 1
            invalid_key_timeout = None
            display_screen()
        elif key == curses.KEY_ENTER or key in [10, 13, 32]:  # Enter or Space key
            lxc_id, hostname, status, ip_addresses, unprivileged = lxc_info[current_row]
            if status == "STOPPED":
                safe_addstr(stdscr, curses.LINES - 3, 0, " " * (curses.COLS - 1), curses.color_pair(0))
                safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
                stdscr.attron(curses.color_pair(4))
                safe_addstr(stdscr, curses.LINES - 2, 0, f"{lxc_id} is currently stopped. Start it? (y/n)")
                stdscr.attroff(curses.color_pair(4))
                stdscr.refresh()
                while True:
                    choice = stdscr.getch()
                    if choice in [ord('y'), ord('Y'), ord('n'), ord('N')]:
                        break
                if choice in [ord('y'), ord('Y')]:
                    safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
                    operation_done_event.clear()
                    spinner_thread = threading.Thread(target=animate_indicator, args=(stdscr, operation_done_event))
                    spinner_thread.start()
                    subprocess.run(["lxc-start", "-n", lxc_id])
                    time.sleep(2)
                    refresh_event.set()
                    operation_done_event.set()
                    spinner_thread.join()
                    refresh_event.wait()
                    display_screen()
                safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
                display_screen()
            else:
                stdscr.clear()
                stdscr.refresh()
                subprocess.run(["lxc-attach", "-n", lxc_id])
                refresh_event.set()
                refresh_event.wait()
                display_screen()
        elif key == ord('i'):
            lxc_id = lxc_info[current_row][0]
            safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
            show_info(stdscr, lxc_id)
            display_screen()
        elif key == ord('h'):
            safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
            show_help(stdscr, show_stopped)
            display_screen()
        elif key == ord('s'):
            show_stopped = not show_stopped
            lxc_info = get_lxc_info(show_stopped)
            current_row = 0
            display_screen()
        elif key == ord('x'):
            lxc_id, hostname, status, ip_addresses, unprivileged = lxc_info[current_row]
            if status == "RUNNING":
                safe_addstr(stdscr, curses.LINES - 3, 0, " " * (curses.COLS - 1), curses.color_pair(0))
                safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
                stdscr.attron(curses.color_pair(4))
                safe_addstr(stdscr, curses.LINES - 2, 0, f"{lxc_id} is currently running. Stop it? (y/n)")
                stdscr.attroff(curses.color_pair(4))
                stdscr.refresh()
                while True:
                    choice = stdscr.getch()
                    if choice in [ord('y'), ord('Y'), ord('n'), ord('N')]:
                        break
                if choice in [ord('y'), ord('Y')]:
                    safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
                    operation_done_event.clear()
                    spinner_thread = threading.Thread(target=animate_indicator, args=(stdscr, operation_done_event))
                    spinner_thread.start()
                    subprocess.run(["lxc-stop", "-n", lxc_id])
                    time.sleep(2)
                    refresh_event.set()
                    operation_done_event.set()
                    spinner_thread.join()
                    refresh_event.wait()
                    display_screen()
                safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
                display_screen()
        elif key == ord('r'):
            lxc_id, hostname, status, ip_addresses, unprivileged = lxc_info[current_row]
            safe_addstr(stdscr, curses.LINES - 3, 0, " " * (curses.COLS - 1), curses.color_pair(0))
            safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
            stdscr.attron(curses.color_pair(4))
            safe_addstr(stdscr, curses.LINES - 2, 0, f"Restart {lxc_id}? (y/n)")
            stdscr.attroff(curses.color_pair(4))
            stdscr.refresh()
            while True:
                choice = stdscr.getch()
                if choice in [ord('y'), ord('Y'), ord('n'), ord('N')]:
                    break
            if choice in [ord('y'), ord('Y')]:
                safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
                operation_done_event.clear()
                spinner_thread = threading.Thread(target=animate_indicator, args=(stdscr, operation_done_event))
                spinner_thread.start()
                subprocess.run(["lxc-stop", "-n", lxc_id])
                subprocess.run(["lxc-start", "-n", lxc_id])
                time.sleep(2)
                refresh_event.set()
                operation_done_event.set()
                spinner_thread.join()
                refresh_event.wait()
                display_screen()
            safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
            display_screen()
        elif key == ord('q') or key == 27:  # Esc key
            safe_addstr(stdscr, curses.LINES - 2, 0, "Goodbye!👋", curses.color_pair(4))
            stdscr.refresh()
            stop_event.set()
            refresh_thread.join()
            break
        else:
            safe_addstr(stdscr, curses.LINES - 2, 0, "Invalid Key", curses.color_pair(4))
            stdscr.refresh()
            invalid_key_timeout = time.time() + 3

        if invalid_key_timeout and time.time() > invalid_key_timeout:
            safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
            invalid_key_timeout = None
            display_screen()

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except Exception as e:
        with open("debug_log.txt", "a") as debug_file:
            debug_file.write(f"Error running the TUI: {e}\n")
        print(f"Error running the TUI: {e}")
        input("Press Enter to exit...")