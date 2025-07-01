"""
setup file for fmatch package
"""

from setuptools import setup, find_packages


VERSION = '0.1.4'
DESCRIPTION = 'Common package for matching runs with provided metadata'
# pylint: disable= line-too-long
LONG_DESCRIPTION = "A package that allows to match metadata and get runs and create csv files with queried metrics"

# Setting up
setup(
    name="fmatch",
    version=VERSION,
    author="sboyapal",
    author_email="sboyapal@redhat.com",
    description=DESCRIPTION,
    long_description_content_type="text/x-rst",
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=["elasticsearch==7.13.0", "elasticsearch-dsl", "pyyaml", "pandas"],
    keywords=["python", "matching", "red hat", "perf-scale", "matcher", "orion"],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
)
