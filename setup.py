import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="EasyEMI",
    version="0.0.1",
    author="Jeremy Chinn",
    author_email="jeremychinn88@gmail.com",
    description="Spectrum analyzer trace grabber and comparison tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rocketsaurus/EasyEMI",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU GPLv3 License",
        "Operating System :: OS Independent",
    ],
)