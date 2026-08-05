"""Setup configuration for RealAI."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="realai",
    version="2.0.0",
    author="RealAI Team",
    description="The limitless AI that can truly do anything - from Web3 to groceries, therapy to business building",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Unwrenchable/realai",
    packages=find_packages() + [
        # realai_core packages are not auto-discoverable by find_packages()
        # because they live under realai-core/ (hyphenated) via package_dir
        # aliasing.  They must be listed explicitly.
        'realai_core',
        'realai_core.agents_impl',
        'realai_core.engine',
        'realai_core.providers',
        'realai_core.tooling',
    ],
    package_dir={
        'realai_core':               'realai-core/agent_tools',
        'realai_core.agents_impl':   'realai-core/agent_tools/agents_impl',
        'realai_core.engine':        'realai-core/agent_tools/engine',
        'realai_core.providers':     'realai-core/agent_tools/providers',
        'realai_core.tooling':       'realai-core/agent_tools/tooling',
    },
    py_modules=["api_server", "local_models", "main"],
    include_package_data=True,
    package_data={"realai": ["models/*.json"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12,<4.0",
    entry_points={
        "console_scripts": [
            "realai=realai:main",
            "realai-cli=realai.cli.realai_cli:main",
            "realai-server=realai.server.app:main",
        ],
    },
)
