import os
import subprocess
from setuptools import setup, find_packages

setup(
    name="mass_client",
    version=subprocess.check_output(['git', 'describe', '--always'], cwd=os.path.dirname(os.path.abspath(__file__))).strip().decode('utf-8'),
    packages=find_packages(),
    install_requires=[
        'requests>=2.11.1',
        'common-helper-encoder==0.1',
    ],
    dependency_links=['git+ssh://git@github.com/mass-project/common_helper_encoder.git#egg=common_helper_encoder-0.1']
)
