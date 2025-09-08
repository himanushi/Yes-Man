"""
Yes-Man音声対話アシスタント セットアップ
"""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="yes-man-assistant",
    version="1.0.0",
    description="Fallout NewVegas Yes-Man風音声対話AIアシスタント",
    author="Yes-Man Development Team",
    packages=find_packages(include=["audio_layer*"]),
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "yes-man-audio=audio_layer.main:main",
            "yes-man-langflow=audio_layer.langflow_client:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
)