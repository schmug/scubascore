"""Setup configuration for SCuBA Scoring Kit."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="scubascore",
    version="1.0.0",
    author="SCuBA Team",
    author_email="scuba@example.com",
    description="Security Configuration Benchmarking and Analysis for Google Workspace",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/scubascore",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "scubascore=scubascore.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "scubascore": ["*.yaml"],
    },
)