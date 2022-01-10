import unittest
from unittest.mock import MagicMock

from parameterized import parameterized

from nordigen.client import AccountClient
from nordigen_lib import config_schema, entry, get_client, get_config
from nordigen_lib.ng import (
    get_account,
    get_accounts,
    get_or_create_requisition,
    get_reference,
    get_requisitions,
    matched_requisition,
    requests,
    unique_ref,
)


class TestSchema(unittest.TestCase):
    def test_basic(self):
        vol = MagicMock()
        cv = MagicMock()
        const = MagicMock()

        config_schema(vol, cv, const)

        self.assertEqual(vol.Schema.call_count, 2)
        self.assertEqual(vol.Required.call_count, 5)
        self.assertEqual(vol.Optional.call_count, 7)


class TestGetConfig(unittest.TestCase):
    def test_not_found(self):
        res = get_config([], {})

        self.assertEqual(None, res)

    def test_first(self):
        res = get_config(
            [
                {"enduser_id": "user1", "institution_id": "aspsp1"},
                {"enduser_id": "user2", "institution_id": "aspsp2"},
                {"enduser_id": "user3", "institution_id": "aspsp3"},
            ],
            {"reference": "user1-aspsp1"},
        )

        self.assertEqual({"enduser_id": "user1", "institution_id": "aspsp1"}, res)

    def test_last(self):
        res = get_config(
            [
                {"enduser_id": "user1", "institution_id": "aspsp1"},
                {"enduser_id": "user2", "institution_id": "aspsp2"},
                {"enduser_id": "user3", "institution_id": "aspsp3"},
            ],
            {"reference": "user3-aspsp3"},
        )

        self.assertEqual({"enduser_id": "user3", "institution_id": "aspsp3"}, res)


class TestGetClient(unittest.TestCase):
    def test_basic(self):
        res = get_client(
            **{
                "secret_id": "secret1",
                "secret_key": "secret2",
            }
        )

        self.assertIsInstance(res.account, AccountClient)


class TestReference(unittest.TestCase):
    def test_basic(self):
        res = get_reference("user1", "aspsp1")
        self.assertEqual("user1-aspsp1", res)

    @parameterized.expand(
        [
            ({"iban": "iban-123"}, "iban-123"),
            ({"bban": "bban-123"}, "bban-123"),
            ({"resourceId": "resourceId-123"}, "resourceId-123"),
            ({"iban": "iban-123", "bban": "bban-123"}, "iban-123"),
            ({}, "id-123"),
        ]
    )
    def test_unique_ref(self, data, expected):
        res = unique_ref("id-123", data)
        self.assertEqual(expected, res)


class TestGetAccount(unittest.TestCase):
    def test_request_error(self):
        fn = MagicMock()

        fn.side_effect = requests.exceptions.HTTPError
        res = get_account(fn, "id", {}, logger=MagicMock())
        self.assertEqual(None, res)

    def test_debug_strange_accounts(self):
        fn = MagicMock()
        logger = MagicMock()
        fn.return_value = {"account": {}}
        get_account(fn=fn, id="id", requisition={}, logger=logger)

        logger.warn.assert_called_with("No iban: %s | %s", {}, {})

    def test_ignored(self):
        fn = MagicMock()
        logger = MagicMock()
        fn.return_value = {"account": {"iban": 123}}
        get_account(fn=fn, id="id", requisition={}, logger=logger, ignored=[123])

        logger.info.assert_called_with("Account ignored due to configuration :%s", 123)

    def test_normal(self):
        fn = MagicMock()
        logger = MagicMock()
        fn.return_value = {"account": {"iban": 321}}
        res = get_account(fn=fn, id="id", requisition={"id": "req-id"}, logger=logger, ignored=[123])

        self.assertEqual(321, res["iban"])


class TestRequisition(unittest.TestCase):
    def test_non_match(self):
        res = matched_requisition("ref", [])
        self.assertEqual({}, res)

    def test_first(self):
        res = matched_requisition(
            "ref",
            [
                {"reference": "ref"},
                {"reference": "fer"},
                {"reference": "erf"},
            ],
        )
        self.assertEqual({"reference": "ref"}, res)

    def test_last(self):
        res = matched_requisition(
            "erf",
            [
                {"reference": "ref"},
                {"reference": "fer"},
                {"reference": "erf"},
            ],
        )
        self.assertEqual({"reference": "erf"}, res)

    @unittest.mock.patch("nordigen_lib.ng.matched_requisition")
    def test_get_or_create_requisition_EX(self, mocked_matched_requisition):
        logger = MagicMock()
        fn_create = MagicMock()
        fn_remove = MagicMock()
        fn_info = MagicMock()
        mocked_matched_requisition.return_value = {
            "id": "req-id",
            "status": "EX",
        }

        fn_create.return_value = {
            "id": "foobar-id",
            "link": "https://example.com/whatever",
        }

        res = get_or_create_requisition(
            fn_create=fn_create,
            fn_remove=fn_remove,
            fn_info=fn_info,
            requisitions=[],
            reference="ref",
            institution_id="aspsp",
            logger=logger,
            config={},
        )

        fn_remove.assert_called_with(
            id="req-id",
        )

        fn_create.assert_called_with(
            redirect="https://127.0.0.1/",
            reference="ref",
            institution_id="aspsp",
        )

        self.assertEqual(
            {
                "id": "foobar-id",
                "link": "https://example.com/whatever",
                "config": {},
                "details": {
                    "id": "N26_NTSBDEB1",
                    "name": "N26 Bank",
                    "bic": "NTSBDEB1",
                    "transaction_total_days": "730",
                    "logo": "https://cdn.nordigen.com/ais/N26_NTSBDEB1.png",
                },
            },
            res,
        )

    @unittest.mock.patch("nordigen_lib.ng.matched_requisition")
    def test_get_or_create_requisition_not_exist(self, mocked_matched_requisition):

        logger = MagicMock()
        fn_create = MagicMock()
        fn_remove = MagicMock()
        fn_info = MagicMock()
        mocked_matched_requisition.return_value = None

        fn_create.return_value = {
            "id": "foobar-id",
            "link": "https://example.com/whatever",
        }

        res = get_or_create_requisition(
            fn_create=fn_create,
            fn_remove=fn_remove,
            fn_info=fn_info,
            requisitions=[],
            reference="ref",
            institution_id="aspsp",
            logger=logger,
            config={},
        )

        fn_remove.assert_not_called()
        fn_create.assert_called_with(
            redirect="https://127.0.0.1/",
            reference="ref",
            institution_id="aspsp",
        )

        self.assertEqual(
            {
                "id": "foobar-id",
                "link": "https://example.com/whatever",
                "config": {},
                "details": {
                    "id": "N26_NTSBDEB1",
                    "name": "N26 Bank",
                    "bic": "NTSBDEB1",
                    "transaction_total_days": "730",
                    "logo": "https://cdn.nordigen.com/ais/N26_NTSBDEB1.png",
                },
            },
            res,
        )

    @unittest.mock.patch("nordigen_lib.ng.matched_requisition")
    def test_get_or_create_requisition_not_linked(self, mocked_matched_requisition):

        logger = MagicMock()
        fn_create = MagicMock()
        fn_remove = MagicMock()
        fn_info = MagicMock()
        mocked_matched_requisition.return_value = {
            "id": "req-id",
            "status": "not-LN",
            "link": "https://example.com/whatever",
        }

        res = get_or_create_requisition(
            fn_create=fn_create,
            fn_remove=fn_remove,
            fn_info=fn_info,
            requisitions=[],
            reference="ref",
            institution_id="aspsp",
            logger=logger,
            config={},
        )

        fn_create.assert_not_called()
        fn_remove.assert_not_called()

        self.assertEqual(
            {
                "id": "req-id",
                "status": "not-LN",
                "link": "https://example.com/whatever",
                "config": {},
                "details": {
                    "id": "N26_NTSBDEB1",
                    "name": "N26 Bank",
                    "bic": "NTSBDEB1",
                    "transaction_total_days": "730",
                    "logo": "https://cdn.nordigen.com/ais/N26_NTSBDEB1.png",
                },
            },
            res,
        )

    @unittest.mock.patch("nordigen_lib.ng.matched_requisition")
    def test_get_or_create_requisition_valid(self, mocked_matched_requisition):

        logger = MagicMock()
        fn_create = MagicMock()
        fn_remove = MagicMock()
        fn_info = MagicMock()
        mocked_matched_requisition.return_value = {
            "id": "req-id",
            "status": "LN",
        }

        res = get_or_create_requisition(
            fn_create=fn_create,
            fn_remove=fn_remove,
            fn_info=fn_info,
            requisitions=[],
            reference="ref",
            institution_id="aspsp",
            logger=logger,
            config={},
        )

        fn_create.assert_not_called()
        fn_remove.assert_not_called()

        self.assertEqual(
            {
                "id": "req-id",
                "status": "LN",
                "config": {},
                "details": {
                    "id": "N26_NTSBDEB1",
                    "name": "N26 Bank",
                    "bic": "NTSBDEB1",
                    "transaction_total_days": "730",
                    "logo": "https://cdn.nordigen.com/ais/N26_NTSBDEB1.png",
                },
            },
            res,
        )


class TestGetAccounts(unittest.TestCase):
    def test_api_exception(self):
        client = MagicMock()
        logger = MagicMock()

        HTTPError = requests.exceptions.HTTPError()
        client.requisitions.list.side_effect = HTTPError

        res = get_requisitions(client=client, configs={}, logger=logger, const={})

        self.assertEqual([], res)
        logger.error.assert_called_with("Unable to fetch Nordigen requisitions: %s", HTTPError)

    def test_key_error(self):
        client = MagicMock()
        logger = MagicMock()

        client.requisitions.list.return_value = {}

        res = get_accounts(client=client, requisitions=[], logger=logger, const={})

        self.assertEqual([], res)

    @unittest.mock.patch("nordigen_lib.ng.get_account")
    def test_works(self, mocked_get_account):
        client = MagicMock()
        client.requisitions.list.return_value = {"results": []}

        const = {
            "INSTITUTION_ID": "institution_id",
            "IGNORE_ACCOUNTS": "ignore_accounts",
            "ENDUSER_ID": "enduser_id",
        }

        logger = MagicMock()

        mocked_get_account.side_effect = [
            {"foobar": "account-1"},
            {"foobar": "account-2"},
            {"foobar": "account-3"},
        ]

        requisitions = [
            {"id": "req-1", "accounts": [1, 2], "config": {"ignore_accounts": []}},
            {"id": "req-2", "accounts": [3], "config": {"ignore_accounts": []}},
        ]
        res = get_accounts(client=client, requisitions=requisitions, logger=logger, const=const)
        self.assertEqual(
            [
                {"foobar": "account-1"},
                {"foobar": "account-2"},
                {"foobar": "account-3"},
            ],
            res,
        )


class TestEntry(unittest.TestCase):
    @unittest.mock.patch("nordigen_lib.ng.Client")
    def test_not_configured(self, mocked_client):
        logger = MagicMock()
        res = entry(hass=None, config={}, const={"DOMAIN": "foo"}, logger=logger)
        logger.warning.assert_called_with("Nordigen not configured")

        self.assertTrue(res)

    @unittest.mock.patch("nordigen_lib.get_requisitions")
    @unittest.mock.patch("nordigen_lib.get_accounts")
    @unittest.mock.patch("nordigen_lib.get_client")
    def test_entry(self, mocked_get_client, mocked_get_accounts, mocked_get_requisitions):
        hass = MagicMock()
        client = MagicMock()
        logger = MagicMock()

        mocked_get_accounts.return_value = ["account"]
        mocked_get_requisitions.return_value = ["requisition"]
        mocked_get_client.return_value = client

        config = {"foobar": {"secret_id": "xxxx", "secret_key": "yyyy", "requisitions": []}}
        const = {
            "DOMAIN": "foobar",
            "SECRET_ID": "secret_id",
            "SECRET_KEY": "secret_key",
            "REQUISITIONS": "requisitions",
        }

        res = entry(hass=hass, config=config, const=const, logger=logger)

        mocked_get_client.assert_called_with(secret_id="xxxx", secret_key="yyyy")
        mocked_get_accounts.assert_called_with(client=client, requisitions=["requisition"], logger=logger, const=const)
        hass.helpers.discovery.load_platform.assert_called_with(
            "sensor", "foobar", {"accounts": ["account"], "requisitions": ["requisition"]}, config
        )

        self.assertTrue(res)
