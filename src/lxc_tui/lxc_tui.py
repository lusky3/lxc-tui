import curses
import threading
import argparse
import os
import importlib
import time
import logging
from lxc_tui.core import log_debug, Plugin, safe_addstr
from lxc_tui.lxc_utils import get_lxc_info, refresh_lxc_info
from lxc_tui.ui_components import display_container_list, update_navigation_bar
from lxc_tui.event_handler import handle_events

logger = logging.getLogger(__name__)

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
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, Plugin)
                        and obj != Plugin
                    ):
                        plugin_instance = obj()
                        plugins.append(plugin_instance)
                        log_debug(f"Loaded plugin: {module_name}.{attr}")
            except ImportError as e:
                log_debug(f"Failed to load plugin {module_name}: {e}")
    return plugins

def main(stdscr):
    logger.debug("Checking screen size")
    if curses.LINES < 10 or curses.COLS < 80:
        safe_addstr(stdscr, 0, 0, "Terminal too small. Please enlarge the terminal.")
        stdscr.refresh()
        stdscr.getch()
        return

    logger.debug("Setting up curses")
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(10)

    show_stopped = False
    lxc_info = []
    invalid_key_timeout = None
    stop_event = threading.Event()
    pause_event = threading.Event()
    operation_done_event = threading.Event()
    current_row = 0
    operation_in_progress = False
    last_refresh_time = 0

    logger.debug("Getting initial lxc_info")
    try:
        lxc_info = get_lxc_info(show_stopped)
    except Exception as e:
        log_debug(f"Error in main: {e}")
        safe_addstr(stdscr, 0, 0, f"Error getting LXC info: {e}")
        stdscr.refresh()
        stdscr.getch()
        return

    logger.debug("Starting refresh thread")
    refresh_thread = threading.Thread(
        target=refresh_lxc_info, args=(lxc_info, stop_event, pause_event, show_stopped)
    )
    refresh_thread.daemon = True
    refresh_thread.start()

    logger.debug("Initializing colors")
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    logger.debug("Loading plugins")
    plugins = load_plugins()
    logger.debug("Displaying initial container list")
    display_container_list(stdscr, lxc_info, current_row)
    logger.debug("Updating navigation bar")
    update_navigation_bar(stdscr, show_stopped, plugins, force=True)

    last_lxc_info = lxc_info.copy()

    logger.debug("Entering main loop")
    while True:
        logger.debug("Loop iteration start")
        start_time = time.time()
        if invalid_key_timeout and time.time() > invalid_key_timeout:
            logger.debug("Clearing invalid_key_timeout")
            safe_addstr(stdscr, curses.LINES - 2, 0, " " * (curses.COLS - 1), curses.color_pair(0))
            invalid_key_timeout = None

        if not operation_in_progress and not pause_event.is_set():
            current_time = time.time()
            if current_time - last_refresh_time >= 60.0:
                logger.debug("Calling get_lxc_info")
                try:
                    new_lxc_info = get_lxc_info(show_stopped)
                    if new_lxc_info != last_lxc_info:
                        lxc_info[:] = new_lxc_info
                        last_lxc_info = lxc_info.copy()
                        display_container_list(stdscr, lxc_info, current_row)
                        update_navigation_bar(stdscr, show_stopped, plugins)
                except Exception as e:
                    log_debug(f"get_lxc_info in loop failed: {e}")
                last_refresh_time = current_time

        logger.debug("Calling handle_events")
        current_row, show_stopped, should_quit, invalid_key_timeout, operation_in_progress = handle_events(
            stdscr, lxc_info, current_row, show_stopped, pause_event, stop_event, operation_done_event, plugins
        )
        logger.debug(f"should_quit: {should_quit}, operation_in_progress: {operation_in_progress}")

        if operation_in_progress and operation_done_event.is_set():
            logger.debug("Operation completed, updating UI")
            try:
                lxc_info[:] = get_lxc_info(show_stopped)
                last_lxc_info = lxc_info.copy()
                display_container_list(stdscr, lxc_info, current_row)
                update_navigation_bar(stdscr, show_stopped, plugins)
            except Exception as e:
                log_debug(f"Post-operation get_lxc_info failed: {e}")
            operation_in_progress = False

        if should_quit:
            logger.debug("Stopping thread")
            stop_event.set()
            logger.debug("Joining thread")
            refresh_thread.join()
            logger.debug("Breaking loop")
            break
        logger.debug(f"Loop iteration took {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    # Configure logging to file and console
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("/root/git/lxc-tui/debug_log.txt"),
            logging.StreamHandler()  # Output to console
        ]
    )
    parser = argparse.ArgumentParser(description="LXC TUI")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    import lxc_tui.core

    lxc_tui.core.DEBUG = args.debug
    logger.debug(f"Debugging started with --debug={args.debug}")

    try:
        curses.wrapper(main)
    except Exception as e:
        logger.error(f"Error running the TUI: {e}")
        print(f"Error running the TUI: {e}")
        input("Press Enter to exit...")