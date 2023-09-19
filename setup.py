#!/usr/bin/env python
"""Setup.py for SageWorks: Sagemaker Workbench"""

import os
import glob
from setuptools import setup, find_packages

readme = open("Readme.md").read()

# Requirements
path = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(path, "requirements.txt")) as f:
    install_requires = f.read().strip().split("\n")


# Data and Example Files
def get_files(dir_name):
    """Simple directory walker"""
    return [(os.path.join(".", d), [os.path.join(d, f) for f in files]) for d, _, files in os.walk(dir_name)]


setup(
    name="sageworks",
    # use_scm_version=True,
    version="0.1.8",
    description="SageWorks: A Python WorkBench for creating and deploying SageMaker Models",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="SuperCowPowers LLC",
    author_email="support@supercowpowers.com",
    url="https://github.com/SuperCowPowers/sageworks",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[os.path.splitext(os.path.basename(path))[0] for path in glob.glob("src/*.py")],
    include_package_data=True,
    data_files=get_files("data") + get_files("examples"),
    install_requires=install_requires,
    license="MIT",
    keywords="SageMaker, Machine Learning, AWS, Python, Utilities",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    setup_requires=["setuptools_scm", "setuptools"],
    entry_points={
        "console_scripts": [
            "sageworks = sageworks.cli.cli:cli",
        ],
    },
)
