from pathlib import Path

from setuptools import find_packages, setup


package_name = "vhit_robot_ui_gateway"


def collect_directory_files(
    source_root: Path,
    install_root: Path,
) -> list[tuple[str, list[str]]]:
    data_files = []

    if not source_root.exists():
        return data_files

    directories = [source_root]
    directories.extend(
        path
        for path in source_root.rglob("*")
        if path.is_dir()
    )

    for directory in directories:
        files = [
            str(path)
            for path in sorted(directory.iterdir())
            if path.is_file()
        ]

        if not files:
            continue

        relative_directory = directory.relative_to(source_root)
        destination = install_root / relative_directory

        data_files.append(
            (
                str(destination),
                files,
            )
        )

    return data_files


web_data_files = collect_directory_files(
    Path("www"),
    Path("share") / package_name / "www",
)

launch_files = [
    str(path)
    for path in sorted(
        Path("launch").glob("*.launch.py")
    )
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
            launch_files,
        ),
        *web_data_files,
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="riky",
    maintainer_email="riky@example.com",
    description="ROS 2 gateway and web UI for the VHIT robot.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "gateway_node = "
            "vhit_robot_ui_gateway.gateway_node:main",
        ],
    },
)