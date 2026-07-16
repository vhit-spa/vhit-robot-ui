from glob import glob
from pathlib import Path

from setuptools import find_packages, setup


package_name = "vhit_robot_ui_gateway"

package_root = Path(__file__).parent

web_files = [
    str(path)
    for path in (package_root / "www").glob("*")
    if path.is_file()
]

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        (
            "share/" + package_name,
            ["package.xml"],
        ),
        (
            "share/" + package_name + "/launch",
            glob("launch/*.launch.py"),
        ),
        (
            "share/" + package_name + "/www",
            web_files,
        ),
    ],
    install_requires=[
        "setuptools",
    ],
    zip_safe=True,
    maintainer="riky",
    maintainer_email="riky@example.com",
    description="ROS 2 gateway and web UI for the VHIT robot.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "gateway_node = "
            "vhit_robot_ui_gateway.gateway_node:main",
        ],
    },
)