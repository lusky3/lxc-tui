import threading
import curses
import time

screen_lock = threading.Lock()
DEBUG = False

def log_debug(message):
    if DEBUG:
        with open("debug_log.txt", "a") as debug_file:
            debug_file.write(f"{time.ctime()}: {message}\n")

def safe_addstr(stdscr, y, x, text, attr=0):
    with screen_lock:
        log_debug(f"Acquiring screen_lock for safe_addstr at ({y}, {x})")
        if 0 <= y < curses.LINES and 0 <= x < curses.COLS:
            max_len = curses.COLS - x
            if len(text) > max_len:
                text = text[:max_len]
            try:
                stdscr.addstr(y, x, text, attr)
            except curses.error as e:
                log_debug(f"Error in safe_addstr at ({y}, {x}): {e}")
        log_debug(f"Releasing screen_lock for safe_addstr at ({y}, {x})")

class Plugin:
    """Base class for plugins to define their behavior."""
    def __init__(self):
        self.key = None
        self.description = ""

    def execute(self, stdscr, lxc_info, current_row, show_stopped, pause_event, operation_done_event):
        raise NotImplementedError("Plugin must implement execute method")