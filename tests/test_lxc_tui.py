import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from unittest.mock import patch, mock_open, MagicMock
import curses
from lxc_tui import (get_lxc_column, get_lxc_info, get_lxc_config, show_panel, show_help, show_info, 
                     animate_indicator, refresh_lxc_info, main, safe_addstr)

class TestLXCTUI(unittest.TestCase):

    def setUp(self):
        # Properly mock curses screen and initialize it
        self.stdscr = MagicMock()
        curses.initscr = lambda: self.stdscr
        curses.endwin = lambda: None
        curses.LINES = 24
        curses.COLS = 80
        curses.start_color = lambda: None
        curses.init_pair = lambda a, b, c: None
        self.stdscr.getch.return_value = -1  # Default return for getch
        self.stdscr.addstr = MagicMock()  # Mock addstr for safe_addstr
        self.stdscr.addch = MagicMock()   # Mock addch for animate_indicator

    @patch('subprocess.Popen')
    def test_get_lxc_column(self, mock_popen):
        # Mock subprocess Popen to return a process with stdout iterable
        mock_process = mock_popen.return_value
        mock_stdout = MagicMock()
        mock_stdout.__iter__.return_value = iter(['header', 'container1', 'container2'])
        mock_process.stdout = mock_stdout
        mock_process.configure_mock(**{'communicate.return_value': (b'', b'')})

        result = get_lxc_column("NAME")
        self.assertEqual(result, ['container1', 'container2'])

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='hostname: test-host\n')
    def test_get_lxc_info(self, mock_file, mock_exists):
        mock_exists.return_value = True
        with patch('lxc_tui.get_lxc_column', side_effect=[
            ['test1', 'test2'],  # NAME
            ['RUNNING', 'STOPPED'],  # STATE
            ['192.168.1.1', '192.168.1.2'],  # IPV4
            ['-', '-'],  # IPV6
            ['yes', 'no']  # UNPRIVILEGED
        ]):
            result = get_lxc_info(include_stopped=True)
            expected = [('test1', 'test-host', 'RUNNING', '192.168.1.1', 'yes'),
                        ('test2', 'test-host', 'STOPPED', '192.168.1.2', 'no')]
            self.assertEqual(result, expected)

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='key: value\n')
    def test_get_lxc_config(self, mock_file, mock_exists):
        mock_exists.return_value = True
        result = get_lxc_config("123")
        self.assertEqual(result, {'key': ' value'})

    @patch('lxc_tui.curses.color_pair')
    def test_show_panel(self, mock_color_pair):
        lines = ["Line1", "Line2"]
        show_panel(self.stdscr, lines, mock_color_pair())
        self.stdscr.addstr.assert_called()

    def test_show_help(self):
        with patch('lxc_tui.show_panel') as mock_show_panel:
            show_help(self.stdscr, show_stopped=False)
            mock_show_panel.assert_called_once_with(self.stdscr, ANY, ANY)

    @patch('threading.Event')
    def test_animate_indicator(self, mock_event):
        event = mock_event()
        event.is_set.return_value = False
        animate_indicator(self.stdscr, event)
        self.stdscr.addch.assert_called()  # Check if addch was called at least once

    @patch('threading.Event')
    def test_refresh_lxc_info(self, mock_event):
        refresh_event = mock_event()
        stop_event = mock_event()
        stop_event.is_set.return_value = False
        with patch('lxc_tui.get_lxc_info', return_value=[('id1', 'host1', 'RUNNING', '', '')]):
            refresh_lxc_info(refresh_event, stop_event)
            refresh_event.set.assert_called()

    @patch('curses.wrapper')
    def test_main(self, mock_wrapper):
        # Mock the entire main function to avoid curses initialization issues
        mock_wrapper.side_effect = lambda func: func(self.stdscr)
        main(self.stdscr)
        self.stdscr.addstr.assert_called()  # Ensure some output was attempted

if __name__ == '__main__':
    unittest.main()