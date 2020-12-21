import setuptools
from PhotoCuration import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="PhotoCuration",
    version=__version__,
    author="Avi Alkalay",
    author_email="avibrazil@gmail.com",
    description="Extracts images and videos from iOS Photo Library on iOS backups tagging and renaming along the way",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/avibrazil/PhotoCuration",
    install_requires=['iOSbackup'],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Environment :: MacOS X",
        "Environment :: Console",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Legal Industry",
        "Intended Audience :: Telecommunications Industry",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: MacOS",
        "Operating System :: iOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Topic :: Database",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Embedded Systems",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System :: Recovery Tools"
    ],
    python_requires='>=3.6',
)
