import pytest
from lxc_tui.core import safe_addstr, log_debug, DEBUG

def test_safe_addstr(mocker):
    stdscr = mocker.Mock()
    stdscr.addstr = mocker.Mock()

    safe_addstr(stdscr, 0, 0, "test", 0)
    stdscr.addstr.assert_called_once_with(0, 0, "test", 0)

    stdscr.reset_mock()
    mocker.patch('lxc_tui.core.curses.LINES', 10)
    mocker.patch('lxc_tui.core.curses.COLS', 10)
    safe_addstr(stdscr, 20, 20, "test", 0)
    stdscr.addstr.assert_not_called()

def test_log_debug(mocker):
    mock_open = mocker.patch('builtins.open', mocker.mock_open())
    mocker.patch('lxc_tui.core.DEBUG', True)

    log_debug("Test message")
    mock_open.assert_called_once_with("debug_log.txt", "a")
    mock_open().write.assert_called_once()