from setuptools import setup, find_packages

setup(
    name="mass_client",
    version='0.1',
    packages=find_packages(),
    dependency_links=['https://github.com/mass-project/mass_api_client.git']
)
