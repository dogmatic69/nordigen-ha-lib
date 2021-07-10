# Nordigen Home Assistant Integration Lib

[![GitHub](https://img.shields.io/github/license/dogmatic69/nordigen-ha-lib)](LICENSE)
[![CodeFactor](https://www.codefactor.io/repository/github/dogmatic69/nordigen-ha-lib/badge)](https://www.codefactor.io/repository/github/dogmatic69/nordigen-ha-lib)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=dogmatic69_nordigen-ha-lib&metric=alert_status)](https://sonarcloud.io/dashboard?id=dogmatic69_nordigen-ha-lib)
[![CI](https://github.com/dogmatic69/nordigen-ha-lib/actions/workflows/master.yaml/badge.svg)](https://github.com/dogmatic69/nordigen-ha-lib/actions/workflows/master.yaml)

Nordigen is a (always*) free banking API that takes advantage of the EU PSD2
regulations. They connect to banks in over 30 countries using real banking
API's (no screen scraping).

This lib uses the generic [Nordigen client lib](https://github.com/dogmatic69/nordigen-python) to
provide all the logic required for the Home Assistant integration.

This lib was created to make unit testing easy whilst following the layout formats
required for HACS to function correctly.