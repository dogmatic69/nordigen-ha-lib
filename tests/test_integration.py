import unittest
from unittest.mock import MagicMock, call

from nordigen_lib import entry


class TestIntegration(unittest.TestCase):
    @unittest.mock.patch("nordigen_lib.Client")
    def test_new_install(self, mocked_client):
        hass = MagicMock()
        LOGGER = MagicMock()

        clinet_instance = MagicMock()
        mocked_client.return_value = clinet_instance

        config = {
            "foobar": {
                "token": "xxxx",
                "requisitions": [
                    {
                        "aspsp_id": "aspsp_123",
                        "enduser_id": "user_123",
                        "ignore": [],
                    }
                ],
            },
        }
        const = {
            "DOMAIN": "foobar",
            "TOKEN": "token",
            "REQUISITIONS": "requisitions",
            "ASPSP_ID": "aspsp_id",
            "ENDUSER_ID": "enduser_id",
            "IGNORE_ACCOUNTS": "ignore",
        }

        clinet_instance.requisitions.list.return_value = {"results": []}

        clinet_instance.requisitions.create.return_value = {
            "id": "req-123",
            "status": "CR",
        }

        clinet_instance.requisitions.initiate.return_value = {"initiate": "https://example.com/whoohooo"}

        entry(hass=hass, config=config, CONST=const, LOGGER=LOGGER)

        clinet_instance.requisitions.create.assert_called_once()
        clinet_instance.requisitions.initiate.assert_called_once()
        clinet_instance.requisitions.list.assert_called_once()

        clinet_instance.requisitions.initiate.assert_called_with(id="req-123", aspsp_id="aspsp_123")

    @unittest.mock.patch("nordigen_lib.Client")
    def test_existing_install(self, mocked_client):
        hass = MagicMock()
        LOGGER = MagicMock()

        clinet_instance = MagicMock()
        mocked_client.return_value = clinet_instance

        config = {
            "foobar": {
                "token": "xxxx",
                "requisitions": [
                    {
                        "aspsp_id": "aspsp_123",
                        "enduser_id": "user_123",
                        "ignore": [
                            "resourceId-123",
                        ],
                    },
                    {
                        "aspsp_id": "aspsp_321",
                        "enduser_id": "user_321",
                        "ignore": [],
                    },
                ],
            },
        }
        const = {
            "DOMAIN": "foobar",
            "TOKEN": "token",
            "REQUISITIONS": "requisitions",
            "ASPSP_ID": "aspsp_id",
            "ENDUSER_ID": "enduser_id",
            "IGNORE_ACCOUNTS": "ignore",
        }

        clinet_instance.requisitions.list.side_effect = [
            {
                "results": [
                    {
                        "id": "req-123",
                        "status": "LN",
                        "reference": "user_123-aspsp_123",
                        "accounts": [
                            "account-1",
                            "account-2",
                            "account-3",
                        ],
                    },
                    {
                        "id": "req-321",
                        "status": "LN",
                        "reference": "user_321-aspsp_321",
                        "accounts": [
                            "account-a",
                        ],
                    },
                ]
            },
        ]

        clinet_instance.account.details.side_effect = [
            {
                "account": {
                    "iban": "iban-123",
                }
            },
            {
                "account": {
                    "bban": "bban-123",
                }
            },
            {
                "account": {
                    "resourceId": "resourceId-123",
                }
            },
            {
                "account": {
                    "iban": "yee-haa",
                }
            },
        ]

        entry(hass=hass, config=config, CONST=const, LOGGER=LOGGER)

        clinet_instance.requisitions.create.assert_not_called()
        clinet_instance.requisitions.initiate.assert_not_called()

        clinet_instance.account.details.assert_has_calls(
            [
                call("account-1"),
                call("account-2"),
                call("account-3"),
                call("account-a"),
            ]
        )

        hass.helpers.discovery.load_platform.assert_called_once_with(
            "sensor",
            "foobar",
            {
                "accounts": [
                    {
                        "bban": None,
                        "bic": None,
                        "config": {"aspsp_id": "aspsp_123", "enduser_id": "user_123", "ignore": ["resourceId-123"]},
                        "currency": None,
                        "iban": "iban-123",
                        "id": "account-1",
                        "name": None,
                        "owner": None,
                        "product": None,
                        "requisition": {
                            "enduser_id": None,
                            "id": "req-123",
                            "redirect": None,
                            "reference": "user_123-aspsp_123",
                            "status": "LN",
                        },
                        "status": None,
                        "unique_ref": "iban-123",
                    },
                    {
                        "bban": "bban-123",
                        "bic": None,
                        "config": {"aspsp_id": "aspsp_123", "enduser_id": "user_123", "ignore": ["resourceId-123"]},
                        "currency": None,
                        "iban": None,
                        "id": "account-2",
                        "name": None,
                        "owner": None,
                        "product": None,
                        "requisition": {
                            "enduser_id": None,
                            "id": "req-123",
                            "redirect": None,
                            "reference": "user_123-aspsp_123",
                            "status": "LN",
                        },
                        "status": None,
                        "unique_ref": "bban-123",
                    },
                    None,
                    {
                        "bban": None,
                        "bic": None,
                        "config": {"aspsp_id": "aspsp_321", "enduser_id": "user_321", "ignore": []},
                        "currency": None,
                        "iban": "yee-haa",
                        "id": "account-a",
                        "name": None,
                        "owner": None,
                        "product": None,
                        "requisition": {
                            "enduser_id": None,
                            "id": "req-321",
                            "redirect": None,
                            "reference": "user_321-aspsp_321",
                            "status": "LN",
                        },
                        "status": None,
                        "unique_ref": "yee-haa",
                    },
                ]
            },
            {
                "foobar": {
                    "requisitions": [
                        {"aspsp_id": "aspsp_123", "enduser_id": "user_123", "ignore": ["resourceId-123"]},
                        {"aspsp_id": "aspsp_321", "enduser_id": "user_321", "ignore": []},
                    ],
                    "token": "xxxx",
                }
            },
        )
