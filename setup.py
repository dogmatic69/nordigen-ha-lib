#!/usr/bin/env python

import setuptools

application_dependencies = ["homeassistant", "nordigen-python>=0.2.0b5", "voluptuous"]
prod_dependencies = []
test_dependencies = ["pytest", "parameterized", "pytest-env", "pytest-cov", "pytest-asyncio", "vcrpy", "requests-mock"]
lint_dependencies = ["flake8", "flake8-docstrings", "black", "isort"]
docs_dependencies = []
dev_dependencies = test_dependencies + lint_dependencies + docs_dependencies + ["ipdb"]
publish_dependencies = ["requests", "twine"]


with open("README.md", "r") as fh:
    long_description = fh.read()


with open("VERSION", "r") as buf:
    version = buf.read()


setuptools.setup(
    name="nordigen-ha-lib",
    version=version,
    description="Home Assistant lib for integration with Nordigen banking API's using nordigen-python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Carl Sutton (dogmatic69)",
    author_email="dogmatic69@gmail.com",
    license='MIT',
    keywords=['nordigen', 'banking', 'home hassistant', 'hassio'],
    url="https://github.com/dogmatic69/nordigen-ha-lib",
    python_requires=">=3.6",
    packages=["nordigen_lib"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
    ],
    install_requires=application_dependencies,
    extras_require={
        "production": prod_dependencies,
        "test": test_dependencies,
        "lint": lint_dependencies,
        "docs": dev_dependencies,
        "dev": dev_dependencies,
        "publish": publish_dependencies,
    },
    include_package_data=True,
    zip_safe=False,
)