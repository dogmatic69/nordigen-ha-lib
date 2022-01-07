# Nordigen Home Assistant Integration Lib

[![GitHub](https://img.shields.io/github/license/dogmatic69/nordigen-ha-lib)](LICENSE.txt)
[![CodeFactor](https://www.codefactor.io/repository/github/dogmatic69/nordigen-ha-lib/badge)](https://www.codefactor.io/repository/github/dogmatic69/nordigen-ha-lib)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=alert_status)](https://sonarcloud.io/dashboard?id=dogmatic69_nordigen-ha-lib)
[![CI](https://github.com/dogmatic69/nordigen-ha-lib/actions/workflows/ci.yaml/badge.svg)](https://github.com/dogmatic69/nordigen-ha-lib/actions/workflows/ci.yaml)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=coverage)](https://sonarcloud.io/summary/new_code?id=dogmatic69_nordigen-ha-lib)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=dogmatic69_nordigen-ha-lib)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=dogmatic69_nordigen-ha-lib)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=dogmatic69_nordigen-ha-lib)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=dogmatic69_nordigen-ha-lib)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=bugs)](https://sonarcloud.io/summary/new_code?id=dogmatic69_nordigen-ha-lib)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=dogmatic69_nordigen-ha-lib)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=dogmatic69_nordigen-ha-lib)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=dogmatic69_nordigen-ha-lib)
[![PyPi](https://img.shields.io/pypi/v/nordigen-ha-lib.svg)](https://pypi.python.org/pypi/nordigen-ha-lib/)
[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)

Nordigen is a (always*) free banking API that takes advantage of the EU PSD2
regulations. They connect to banks in over 30 countries using real banking
API's (no screen scraping).

This lib uses the generic [Nordigen client lib](https://github.com/dogmatic69/nordigen-python) to
provide all the logic required for the Home Assistant integration.

This lib was created to make unit testing easy whilst following the layout formats
required for HACS to function correctly.