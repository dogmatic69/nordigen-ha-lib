import unittest
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from nordigen_lib.sensor import NordigenBalanceSensor, build_coordinator, build_sensors, data_updater, random_balance
from . import AsyncMagicMock

case = unittest.TestCase()


class TestSensorRandom(unittest.TestCase):
    def test_basic(self):
        res = random_balance()
        self.assertTrue(res["balances"][0]["balanceAmount"]["amount"] > 0)


class TestBuildCoordinator(unittest.TestCase):
    def test_basic(self):
        hass = MagicMock()
        logger = MagicMock()
        updater = MagicMock()
        interval = MagicMock()
        res = build_coordinator(hass=hass, LOGGER=logger, updater=updater, interval=interval, reference="ref")
        self.assertEqual(res.hass, hass)
        self.assertEqual(res.logger, logger)
        self.assertEqual(res.update_method, updater)
        self.assertEqual(res.update_interval, interval)
        self.assertEqual(res.name, "nordigen-balance-ref")


class TestDataUpdater:
    @pytest.mark.asyncio
    async def test_return(self):
        executor = AsyncMagicMock()
        executor.return_value = {
            "balances": [
                {
                    "balanceAmount": {
                        "amount": 123,
                        "currency": "SEK",
                    },
                    "balanceType": "interimAvailable",
                    "creditLimitIncluded": True,
                },
                {
                    "balanceAmount": {
                        "amount": 321,
                        "currency": "SEK",
                    },
                    "balanceType": "interimBooked",
                },
            ]
        }

        balance = MagicMock()
        logger = MagicMock()
        res = data_updater(LOGGER=logger, async_executor=executor, balance=balance, account_id="id")
        res = await res()

        case.assertEqual(
            res,
            {
                "closingBooked": None,
                "expected": None,
                "openingBooked": None,
                "forwardAvailable": None,
                "nonInvoiced": None,
                "interimAvailable": 123,
                "interimBooked": 321,
            },
        )

    @pytest.mark.asyncio
    async def test_exception(self):
        executor = AsyncMagicMock()
        executor.side_effect = Exception("whoops")

        balance = MagicMock()
        logger = MagicMock()
        res = data_updater(LOGGER=logger, async_executor=executor, balance=balance, account_id="id")

        with case.assertRaises(UpdateFailed):
            await res()


class TestBuildSensors:
    def build_sensors_helper(self, account, const, debug=False):
        hass = MagicMock()
        logger = MagicMock()
        return dict(hass=hass, LOGGER=logger, account=account, CONST=const, debug=debug)

    @unittest.mock.patch("nordigen_lib.sensor.random_balance")
    @unittest.mock.patch("nordigen_lib.sensor.build_coordinator")
    @unittest.mock.patch("nordigen_lib.sensor.timedelta")
    @unittest.mock.patch("nordigen_lib.sensor.data_updater")
    @pytest.mark.asyncio
    async def test_balance_debug(
        self, mocked_data_updater, mocked_timedelta, mocked_build_coordinator, mocked_random_balance
    ):
        account = {
            "config": {
                "refresh_rate": 1,
                "disable": False,
            },
            "id": "foobar-id",
        }
        const = {
            "AVAILABLE_BALANCE": "disable",
            "BOOKED_BALANCE": "disable",
            "REFRESH_RATE": "refresh_rate",
        }

        mocked_balance_coordinator = MagicMock()
        mocked_build_coordinator.return_value = mocked_balance_coordinator

        mocked_balance_coordinator.async_config_entry_first_refresh = AsyncMock()

        args = self.build_sensors_helper(account=account, const=const, debug=True)
        await build_sensors(**args)

        mocked_data_updater.assert_called_with(
            LOGGER=args["LOGGER"],
            async_executor=args["hass"].async_add_executor_job,
            balance=mocked_random_balance,
            account_id="foobar-id",
        )

    @unittest.mock.patch("nordigen_lib.sensor.random_balance")
    @unittest.mock.patch("nordigen_lib.sensor.build_coordinator")
    @unittest.mock.patch("nordigen_lib.sensor.timedelta")
    @unittest.mock.patch("nordigen_lib.sensor.data_updater")
    @pytest.mark.asyncio
    async def test_balance(
        self, mocked_data_updater, mocked_timedelta, mocked_build_coordinator, mocked_random_balance
    ):
        account = {
            "config": {
                "refresh_rate": 1,
                "disable": False,
            },
            "id": "foobar-id",
        }
        const = {
            "DOMAIN": "domain",
            "AVAILABLE_BALANCE": "disable",
            "BOOKED_BALANCE": "disable",
            "REFRESH_RATE": "refresh_rate",
        }

        mocked_balance_coordinator = MagicMock()
        mocked_build_coordinator.return_value = mocked_balance_coordinator

        mocked_balance_coordinator.async_config_entry_first_refresh = AsyncMock()

        args = self.build_sensors_helper(account=account, const=const)
        await build_sensors(**args)

        mocked_data_updater.assert_called_with(
            LOGGER=args["LOGGER"],
            async_executor=args["hass"].async_add_executor_job,
            balance=args["hass"].data["domain"]["client"].account.balances,
            account_id="foobar-id",
        )

    @unittest.mock.patch("nordigen_lib.sensor.NordigenBalanceSensor")
    @unittest.mock.patch("nordigen_lib.sensor.random_balance")
    @unittest.mock.patch("nordigen_lib.sensor.build_coordinator")
    @unittest.mock.patch("nordigen_lib.sensor.timedelta")
    @unittest.mock.patch("nordigen_lib.sensor.data_updater")
    @pytest.mark.asyncio
    async def test_available_entities(
        self,
        mocked_data_updater,
        mocked_timedelta,
        mocked_build_coordinator,
        mocked_random_balance,
        mocked_nordigen_balance_sensor,
    ):
        account = {
            "config": {
                "refresh_rate": 1,
                "available": True,
                "booked": False,
            },
            "id": "foobar-id",
        }
        const = {
            "ICON": {},
            "DOMAIN": "domain",
            "AVAILABLE_BALANCE": "available",
            "BOOKED_BALANCE": "booked",
            "REFRESH_RATE": "refresh_rate",
        }

        mocked_balance_coordinator = MagicMock()
        mocked_build_coordinator.return_value = mocked_balance_coordinator

        mocked_balance_coordinator.async_config_entry_first_refresh = AsyncMock()

        args = self.build_sensors_helper(account=account, const=const)
        res = await build_sensors(**args)

        assert 1 == len(res)
        mocked_nordigen_balance_sensor.assert_called_with(
            **{
                "id": "foobar-id",
                "balance_type": "interimAvailable",
                "config": {"available": True, "booked": False, "refresh_rate": 1},
                "coordinator": mocked_balance_coordinator,
                "domain": "domain",
                "icons": {},
            }
        )

    @unittest.mock.patch("nordigen_lib.sensor.NordigenBalanceSensor")
    @unittest.mock.patch("nordigen_lib.sensor.random_balance")
    @unittest.mock.patch("nordigen_lib.sensor.build_coordinator")
    @unittest.mock.patch("nordigen_lib.sensor.timedelta")
    @unittest.mock.patch("nordigen_lib.sensor.data_updater")
    @pytest.mark.asyncio
    async def test_booked_entities(
        self,
        mocked_data_updater,
        mocked_timedelta,
        mocked_build_coordinator,
        mocked_random_balance,
        mocked_nordigen_balance_sensor,
    ):
        account = {
            "id": "foobar-id",
            "config": {
                "refresh_rate": 1,
                "available": False,
                "booked": True,
            },
        }
        const = {
            "ICON": {},
            "DOMAIN": "domain",
            "AVAILABLE_BALANCE": "available",
            "BOOKED_BALANCE": "booked",
            "REFRESH_RATE": "refresh_rate",
        }

        mocked_balance_coordinator = MagicMock()
        mocked_build_coordinator.return_value = mocked_balance_coordinator

        mocked_balance_coordinator.async_config_entry_first_refresh = AsyncMock()

        args = self.build_sensors_helper(account=account, const=const)
        res = await build_sensors(**args)

        assert 1 == len(res)
        mocked_nordigen_balance_sensor.assert_called_with(
            **{
                "id": "foobar-id",
                "balance_type": "interimBooked",
                "config": {"available": False, "booked": True, "refresh_rate": 1},
                "coordinator": mocked_balance_coordinator,
                "domain": "domain",
                "icons": {},
            }
        )


class TestSensors(unittest.TestCase):
    data = {
        "coordinator": MagicMock(),
        "id": "account_id",
        "domain": "domain",
        "balance_type": "interimWhatever",
        "iban": "iban",
        "bban": "bban",
        "unique_ref": "unique_ref",
        "name": "name",
        "owner": "owner",
        "currency": "currency",
        "product": "product",
        "status": "status",
        "bic": "bic",
        "requisition": {
            "id": "req-id",
            "enduser_id": "req-user-id",
            "reference": "req-ref",
        },
        "config": "config",
        "icons": {
            "foobar": "something",
            "default": "something-else",
        },
    }

    def test_init(self):
        sensor = NordigenBalanceSensor(**self.data)
        for k in self.data:
            if k in ["coordinator"]:
                continue
            self.assertEqual(getattr(sensor, f"_{k}"), self.data[k])

    def test_device_info(self):
        sensor = NordigenBalanceSensor(**self.data)

        self.assertEqual(
            {
                "identifiers": {("domain", "req-id")},
                "name": "bic unique_ref whatever",
            },
            sensor.device_info,
        )

    def test_unique_id(self):
        sensor = NordigenBalanceSensor(**self.data)

        self.assertEqual("unique_ref-whatever", sensor.unique_id)

    def test_balance_type(self):
        sensor = NordigenBalanceSensor(**self.data)

        self.assertEqual("whatever", sensor.balance_type)

    def test_name(self):
        sensor = NordigenBalanceSensor(**self.data)

        self.assertEqual("unique_ref whatever", sensor.name)

    def test_state(self):
        ret = {"interimWhatever": "123"}
        self.data["coordinator"].data.__getitem__.side_effect = ret.__getitem__

        sensor = NordigenBalanceSensor(**self.data)

        self.assertEqual("123", sensor.state)

    def test_unit_of_measurement(self):
        sensor = NordigenBalanceSensor(**self.data)

        self.assertEqual("currency", sensor.unit_of_measurement)

    def test_icon_default(self):
        sensor = NordigenBalanceSensor(**self.data)

        self.assertEqual("something-else", sensor.icon)

    def test_icon_custom(self):
        data = dict(self.data)
        data["currency"] = "foobar"
        sensor = NordigenBalanceSensor(**data)

        self.assertEqual("something", sensor.icon)

    def test_icon_available_true(self):
        data = dict(self.data)
        data["status"] = "enabled"
        sensor = NordigenBalanceSensor(**data)

        self.assertEqual(True, sensor.available)

    def test_icon_available_false(self):
        data = dict(self.data)
        data["status"] = "not-enabled"
        sensor = NordigenBalanceSensor(**data)

        self.assertEqual(False, sensor.available)

    @unittest.mock.patch("nordigen_lib.sensor.datetime")
    def test_state_attributes(self, mocked_datatime):
        mocked_datatime.now.return_value = "last_update"
        sensor = NordigenBalanceSensor(**self.data)

        self.assertEqual(
            {
                "balance_type": "whatever",
                "iban": "iban",
                "unique_ref": "unique_ref",
                "name": "name",
                "owner": "owner",
                "product": "product",
                "status": "status",
                "bic": "bic",
                "enduser_id": "req-user-id",
                "reference": "req-ref",
                "last_update": "last_update",
            },
            sensor.state_attributes,
        )
