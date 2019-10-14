import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent

README = (HERE / "README.md").read_text()

setup(
    name="cloudwatch-metrics-buffer",
    version="0.1.0",
    description="Library for posting metrics to AWS CloudWatch",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/kecabojan/cloudwatch-metrics-buffer",
    author="Bojan Keca",
    author_email="kecabojan@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=find_packages(exclude=("tests",)),
    install_requires=["boto3", 'botocore'],
)