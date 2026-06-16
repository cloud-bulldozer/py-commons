"""
setup file for py-commons package
"""

from setuptools import setup, find_namespace_packages


VERSION = '0.3.0'
DESCRIPTION = 'Common Python libraries for Red Hat tools and automation'
LONG_DESCRIPTION = """
py-commons is a collection of shared Python libraries for Red Hat tools and automation.

Current libraries:
- commons.jira: Unified JIRA client for Atlassian Cloud and on-premise instances with retry logic and common query patterns
"""

# Setting up
setup(
    name="py-commons",
    version=VERSION,
    author="Red Hat Performance and Scale",
    author_email="jtaleric@redhat.com",
    description=DESCRIPTION,
    long_description_content_type="text/plain",
    long_description=LONG_DESCRIPTION,
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "jira>=3.0.0",
        "openai>=1.0.0",
        "langchain-core>=1.3.0",
        "httpx>=0.27.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-cov>=4.1.0",
            "pytest-random-order>=1.1.0",
            "pylint>=3.0.3",
        ],
    },
    keywords=["python", "jira", "red hat", "automation", "atlassian"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
)
