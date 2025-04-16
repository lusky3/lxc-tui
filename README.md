# LXC TUI

A Text User Interface (TUI) for managing LXC (Linux Containers) containers, written in Python using the `curses` library. This tool allows you to list, start, stop, restart, and attach to LXC containers, as well as view detailed information and toggle the display of stopped containers.

## Features

- List all running and stopped LXC containers with their IDs, hostnames, states, IP addresses, and privilege levels.
- Navigate the container list using arrow keys.
- Attach to a running container, start containers, stop containers, or restart containers.
- View detailed configuration information for a selected container.

## Prerequisites

- Python 3.6 or later
- `curses` library (included with Python on most Unix-like systems)
- LXC tools (`lxc-ls`, `lxc-start`, `lxc-stop`, `lxc-attach`, etc) installed on your system
- Access to LXC configuration files (e.g., `/etc/pve/lxc/`)

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/lusky3/lxc-tui.git
   cd lxc-tui
   ```

   or

   Download the latest release from the [Releases](https://github.com/lusky3/lxc-tui/releases) page.

   or

   Download the script directly from the [repo](https://github.com/lusky3/lxc-tui/blob/master/lxc_tui.py).

2. No additional Python packages are required, but for testing and development, you can install dependencies:

   ```bash
   pip install pytest mock flake8
   ```

## Usage

Run the TUI script:

```bash
python src/lxc_tui.py [--debug]
```

### Controls

- **Up/Down Arrows**: Navigate the list of containers.
- **Enter/Space**: Attach to the selected LXC container (if running) or prompt to start it (if stopped).
- **i**: Show detailed information about the selected container.
- **x**: Stop the selected running container (with confirmation).
- **r**: Restart the selected container (with confirmation).
- **s**: Toggle showing/hiding stopped containers.
- **h**: Display the help menu.
- **q/Esc**: Quit the TUI.

## Testing

This project includes automated tests that run on GitHub Actions. To run tests locally:

1. Navigate to the `tests/` directory.
2. Run:

   ```bash
   pytest tests/ -v
   ```

Linting can be performed with:

```bash
flake8 src/ tests/ --max-line-length=100 --extend-ignore=E501
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and ensure tests pass.
4. Submit a pull request with a clear description of your changes.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/lusky3/lxc-tui/blob/master/LICENSE) file for details.

## Acknowledgments

- Thanks to the Python `curses` library (and LXC community at large).
