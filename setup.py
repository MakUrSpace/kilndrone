from setuptools import setup


# read the contents of README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='kilndrone',
    version='0.0.1',
    author='MakUrSpace, LLC',
    author_email='hello@makurspace.com',
    description='Automated Kilner',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/makurspace/kilndrone',
    install_requires=[],
    packages=["kilndrone", "kilnui"],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
