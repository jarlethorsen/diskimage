import setuptools

# read the contents of README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setuptools.setup(
    name="diskimage",
    version="0.0.1",
    author="Jarle Thorsen",
    author_email="jarlethorsen@gmail.com",
    url='https://github.com/jarlethorsen/diskimage',
    description="A tool for easy handling of disk-images",
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha"
    ],
    entry_points={
        'console_scripts': [
            'di = diskimage.__main__:main'
        ]
        },
        install_requires=[
        'pytsk3>=20210419',
        'libewf-python>=20201230'
    ],
    python_requires='>=3.0'
 )
