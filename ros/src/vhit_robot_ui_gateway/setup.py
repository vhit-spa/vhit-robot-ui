from setuptools import find_packages, setup

package_name = "vhit_robot_ui_gateway"

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
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="riky",
    maintainer_email="riccardo.valtorta@vhit-weifu.com",
    description="ROS 2 gateway for the VHIT ctrlX robot UI.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "gateway_node = "
            "vhit_robot_ui_gateway.gateway_node:main",
        ],
    },
)