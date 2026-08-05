"""Setup configuration for RealAI."""

from setuptools import find_packages, setup


setup(
    packages=find_packages(exclude=["tests", "tests.*"]),
    py_modules=["api_server", "local_models", "main"],
    include_package_data=True,
    package_data={"realai": ["models/*.json"]},
)
