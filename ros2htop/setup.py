# Copyright (c) 2026 yiannis88.
#
# Licensed under the MIT License.

import os

from setuptools import find_packages, setup


package_name = 'ros2htop'


def generate_data_files(share_p: str, dir_: str) -> list:
    """Iterate through all files and subdirs."""
    data_files = []

    for path, _, files in os.walk(dir_):
        _entry = (share_p + path, [os.path.join(path, f) for f in files if not f.startswith('.')])
        data_files.append(_entry)

    return data_files


setup(
    name=package_name,
    version='0.0.2',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml'])
    ] + generate_data_files('share/' + package_name + '/', 'config'),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yiannis88',
    maintainer_email='selinis.g@gmail.com',
    description='A real-time terminal monitor for ROS 2',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
            'pytest-asyncio',
        ],
    },
    entry_points={
        'console_scripts': [
            'ros2htop_node = ros2htop.nodes.ros2htop_node:main',
        ],
    },
)
