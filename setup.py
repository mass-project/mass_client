from mass_client import __version__
from setuptools import setup, find_packages

setup(
    name="mass_client",
    version=__version__,
    packages=find_packages(),
    dependency_links=['https://github.com/mass-project/mass_api_client.git']
)
