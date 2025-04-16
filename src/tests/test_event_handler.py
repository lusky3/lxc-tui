import pytest
from lxc_tui.event_handler import handle_events

def test_handle_events_navigation(mocker):
    stdscr = mocker.Mock()
    stdscr.getch.return_value = 259  # curses.KEY_UP value
    stdscr.getmaxyx.return_value = (20, 80)  # Ensure tuple return
    lxc_info = [("101", "test", "RUNNING", "192.168.1.1", "true")]

    # Mock curses module with predefined attributes
    curses_mock = mocker.MagicMock()
    curses_mock.LINES = 20
    curses_mock.COLS = 80
    curses_mock.color_pair = lambda x: x
    mocker.patch('lxc_tui.ui_components.curses', curses_mock)
    mocker.patch('lxc_tui.core.curses', curses_mock)

    mocker.patch('lxc_tui.ui_components.update_highlighted_row')

    current_row, _, _, _ = handle_events(stdscr, lxc_info, 1, False, mocker.Mock(), mocker.Mock(), mocker.Mock(), [])
    assert current_row == 0