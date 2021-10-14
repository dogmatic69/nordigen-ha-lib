import unittest
from unittest.mock import MagicMock

from parameterized import parameterized

from nordigen_lib import (
    config_schema,
    entry,
    get_account,
    get_accounts,
    get_config,
    get_or_create_requisition,
    get_reference,
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
        self.assertEqual(vol.Required.call_count, 4)
        self.assertEqual(vol.Optional.call_count, 7)


class TestGetConfig(unittest.TestCase):
    def test_not_found(self):
        res = get_config([], {})

        self.assertEqual(None, res)

    def test_first(self):
        res = get_config(
            [
                {"enduser_id": "user1", "aspsp_id": "aspsp1"},
                {"enduser_id": "user2", "aspsp_id": "aspsp2"},
                {"enduser_id": "user3", "aspsp_id": "aspsp3"},
            ],
            {"reference": "user1-aspsp1"},
        )

        self.assertEqual({"enduser_id": "user1", "aspsp_id": "aspsp1"}, res)

    def test_last(self):
        res = get_config(
            [
                {"enduser_id": "user1", "aspsp_id": "aspsp1"},
                {"enduser_id": "user2", "aspsp_id": "aspsp2"},
                {"enduser_id": "user3", "aspsp_id": "aspsp3"},
            ],
            {"reference": "user3-aspsp3"},
        )

        self.assertEqual({"enduser_id": "user3", "aspsp_id": "aspsp3"}, res)


class TestReferenc(unittest.TestCase):
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
        self.assertEqual(res, expected)


class TestGetAccount(unittest.TestCase):
    def test_request_error(self):
        fn = MagicMock()

        fn.side_effect = requests.exceptions.HTTPError
        res = get_account(fn, "id", {}, LOGGER=MagicMock())
        self.assertEqual(None, res)

    def test_debug_strange_accounts(self):
        fn = MagicMock()
        LOGGER = MagicMock()
        fn.return_value = {"account": {}}
        get_account(fn=fn, id="id", requisition={}, LOGGER=LOGGER)

        LOGGER.warn.assert_called_with("Strange account: %s | %s", {}, {})

    def test_ignored(self):
        fn = MagicMock()
        LOGGER = MagicMock()
        fn.return_value = {"account": {"iban": 123}}
        get_account(fn=fn, id="id", requisition={}, LOGGER=LOGGER, ignored=[123])

        LOGGER.info.assert_called_with("Account ignored due to configuration :%s", 123)

    def test_normal(self):
        fn = MagicMock()
        LOGGER = MagicMock()
        fn.return_value = {"account": {"iban": 321}}
        res = get_account(fn=fn, id="id", requisition={"id": "req-id"}, LOGGER=LOGGER, ignored=[123])

        self.assertEqual(321, res["iban"])
        self.assertEqual("req-id", res["requisition"]["id"])


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

    @unittest.mock.patch("nordigen_lib.matched_requisition")
    def test_get_or_create_requisition_EX(self, mocked_matched_requisition):
        LOGGER = MagicMock()
        fn_create = MagicMock()
        fn_initiate = MagicMock()
        fn_remove = MagicMock()
        mocked_matched_requisition.return_value = {
            "id": "req-id",
            "status": "EX",
        }

        fn_create.return_value = {
            "id": "foobar-id",
        }
        fn_initiate.return_value = {
            "initiate": "http://example.com/whatever",
        }

        res = get_or_create_requisition(
            fn_create=fn_create,
            fn_initiate=fn_initiate,
            fn_remove=fn_remove,
            requisitions=[],
            reference="ref",
            enduser_id="user",
            aspsp_id="aspsp",
            LOGGER=LOGGER,
        )

        fn_remove.assert_called_with(
            id="req-id",
        )

        fn_create.assert_called_with(
            redirect="http://127.0.0.1/",
            reference="ref",
            enduser_id="user",
            agreements=[],
        )

        self.assertEqual(
            {
                "id": "foobar-id",
                "initiate": "http://example.com/whatever",
                "requires_auth": True,
            },
            res,
        )

    @unittest.mock.patch("nordigen_lib.matched_requisition")
    def test_get_or_create_requisition_not_exist(self, mocked_matched_requisition):

        LOGGER = MagicMock()
        fn_create = MagicMock()
        fn_initiate = MagicMock()
        fn_remove = MagicMock()
        mocked_matched_requisition.return_value = None

        fn_create.return_value = {
            "id": "foobar-id",
        }
        fn_initiate.return_value = {
            "initiate": "http://example.com/whatever",
        }

        res = get_or_create_requisition(
            fn_create=fn_create,
            fn_initiate=fn_initiate,
            fn_remove=fn_remove,
            requisitions=[],
            reference="ref",
            enduser_id="user",
            aspsp_id="aspsp",
            LOGGER=LOGGER,
        )

        fn_remove.assert_not_called()
        fn_create.assert_called_with(
            redirect="http://127.0.0.1/",
            reference="ref",
            enduser_id="user",
            agreements=[],
        )

        self.assertEqual(
            {
                "id": "foobar-id",
                "initiate": "http://example.com/whatever",
                "requires_auth": True,
            },
            res,
        )

    @unittest.mock.patch("nordigen_lib.matched_requisition")
    def test_get_or_create_requisition_not_linked(self, mocked_matched_requisition):

        LOGGER = MagicMock()
        fn_create = MagicMock()
        fn_initiate = MagicMock()
        fn_remove = MagicMock()
        mocked_matched_requisition.return_value = {
            "id": "req-id",
            "status": "not-LN",
        }

        fn_initiate.return_value = {
            "initiate": "http://example.com/whatever",
        }

        res = get_or_create_requisition(
            fn_create=fn_create,
            fn_initiate=fn_initiate,
            fn_remove=fn_remove,
            requisitions=[],
            reference="ref",
            enduser_id="user",
            aspsp_id="aspsp",
            LOGGER=LOGGER,
        )

        fn_create.assert_not_called()
        fn_remove.assert_not_called()

        fn_initiate.assert_called_with(
            id="req-id",
            aspsp_id="aspsp",
        )

        self.assertEqual(
            {
                "id": "req-id",
                "status": "not-LN",
                "initiate": "http://example.com/whatever",
                "requires_auth": True,
            },
            res,
        )

    @unittest.mock.patch("nordigen_lib.matched_requisition")
    def test_get_or_create_requisition_valid(self, mocked_matched_requisition):

        LOGGER = MagicMock()
        fn_create = MagicMock()
        fn_initiate = MagicMock()
        fn_remove = MagicMock()
        mocked_matched_requisition.return_value = {
            "id": "req-id",
            "status": "LN",
        }

        res = get_or_create_requisition(
            fn_create=fn_create,
            fn_initiate=fn_initiate,
            fn_remove=fn_remove,
            requisitions=[],
            reference="ref",
            enduser_id="user",
            aspsp_id="aspsp",
            LOGGER=LOGGER,
        )

        fn_create.assert_not_called()
        fn_remove.assert_not_called()
        fn_initiate.assert_not_called()

        self.assertEqual(
            {
                "id": "req-id",
                "status": "LN",
            },
            res,
        )


class TestGetAccounts(unittest.TestCase):
    def test_api_exception(self):
        client = MagicMock()
        LOGGER = MagicMock()

        HTTPError = requests.exceptions.HTTPError()
        client.requisitions.list.side_effect = HTTPError

        res = get_accounts(client=client, configs=[], LOGGER=LOGGER, CONST={})

        self.assertEqual([], res)
        LOGGER.error.assert_called_with("Unable to fetch Nordigen requisitions: %s", HTTPError)

    def test_key_error(self):
        client = MagicMock()
        LOGGER = MagicMock()

        client.requisitions.list.return_value = {}

        res = get_accounts(client=client, configs=[], LOGGER=LOGGER, CONST={})

        self.assertEqual([], res)

    @unittest.mock.patch("nordigen_lib.get_account")
    @unittest.mock.patch("nordigen_lib.get_or_create_requisition")
    def test_works(self, mocked_get_or_create_requisition, mocked_get_account):
        client = MagicMock()
        client.requisitions.list.return_value = {"results": []}

        CONST = {
            "ASPSP_ID": "aspsp_id",
            "IGNORE_ACCOUNTS": "ignore_accounts",
            "ENDUSER_ID": "enduser_id",
        }

        LOGGER = MagicMock()
        configs = [{"enduser_id": "user", "aspsp_id": "aspsp", "ignore_accounts": []}]

        mocked_get_or_create_requisition.return_value = {"id": "req-id", "accounts": [1, 2]}
        mocked_get_account.return_value = {"foobar": "account-1"}

        res = get_accounts(client=client, configs=configs, LOGGER=LOGGER, CONST=CONST)
        self.assertEqual([{"foobar": "account-1"}, {"foobar": "account-1"}], res)


class TestEntry(unittest.TestCase):
    @unittest.mock.patch("nordigen_lib.Client")
    def test_not_configured(self, mocked_client):
        LOGGER = MagicMock()
        res = entry(hass=None, config={}, CONST={"DOMAIN": "foo"}, LOGGER=LOGGER)
        LOGGER.warning.assert_called_with("Nordigen not configured")

        self.assertTrue(res)

    @unittest.mock.patch("nordigen_lib.get_accounts")
    @unittest.mock.patch("nordigen_lib.Client")
    def test_entry(self, mocked_client, mocked_get_accounts):
        hass = MagicMock()
        LOGGER = MagicMock()

        mocked_get_accounts.return_value = ["accounts"]
        mocked_client.return_value = "client instance"

        config = {"foobar": {"token": "xxxx", "requisitions": []}}
        const = {"DOMAIN": "foobar", "TOKEN": "token", "REQUISITIONS": "requisitions"}

        res = entry(hass=hass, config=config, CONST=const, LOGGER=LOGGER)

        mocked_client.assert_called_with(token="xxxx")
        mocked_get_accounts.assert_called_with(client="client instance", configs=[], LOGGER=LOGGER, CONST=const)
        hass.helpers.discovery.load_platform.assert_called_with("sensor", "foobar", {"accounts": ["accounts"]}, config)

        self.assertTrue(res)
