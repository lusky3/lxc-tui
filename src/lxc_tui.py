import curses
import threading
import argparse
import os
import importlib
import time  # Added for time.time()
from .core import log_debug, DEBUG, Plugin, safe_addstr  # Adjusted to relative import
from .lxc_utils import get_lxc_info, refresh_lxc_info
from .ui_components import display_container_list, update_navigation_bar
from .event_handler import handle_events

def load_plugins():
    plugins = []
    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)
    for filename in os.listdir(plugin_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"lxc_tui.plugins.{module_name}")
                for attr in dir(module):
                    obj = getattr(module, attr)
                    if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                        plugin_instance = obj()
                        plugins.append(plugin_instance)
                        log_debug(f"Loaded plugin: {module_name}.{attr}")
            except ImportError as e:
                log_debug(f"Failed to load plugin {module_name}: {e}")
    return plugins

def main(stdscr):
    if curses.LINES < 10 or curses.COLS < 80:
        safe_addstr(stdscr, 0, 0, "Terminal too small. Please enlarge the terminal.")
        stdscr.refresh()
        stdscr.getch()
        return

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)

    show_stopped = False
    lxc_info = []
    invalid_key_timeout = None
    stop_event = threading.Event()
    pause_event = threading.Event()
    operation_done_event = threading.Event()
    current_row = 0

    try:
        lxc_info = get_lxc_info(show_stopped)
    except Exception as e:
        log_debug(f"Error in main: {e}")
        safe_addstr(stdscr, 0, 0, f"Error getting LXC info: {e}")
        stdscr.refresh()
        stdscr.getch()
        return

    refresh_thread = threading.Thread(target=refresh_lxc_info, args=(lxc_info, stop_event, pause_event, show_stopped))
    refresh_thread.daemon = True
    refresh_thread.start()

    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)

    plugins = load_plugins()
    display_container_list(stdscr, lxc_info, current_row)
    update_navigation_bar(stdscr, show_stopped, plugins, force=True)

    last_lxc_info = lxc_info.copy()

    while True:
        if invalid_key_timeout and time.time() > invalid_key_timeout:
            safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
            invalid_key_timeout = None

        new_lxc_info = get_lxc_info(show_stopped)
        if new_lxc_info != last_lxc_info:
            lxc_info[:] = new_lxc_info
            last_lxc_info = lxc_info.copy()
            display_container_list(stdscr, lxc_info, current_row)

        current_row, show_stopped, should_quit, invalid_key_timeout = handle_events(
            stdscr, lxc_info, current_row, show_stopped, pause_event, stop_event, operation_done_event, plugins
        )

        if should_quit:
            refresh_thread.join()
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LXC TUI")
    parser.add_argument('--debug', action='store_true', help="Enable debug logging")
    args = parser.parse_args()
    DEBUG = args.debug

    if DEBUG:
        with open("debug_log.txt", "w") as debug_file:
            debug_file.write(f"Debugging started at {time.ctime()}\n")

    try:
        curses.wrapper(main)
    except Exception as e:
        log_debug(f"Error running the TUI: {e}")
        print(f"Error running the TUI: {e}")
        input("Press Enter to exit...")