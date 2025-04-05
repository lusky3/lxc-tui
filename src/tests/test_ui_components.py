import pytest
from lxc_tui.ui_components import display_container_list, update_navigation_bar

def test_display_container_list(mocker):
    stdscr = mocker.Mock()
    mocker.patch('curses.LINES', 20)
    mocker.patch('curses.COLS', 80)
    stdscr.getmaxyx.return_value = (20, 80)
    lxc_info = [("101", "test-host", "RUNNING", "192.168.1.1", "true")]

    display_container_list(stdscr, lxc_info, 0)
    stdscr.addstr.assert_called()

def test_update_navigation_bar(mocker):
    stdscr = mocker.Mock()
    mocker.patch('curses.COLS', 100)
    stdscr.instr.return_value = b"old nav"
    update_navigation_bar(stdscr, False, [], force=True)
    stdscr.addstr.assert_called()