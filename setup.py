import setuptools

setuptools.setup(
    name="diskimage",
    version="0.0.1",
    author="Jarle Thorsen",
    author_email="jarlethorsen@gmail.com",
    url='https://github.com/jarlethorsen/diskimage',
    description="A tool for easy handling of disk-images",
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
