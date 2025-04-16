import pytest
from lxc_tui.lxc_utils import get_lxc_column, get_lxc_info

def test_get_lxc_column(mocker):
    mock_proc = mocker.Mock()
    mock_proc.stdout = ["HEADER\n", "value1\n", "value2\n"]
    mock_proc.wait.return_value = 0
    mocker.patch('subprocess.Popen', return_value=mock_proc)

    result = get_lxc_column("NAME")
    assert result == ["value1", "value2"]

def test_get_lxc_info(mocker):
    mocker.patch('lxc_tui.lxc_utils.get_lxc_column', side_effect=[
        ["container1"], ["RUNNING"], ["192.168.1.1"], ["-"], ["true"]
    ])
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data="hostname: test-host\n"))

    result = get_lxc_info(include_stopped=True)
    assert result == [("container1", "test-host", "RUNNING", "192.168.1.1", "true")]