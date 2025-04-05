import curses
import pytest
from lxc_tui.event_handler import handle_events

def test_handle_events_navigation(mocker):
    stdscr = mocker.Mock()
    stdscr.getch.return_value = curses.KEY_UP
    lxc_info = [("101", "test", "RUNNING", "192.168.1.1", "true")]
    mocker.patch('lxc_tui.ui_components.update_highlighted_row')

    current_row, _, _, _ = handle_events(stdscr, lxc_info, 1, False, mocker.Mock(), mocker.Mock(), mocker.Mock(), [])
    assert current_row == 0