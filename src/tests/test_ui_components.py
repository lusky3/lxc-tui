import pytest
from lxc_tui.ui_components import display_container_list, update_navigation_bar

def test_display_container_list(mocker):
    stdscr = mocker.Mock()
    stdscr.getmaxyx.return_value = (20, 80)  # Mock getmaxyx to return tuple
    stdscr.addstr = mocker.Mock()

    # Mock curses module with predefined attributes
    curses_mock = mocker.MagicMock()
    curses_mock.LINES = 20
    curses_mock.COLS = 80
    curses_mock.color_pair = lambda x: x
    mocker.patch('lxc_tui.ui_components.curses', curses_mock)
    mocker.patch('lxc_tui.core.curses', curses_mock)

    lxc_info = [("101", "test-host", "RUNNING", "192.168.1.1", "true")]
    display_container_list(stdscr, lxc_info, 0)
    stdscr.addstr.assert_called()

def test_update_navigation_bar(mocker):
    stdscr = mocker.Mock()
    stdscr.instr.return_value = b"old nav"
    stdscr.addstr = mocker.Mock()

    # Mock curses module with predefined attributes
    curses_mock = mocker.MagicMock()
    curses_mock.LINES = 20
    curses_mock.COLS = 100
    mocker.patch('lxc_tui.ui_components.curses', curses_mock)
    mocker.patch('lxc_tui.core.curses', curses_mock)

    update_navigation_bar(stdscr, False, [], force=True)
    stdscr.addstr.assert_called()