from setuptools import setup, find_packages

setup(
    name="lxc_tui",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
    entry_points={
        "console_scripts": [
            "lxc-tui = lxc_tui.lxc_tui:main",
        ],
    },
)