import curses
import subprocess
import threading
import time
from lxc_tui.core import safe_addstr, log_debug, screen_lock
from lxc_tui.lxc_utils import execute_lxc_command, get_lxc_info
from lxc_tui.ui_components import (
    display_container_list,
    update_navigation_bar,
    update_highlighted_row,
    show_info,
    show_help,
    animate_indicator,
)

def handle_events(
    stdscr,
    lxc_info,
    current_row,
    show_stopped,
    pause_event,
    stop_event,
    operation_done_event,
    plugins,
):
    key = stdscr.getch()
    invalid_key_timeout = None
    key_map = {plugin.key: plugin for plugin in plugins}

    if key == curses.KEY_RESIZE:
        lines, cols = stdscr.getmaxyx()
        curses.resize_term(lines, cols)
        log_debug(
            f"Terminal resized via KEY_RESIZE to: LINES={curses.LINES}, COLS={curses.COLS}"
        )
        display_container_list(stdscr, lxc_info, current_row)
        update_navigation_bar(stdscr, show_stopped, plugins, force=True)
        return current_row, show_stopped, False, invalid_key_timeout

    if key == -1:
        return current_row, show_stopped, False, invalid_key_timeout

    pause_event.set()
    if key == curses.KEY_UP and current_row > 0:
        old_row = current_row
        current_row -= 1
        update_highlighted_row(stdscr, old_row, current_row, lxc_info)
    elif key == curses.KEY_DOWN and current_row < len(lxc_info) - 1:
        old_row = current_row
        current_row += 1
        update_highlighted_row(stdscr, old_row, current_row, lxc_info)
    elif key == curses.KEY_ENTER or key in [10, 13, 32]:
        if current_row < len(lxc_info):
            lxc_id, hostname, status, ip_addresses, unprivileged = lxc_info[current_row]
            if status == "STOPPED":
                safe_addstr(
                    stdscr,
                    curses.LINES - 3,
                    0,
                    " " * (curses.COLS - 1),
                    curses.color_pair(0),
                )
                safe_addstr(
                    stdscr,
                    curses.LINES - 2,
                    0,
                    " " * (curses.COLS - 1),
                    curses.color_pair(0),
                )
                stdscr.attron(curses.color_pair(4))
                safe_addstr(
                    stdscr,
                    curses.LINES - 2,
                    0,
                    f"{lxc_id} is currently stopped. Start and attach? (y/n)",
                )
                stdscr.attroff(curses.color_pair(4))
                stdscr.refresh()
                stdscr.nodelay(False)
                while True:
                    choice = stdscr.getch()
                    if choice in [ord("y"), ord("Y"), ord("n"), ord("N")]:
                        break
                stdscr.nodelay(True)
                if choice in [ord("y"), ord("Y")]:
                    safe_addstr(
                        stdscr,
                        curses.LINES - 2,
                        0,
                        " " * (curses.COLS - 1),
                        curses.color_pair(0),
                    )
                    operation_done_event.clear()
                    spinner_thread = threading.Thread(
                        target=animate_indicator, args=(stdscr, operation_done_event)
                    )
                    spinner_thread.start()
                    if execute_lxc_command(
                        stdscr, ["lxc-start", "-n", lxc_id], operation_done_event
                    ):
                        time.sleep(2)
                        log_debug(f"Attaching to container {lxc_id}")
                        subprocess.run(
                            ["xterm", "-e", "lxc-attach", "-n", lxc_id], check=False
                        )
                        lxc_info[:] = get_lxc_info(show_stopped)
                        display_container_list(stdscr, lxc_info, current_row)
                    operation_done_event.set()
                    spinner_thread.join()
                else:
                    display_container_list(stdscr, lxc_info, current_row)
            else:
                stdscr.clear()
                stdscr.refresh()
                log_debug(f"Attaching to running container {lxc_id}")
                subprocess.run(["lxc-attach", "-n", lxc_id])
                display_container_list(stdscr, lxc_info, current_row)
        update_navigation_bar(stdscr, show_stopped, plugins)
    elif key == ord("s"):
        show_stopped = not show_stopped
        lxc_info[:] = get_lxc_info(show_stopped)
        current_row = 0
        display_container_list(stdscr, lxc_info, current_row)
        update_navigation_bar(stdscr, show_stopped, plugins, force=True)
    elif key == ord("q") or key == 27:
        safe_addstr(stdscr, curses.LINES - 2, 0, "Goodbye!👋", curses.color_pair(4))
        stdscr.refresh()
        stop_event.set()
        return current_row, show_stopped, True, invalid_key_timeout
    elif key == ord("x"):
        if current_row < len(lxc_info):
            lxc_id, hostname, status, ip_addresses, unprivileged = lxc_info[current_row]
            safe_addstr(
                stdscr,
                curses.LINES - 2,
                0,
                " " * (curses.COLS - 1),
                curses.color_pair(0),
            )
            if status == "RUNNING":
                safe_addstr(
                    stdscr,
                    curses.LINES - 2,
                    0,
                    f"Stopping container {lxc_id}... (y/n)",
                    curses.color_pair(4),
                )
                stdscr.refresh()
                stdscr.nodelay(False)
                choice = stdscr.getch()
                stdscr.nodelay(True)
                if choice in [ord("y"), ord("Y")]:
                    operation_done_event.clear()
                    spinner_thread = threading.Thread(
                        target=animate_indicator, args=(stdscr, operation_done_event)
                    )
                    spinner_thread.daemon = True
                    spinner_thread.start()

                    # Run lxc command in a separate thread
                    def run_lxc_command():
                        try:
                            success = execute_lxc_command(
                                stdscr, ["lxc-stop", "-n", lxc_id], operation_done_event
                            )
                            with screen_lock:
                                if success:
                                    safe_addstr(
                                        stdscr,
                                        curses.LINES - 2,
                                        0,
                                        f"Stopped {lxc_id}",
                                        curses.color_pair(1),
                                    )
                                else:
                                    safe_addstr(
                                        stdscr,
                                        curses.LINES - 2,
                                        0,
                                        f"Failed to stop {lxc_id}",
                                        curses.color_pair(2),
                                    )
                                stdscr.refresh()
                        finally:
                            operation_done_event.set()

                    lxc_thread = threading.Thread(target=run_lxc_command)
                    lxc_thread.daemon = True
                    lxc_thread.start()
                    lxc_thread.join()  # Wait for command to finish
                    spinner_thread.join()
                    lxc_info[:] = get_lxc_info(show_stopped)
                    display_container_list(stdscr, lxc_info, current_row)
                else:
                    safe_addstr(
                        stdscr,
                        curses.LINES - 2,
                        0,
                        "Action canceled",
                        curses.color_pair(4),
                    )
                    stdscr.refresh()
            elifS = threading.Event()
            safe_addstr(
                stdscr,
                curses.LINES - 2,
                0,
                " " * (curses.COLS - 1),
                curses.color_pair(0),
            )
            if status == "STOPPED":
                safe_addstr(
                    stdscr,
                    curses.LINES - 2,
                    0,
                    f"Starting container {lxc_id}... (y/n)",
                    curses.color_pair(4),
                )
                stdscr.refresh()
                stdscr.nodelay(False)
                choice = stdscr.getch()
                stdscr.nodelay(True)
                if choice in [ord("y"), ord("Y")]:
                    operation_done_event.clear()
                    spinner_thread = threading.Thread(
                        target=animate_indicator, args=(stdscr, operation_done_event)
                    )
                    spinner_thread.daemon = True
                    spinner_thread.start()

                    def run_lxc_command():
                        try:
                            success = execute_lxc_command(
                                stdscr, ["lxc-start", "-n", lxc_id], operation_done_event
                            )
                            with screen_lock:
                                if success:
                                    safe_addstr(
                                        stdscr,
                                        curses.LINES - 2,
                                        0,
                                        f"Started {lxc_id}",
                                        curses.color_pair(1),
                                    )
                                else:
                                    safe_addstr(
                                        stdscr,
                                        curses.LINES - 2,
                                        0,
                                        f"Failed to start {lxc_id}",
                                        curses.color_pair(2),
                                    )
                                stdscr.refresh()
                        finally:
                            operation_done_event.set()

                    lxc_thread = threading.Thread(target=run_lxc_command)
                    lxc_thread.daemon = True
                    lxc_thread.start()
                    lxc_thread.join()
                    spinner_thread.join()
                    lxc_info[:] = get_lxc_info(show_stopped)
                    display_container_list(stdscr, lxc_info, current_row)
                else:
                    safe_addstr(
                        stdscr,
                        curses.LINES - 2,
                        0,
                        "Action canceled",
                        curses.color_pair(4),
                    )
                    stdscr.refresh()
        update_navigation_bar(stdscr, show_stopped, plugins)
    elif key == ord("r"):
        if current_row < len(lxc_info):
            lxc_id, hostname, status, ip_addresses, unprivileged = lxc_info[current_row]
            if status == "RUNNING":
                safe_addstr(
                    stdscr,
                    curses.LINES - 2,
                    0,
                    f"Restarting container {lxc_id}... (y/n)",
                    curses.color_pair(4),
                )
                stdscr.refresh()
                stdscr.nodelay(False)
                choice = stdscr.getch()
                stdscr.nodelay(True)
                if choice in [ord("y"), ord("Y")]:
                    operation_done_event.clear()
                    spinner_thread = threading.Thread(
                        target=animate_indicator, args=(stdscr, operation_done_event)
                    )
                    spinner_thread.daemon = True
                    spinner_thread.start()

                    def run_lxc_command():
                        try:
                            success = (
                                execute_lxc_command(
                                    stdscr,
                                    ["lxc-stop", "-n", lxc_id],
                                    operation_done_event,
                                )
                                and execute_lxc_command(
                                    stdscr,
                                    ["lxc-start", "-n", lxc_id],
                                    operation_done_event,
                                )
                            )
                            with screen_lock:
                                if success:
                                    safe_addstr(
                                        stdscr,
                                        curses.LINES - 2,
                                        0,
                                        f"Restarted {lxc_id}",
                                        curses.color_pair(1),
                                    )
                                else:
                                    safe_addstr(
                                        stdscr,
                                        curses.LINES - 2,
                                        0,
                                        f"Failed to restart {lxc_id}",
                                        curses.color_pair(2),
                                    )
                                stdscr.refresh()
                        finally:
                            operation_done_event.set()

                    lxc_thread = threading.Thread(target=run_lxc_command)
                    lxc_thread.daemon = True
                    lxc_thread.start()
                    lxc_thread.join()
                    spinner_thread.join()
                    lxc_info[:] = get_lxc_info(show_stopped)
                    display_container_list(stdscr, lxc_info, current_row)
                else:
                    safe_addstr(
                        stdscr,
                        curses.LINES - 2,
                        0,
                        "Action canceled",
                        curses.color_pair(4),
                    )
                    stdscr.refresh()
            else:
                safe_addstr(
                    stdscr,
                    curses.LINES - 2,
                    0,
                    f"Container {lxc_id} is not running, cannot restart",
                    curses.color_pair(2),
                )
                stdscr.refresh()
        update_navigation_bar(stdscr, show_stopped, plugins)
    elif key == ord("i"):
        if current_row < len(lxc_info):
            lxc_id = lxc_info[current_row][0]
            show_info(stdscr, lxc_id, pause_event)
            # Removed display_container_list and update_navigation_bar
    elif key == ord("h"):
        show_help(stdscr, show_stopped, pause_event, plugins)
        # Removed display_container_list and update_navigation_bar
    elif key in key_map:
        current_row = key_map[key].execute(
            stdscr,
            lxc_info,
            current_row,
            show_stopped,
            pause_event,
            operation_done_event,
        )
        update_navigation_bar(stdscr, show_stopped, plugins)
    else:
        safe_addstr(stdscr, curses.LINES - 2, 0, "Invalid Key", curses.color_pair(4))
        stdscr.refresh()
        invalid_key_timeout = time.time() + 2

    pause_event.clear()
    return current_row, show_stopped, False, invalid_key_timeout