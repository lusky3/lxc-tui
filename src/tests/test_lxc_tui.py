import pytest
import logging
from lxc_tui.lxc_tui import main, load_plugins

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_load_plugins(mocker):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.listdir', return_value=["__init__.py"])
    mocker.patch('importlib.import_module')

    plugins = load_plugins()
    assert plugins == []

def test_main_initialization(mocker):
    stdscr = mocker.Mock()
    stdscr.getmaxyx.return_value = (20, 80)
    stdscr.getch.return_value = -1
    stdscr.nodelay = mocker.Mock(return_value=None)
    stdscr.timeout = mocker.Mock(return_value=None)
    
    # Mock curses module with minimal attributes
    curses_mock = mocker.MagicMock()
    curses_mock.LINES = 20
    curses_mock.COLS = 80
    curses_mock.color_pair = lambda x: x
    curses_mock.init_pair = lambda *args: None
    curses_mock.start_color = lambda: None
    curses_mock.curs_set = lambda x: None
    curses_mock.wrapper = lambda func: func(stdscr)
    
    mocker.patch('lxc_tui.lxc_tui.curses', curses_mock)
    mocker.patch('lxc_tui.core.curses', curses_mock)
    mocker.patch('lxc_tui.ui_components.curses', curses_mock)
    mocker.patch('lxc_tui.lxc_utils.curses', curses_mock)
    mocker.patch('lxc_tui.event_handler.curses', curses_mock)

    # Mock threading.Thread with explicit behavior
    thread_mock = mocker.Mock()
    thread_mock.start = mocker.Mock(return_value=None)
    thread_mock.join = mocker.Mock(return_value=None)
    thread_mock.daemon = True
    mocker.patch('threading.Thread', return_value=thread_mock)

    # Mock dependencies
    mocker.patch('lxc_tui.lxc_utils.get_lxc_info', return_value=[])
    mocker.patch('lxc_tui.ui_components.display_container_list', return_value=None)
    mocker.patch('lxc_tui.ui_components.update_navigation_bar', return_value=None)
    
    # Mock handle_events in the lxc_tui.lxc_tui namespace
    handle_events_mock = mocker.patch('lxc_tui.lxc_tui.handle_events')
    handle_events_mock.return_value = (0, False, True, None)
    handle_events_mock.side_effect = lambda *args, **kwargs: (
        logger.debug("Mocked handle_events called"),
        (0, False, True, None)
    )[1]

    mocker.patch('time.time', return_value=0)

    logger.debug("Starting main")
    try:
        main(stdscr)
        logger.debug("Main completed successfully")
    except Exception as e:
        logger.debug(f"Main raised exception: {e}", exc_info=True)
        pytest.fail(f"Main failed with exception: {e}")

    logger.debug("Test assertions starting")
    stdscr.nodelay.assert_called_with(True)
    thread_mock.start.assert_called_once()
    thread_mock.join.assert_called_once()
    handle_events_mock.assert_called()  # Ensure mock was called