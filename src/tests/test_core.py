import pytest
from lxc_tui.core import safe_addstr, log_debug, DEBUG

def test_safe_addstr(mocker):
    # Mock stdscr
    stdscr = mocker.Mock()
    stdscr.addstr = mocker.Mock()

    # Mock curses module with predefined attributes
    curses_mock = mocker.MagicMock()
    curses_mock.LINES = 10
    curses_mock.COLS = 10
    mocker.patch('lxc_tui.core.curses', curses_mock)

    # Test within bounds
    safe_addstr(stdscr, 0, 0, "test", 0)
    stdscr.addstr.assert_called_once_with(0, 0, "test", 0)

    # Test out of bounds
    stdscr.reset_mock()
    safe_addstr(stdscr, 20, 20, "test", 0)
    stdscr.addstr.assert_not_called()

def test_log_debug(mocker):
    mock_open = mocker.patch('builtins.open', mocker.mock_open())
    mocker.patch('lxc_tui.core.DEBUG', True)

    log_debug("Test message")
    mock_open.assert_called_once_with("debug_log.txt", "a")
    mock_open().write.assert_called_once()