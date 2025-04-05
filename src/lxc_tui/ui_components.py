import curses
import time
from lxc_tui.core import log_debug, safe_addstr, screen_lock

def display_container_list(stdscr, lxc_info, current_row):
    lines, cols = stdscr.getmaxyx()
    log_debug(f"Checking screen size: LINES={curses.LINES}, COLS={curses.COLS}")

    if curses.LINES < 4 or curses.COLS < 50:
        safe_addstr(stdscr, 0, 0, "Terminal too small. Enlarge to 4 lines, 50 cols.")
        stdscr.refresh()
        log_debug("Screen too small, displaying error message")
        return

    id_width = 5
    hostname_width = 20
    state_width = 10
    unprivileged_width = len("UNPRIVILEGED")
    fixed_width = id_width + hostname_width + state_width + unprivileged_width + 4
    max_ip_width = max(50, curses.COLS - fixed_width - 1)
    max_rows = max(0, curses.LINES - 2)
    visible_containers = lxc_info[:max_rows]

    for i in range(max_rows + 1):
        safe_addstr(stdscr, i, 0, " " * cols)

    safe_addstr(stdscr, 0, 0, f"{'ID':<5} {'HOSTNAME':<20} {'STATE':<10} {'IP ADDRESSES':<50} {'UNPRIVILEGED'}", curses.A_BOLD)

    for idx, container in enumerate(visible_containers):
        lxc_id, hostname, status, ip_addresses, unprivileged = container
        if len(ip_addresses) > max_ip_width:
            ip_addresses = ip_addresses[:max_ip_width - 3] + "..."

        line = f"{lxc_id:<5} {hostname:<20} {status:<10} {ip_addresses:<{max_ip_width}} {unprivileged}"
        if idx == current_row:
            stdscr.attron(curses.color_pair(3))
            safe_addstr(stdscr, idx + 1, 0, line)
            stdscr.attroff(curses.color_pair(3))
        else:
            color = curses.color_pair(1) if status == "RUNNING" else curses.color_pair(2)
            safe_addstr(stdscr, idx + 1, 0, line, color)

    stdscr.refresh()

def update_navigation_bar(stdscr, show_stopped, plugins, force=False):
    base_nav = "Commands: Up/Down - Navigate | Enter/Space - Attach | i - Info | x - Stop/Start | r - Restart | h - Help"
    plugin_nav = " | ".join(f"{chr(plugin.key)} - {plugin.description}" for plugin in plugins if plugin.key not in [ord(' '), ord('i'), ord('x'), ord('r'), ord('h'), ord('s'), ord('q')])
    full_nav = f"{base_nav} | s - {'Show' if not show_stopped else 'Hide'} Stopped | q - Quit" + (f" | {plugin_nav}" if plugin_nav else "")
    short_nav = "Up/Down - Navigate | q - Quit"

    if 80 <= curses.COLS <= 127:
        nav_text = short_nav
    else:
        nav_text = full_nav
        if len(nav_text) > curses.COLS:
            nav_text = nav_text[:curses.COLS - 3] + "..."

    current_nav = stdscr.instr(curses.LINES - 1, 0, curses.COLS).decode('utf-8', errors='ignore').strip()
    if force or current_nav != nav_text:
        safe_addstr(stdscr, curses.LINES - 1, 0, " " * curses.COLS)
        safe_addstr(stdscr, curses.LINES - 1, 0, nav_text, curses.A_BOLD)
        stdscr.refresh()

def update_highlighted_row(stdscr, old_row, new_row, lxc_info):
    lines, cols = stdscr.getmaxyx()
    log_debug(f"Updating highlight: old_row={old_row}, new_row={new_row}, lxc_info length={len(lxc_info)}")

    id_width = 5
    hostname_width = 20
    state_width = 10
    unprivileged_width = len("UNPRIVILEGED")
    fixed_width = id_width + hostname_width + state_width + unprivileged_width + 4
    max_ip_width = max(50, curses.COLS - fixed_width - 1)

    if 0 <= old_row < len(lxc_info):
        lxc_id, hostname, status, ip_addresses, unprivileged = lxc_info[old_row]
        if len(ip_addresses) > max_ip_width:
            ip_addresses = ip_addresses[:max_ip_width - 3] + "..."
        line = f"{lxc_id:<5} {hostname:<20} {status:<10} {ip_addresses:<{max_ip_width}} {unprivileged}"
        color = curses.color_pair(1) if status == "RUNNING" else curses.color_pair(2)
        safe_addstr(stdscr, old_row + 1, 0, line, color)
        log_debug(f"Reset old row {old_row} to color {color}")

    if 0 <= new_row < len(lxc_info):
        lxc_id, hostname, status, ip_addresses, unprivileged = lxc_info[new_row]
        if len(ip_addresses) > max_ip_width:
            ip_addresses = ip_addresses[:max_ip_width - 3] + "..."
        line = f"{lxc_id:<5} {hostname:<20} {status:<10} {ip_addresses:<{max_ip_width}} {unprivileged}"
        stdscr.attron(curses.color_pair(3))
        safe_addstr(stdscr, new_row + 1, 0, line)
        stdscr.attroff(curses.color_pair(3))
        log_debug(f"Highlighted new row {new_row} in white")

    stdscr.refresh()
    log_debug("Highlight update complete")

def show_panel(stdscr, lines, color_pair, pause_event):
    try:
        panel_height = len(lines) + 4
        panel_width = max(len(line) for line in lines) + 4

        if panel_width > curses.COLS or panel_height > curses.LINES:
            panel_width = min(panel_width, curses.COLS - 4)
            panel_height = min(panel_height, curses.LINES - 4)

        start_y = max(0, (curses.LINES - panel_height) // 2)
        start_x = max(0, (curses.COLS - panel_width) // 2)

        pause_event.set()

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

        stdscr.nodelay(False)
        stdscr.getch()
        stdscr.nodelay(True)

    except curses.error as e:
        log_debug(f"Error in show_panel: {e}, LINES={curses.LINES}, COLS={curses.COLS}, panel_width={panel_width}, panel_height={panel_height}")
    finally:
        pause_event.clear()

def show_help(stdscr, show_stopped, pause_event, plugins):
    help_lines = [
        "Help Menu",
        "",
        "Available Commands:",
        "  - Up/Down arrows: Navigate the list",
        "  - Enter/Space: Attach to the selected LXC container",
        "  - i: Show detailed container info",
        "  - x: Stop/Start the selected container",
        "  - r: Restart the selected container",
        f"  - s: {'Show' if not show_stopped else 'Hide'} Stopped containers",
        "  - q: Quit the TUI",
        "  - h: Show this help window",
    ]
    plugin_help = [f"  - {chr(plugin.key)}: {plugin.description}" for plugin in plugins if plugin.key not in [ord(' '), ord('i'), ord('x'), ord('r'), ord('h'), ord('s'), ord('q')]]
    if plugin_help:
        help_lines.append("")
        help_lines.append("Plugins:")
        help_lines.extend(plugin_help)
    help_lines.append("")
    help_lines.append("Press any key to return...")
    show_panel(stdscr, help_lines, curses.color_pair(4), pause_event)

def show_info(stdscr, lxc_id, pause_event):
    from lxc_tui.lxc_utils import get_lxc_config
    config_info = get_lxc_config(lxc_id)

    info_lines = [
        f"LXC Information (ID: {lxc_id})",
        f"{'Property':<20}{'Value':<30}",
        "-" * 50
    ]
    for key, value in config_info.items():
        info_lines.append(f"{key.capitalize():<20}{value:<30}")
    show_panel(stdscr, info_lines, curses.color_pair(4), pause_event)

def animate_indicator(stdscr, operation_done_event):
    indicator_chars = ['|', '/', '-', '\\']
    i = 0
    while not operation_done_event.is_set():
        with screen_lock:
            safe_addstr(stdscr, curses.LINES - 2, 0, indicator_chars[i % len(indicator_chars)], curses.A_BOLD)
            stdscr.refresh()
        i += 1
        time.sleep(0.05)