import unittest
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from nordigen_lib.sensor import (
    BalanceSensor,
    RequisitionSensor,
    balance_update,
    build_account_sensors,
    build_coordinator,
    build_requisition_sensor,
    build_sensors,
    random_balance,
    requisition_update,
)
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

        res = build_coordinator(hass=hass, logger=logger, updater=updater, interval=interval, reference="ref")

        self.assertEqual(res.hass, hass)
        self.assertEqual(res.logger, logger)
        self.assertEqual(res.update_method, updater)
        self.assertEqual(res.update_interval, interval)
        self.assertEqual(res.name, "nordigen-balance-ref")

    def test_listners(self):
        hass = MagicMock()
        logger = MagicMock()
        updater = MagicMock()
        interval = MagicMock()

        res = build_coordinator(hass=hass, logger=logger, updater=updater, interval=interval, reference="ref")

        self.assertEqual([], res._listeners)


class TestRequisitionUpdate:
    @pytest.mark.asyncio
    async def test_return(self):
        executor = AsyncMagicMock()
        executor.return_value = {"id": "req-id"}

        fn = MagicMock()
        logger = MagicMock()
        res = requisition_update(logger=logger, async_executor=executor, fn=fn, requisition_id="id")
        res = await res()

        case.assertEqual(
            res,
            {"id": "req-id"},
        )

    @pytest.mark.asyncio
    async def test_exception(self):
        executor = AsyncMagicMock()
        executor.side_effect = Exception("whoops")

        balance = MagicMock()
        logger = MagicMock()
        res = requisition_update(logger=logger, async_executor=executor, fn=balance, requisition_id="id")

        with case.assertRaises(UpdateFailed):
            await res()


class TestBalanceUpdate:
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

        fn = MagicMock()
        logger = MagicMock()
        res = balance_update(logger=logger, async_executor=executor, fn=fn, account_id="id")
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
        res = balance_update(logger=logger, async_executor=executor, fn=balance, account_id="id")

        with case.assertRaises(UpdateFailed):
            await res()


class TestBuildSensors:
    @unittest.mock.patch("nordigen_lib.sensor.build_requisition_sensor")
    @unittest.mock.patch("nordigen_lib.sensor.build_account_sensors")
    @pytest.mark.asyncio
    async def test_build_sensors_unconfirmed(self, mocked_build_account_sensors, mocked_build_requisition_sensor):
        args = {"hass": "hass", "logger": "logger", "account": {"requires_auth": True}, "const": "const"}
        await build_sensors(**args, debug="debug")
        args["requisition"] = args["account"]
        del args["account"]

        mocked_build_account_sensors.assert_not_called()
        mocked_build_requisition_sensor.assert_called_with(**args)

    @unittest.mock.patch("nordigen_lib.sensor.build_requisition_sensor")
    @unittest.mock.patch("nordigen_lib.sensor.build_account_sensors")
    @pytest.mark.asyncio
    async def test_build_sensors_account(self, mocked_build_account_sensors, mocked_build_requisition_sensor):
        args = {
            "hass": "hass",
            "logger": "logger",
            "account": {"requires_auth": False},
            "const": "const",
            "debug": "debug",
        }
        await build_sensors(**args)

        mocked_build_account_sensors.assert_called_with(**args)
        mocked_build_requisition_sensor.assert_not_called()


class TestBuildAccountSensors:
    def build_sensors_helper(self, account, const, debug=False):
        hass = MagicMock()
        logger = MagicMock()
        return dict(hass=hass, logger=logger, account=account, const=const, debug=debug)

    @unittest.mock.patch("nordigen_lib.sensor.random_balance")
    @unittest.mock.patch("nordigen_lib.sensor.build_coordinator")
    @unittest.mock.patch("nordigen_lib.sensor.balance_update")
    @pytest.mark.asyncio
    async def test_balance_debug(self, mocked_balance_update, mocked_build_coordinator, mocked_random_balance):
        account = {
            "config": {
                "refresh_rate": 1,
                "disable": False,
                "balance_types": [],
            },
            "id": "foobar-id",
        }
        const = {
            "AVAILABLE_BALANCE": "disable",
            "BOOKED_BALANCE": "disable",
            "REFRESH_RATE": "refresh_rate",
            "BALANCE_TYPES": "balance_types",
        }

        mocked_balance_coordinator = MagicMock()
        mocked_build_coordinator.return_value = mocked_balance_coordinator

        mocked_balance_coordinator.async_config_entry_first_refresh = AsyncMock()

        args = self.build_sensors_helper(account=account, const=const, debug=True)
        await build_account_sensors(**args)

        mocked_balance_update.assert_called_with(
            logger=args["logger"],
            async_executor=args["hass"].async_add_executor_job,
            fn=mocked_random_balance,
            account_id="foobar-id",
        )

    @unittest.mock.patch("nordigen_lib.sensor.build_coordinator")
    @unittest.mock.patch("nordigen_lib.sensor.balance_update")
    @pytest.mark.asyncio
    async def test_balance(self, mocked_balance_update, mocked_build_coordinator):
        account = {
            "config": {
                "refresh_rate": 1,
                "disable": False,
            },
            "id": "foobar-id",
            "iban": "iban",
            "bban": "bban",
            "unique_ref": "unique_ref",
            "name": "name",
            "owner": "owner",
            "currency": "currency",
            "product": "product",
            "status": "status",
            "bic": "bic",
            "requisition": "requisition",
        }
        const = {
            "DOMAIN": "domain",
            "AVAILABLE_BALANCE": "disable",
            "BOOKED_BALANCE": "disable",
            "REFRESH_RATE": "refresh_rate",
            "ICON": "icon",
            "BALANCE_TYPES": "balance_types",
        }

        mocked_balance_coordinator = MagicMock()
        mocked_build_coordinator.return_value = mocked_balance_coordinator

        mocked_balance_coordinator.async_config_entry_first_refresh = AsyncMock()

        args = self.build_sensors_helper(account=account, const=const)
        await build_account_sensors(**args)

        mocked_balance_update.assert_called_with(
            logger=args["logger"],
            async_executor=args["hass"].async_add_executor_job,
            fn=args["hass"].data["domain"]["client"].account.balances,
            account_id="foobar-id",
        )

    @unittest.mock.patch("nordigen_lib.sensor.BalanceSensor")
    @unittest.mock.patch("nordigen_lib.sensor.random_balance")
    @unittest.mock.patch("nordigen_lib.sensor.build_coordinator")
    @unittest.mock.patch("nordigen_lib.sensor.timedelta")
    @unittest.mock.patch("nordigen_lib.sensor.balance_update")
    @pytest.mark.asyncio
    async def test_available_entities(
        self,
        mocked_balance_update,
        mocked_timedelta,
        mocked_build_coordinator,
        mocked_random_balance,
        mocked_nordigen_balance_sensor,
    ):
        account = {
            "config": {
                "refresh_rate": 1,
                "balance_types": ["Available"],
            },
            "id": "foobar-id",
        }
        const = {
            "ICON": {},
            "DOMAIN": "domain",
            "AVAILABLE_BALANCE": "available",
            "BOOKED_BALANCE": "booked",
            "REFRESH_RATE": "refresh_rate",
            "BALANCE_TYPES": "balance_types",
        }

        mocked_balance_coordinator = MagicMock()
        mocked_build_coordinator.return_value = mocked_balance_coordinator

        mocked_balance_coordinator.async_config_entry_first_refresh = AsyncMock()

        args = self.build_sensors_helper(account=account, const=const)
        res = await build_account_sensors(**args)

        assert 1 == len(res)
        mocked_nordigen_balance_sensor.assert_called_with(
            **{
                "id": "foobar-id",
                "balance_type": "interimAvailable",
                "config": {"refresh_rate": 1, "balance_types": ["Available"]},
                "coordinator": mocked_balance_coordinator,
                "domain": "domain",
                "icons": {},
            }
        )

    @unittest.mock.patch("nordigen_lib.sensor.BalanceSensor")
    @unittest.mock.patch("nordigen_lib.sensor.random_balance")
    @unittest.mock.patch("nordigen_lib.sensor.build_coordinator")
    @unittest.mock.patch("nordigen_lib.sensor.timedelta")
    @unittest.mock.patch("nordigen_lib.sensor.balance_update")
    @pytest.mark.asyncio
    async def test_booked_entities(
        self,
        mocked_balance_update,
        mocked_timedelta,
        mocked_build_coordinator,
        mocked_random_balance,
        mocked_nordigen_balance_sensor,
    ):
        account = {
            "id": "foobar-id",
            "config": {
                "refresh_rate": 1,
                "balance_types": ["Booked"],
            },
        }
        const = {
            "ICON": {},
            "DOMAIN": "domain",
            "AVAILABLE_BALANCE": "available",
            "BOOKED_BALANCE": "booked",
            "REFRESH_RATE": "refresh_rate",
            "BALANCE_TYPES": "balance_types",
        }

        mocked_balance_coordinator = MagicMock()
        mocked_build_coordinator.return_value = mocked_balance_coordinator

        mocked_balance_coordinator.async_config_entry_first_refresh = AsyncMock()

        args = self.build_sensors_helper(account=account, const=const)
        res = await build_account_sensors(**args)

        assert 1 == len(res)
        mocked_nordigen_balance_sensor.assert_called_with(
            **{
                "id": "foobar-id",
                "balance_type": "interimBooked",
                "config": {"refresh_rate": 1, "balance_types": ["Booked"]},
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
            "details": {
                "id": "N26_NTSBDEB1",
                "name": "N26 Bank",
                "bic": "NTSBDEB1",
                "transaction_total_days": "730",
                "logo": "https://cdn.nordigen.com/ais/N26_NTSBDEB1.png",
            },
        },
        "config": "config",
        "icons": {
            "foobar": "something",
            "default": "something-else",
        },
    }

    def test_init(self):
        sensor = BalanceSensor(**self.data)
        for k in self.data:
            if k in ["coordinator"]:
                continue
            self.assertEqual(getattr(sensor, f"_{k}"), self.data[k])

    def test_device_info(self):
        sensor = BalanceSensor(**self.data)

        self.assertEqual(
            {
                "default_manufacturer": "N26 Bank",
                "default_name": "bic unique_ref whatever",
                "identifiers": {("domain", "unique_ref-whatever"), ("domain", "req-id")},
                "suggested_area": "External",
                "sw_version": "V2",
                "via_device": "req-id",
            },
            sensor.device_info,
        )

    def test_unique_id(self):
        sensor = BalanceSensor(**self.data)

        self.assertEqual("unique_ref-whatever", sensor.unique_id)

    def test_balance_type(self):
        sensor = BalanceSensor(**self.data)

        self.assertEqual("whatever", sensor.balance_type)

    def test_name(self):
        sensor = BalanceSensor(**self.data)

        self.assertEqual("unique_ref whatever", sensor.name)

    def test_state(self):
        ret = {"interimWhatever": "123.990"}
        self.data["coordinator"].data.__getitem__.side_effect = ret.__getitem__

        sensor = BalanceSensor(**self.data)

        self.assertEqual(123.99, sensor.state)

    def test_unit_of_measurement(self):
        sensor = BalanceSensor(**self.data)

        self.assertEqual("currency", sensor.unit_of_measurement)

    def test_icon_default(self):
        sensor = BalanceSensor(**self.data)

        self.assertEqual("something-else", sensor.icon)

    def test_icon_custom(self):
        data = dict(self.data)
        data["currency"] = "foobar"
        sensor = BalanceSensor(**data)

        self.assertEqual("something", sensor.icon)

    def test_available_true(self):
        data = dict(self.data)
        data["status"] = "enabled"
        sensor = BalanceSensor(**data)

        self.assertEqual(True, sensor.available)

    @unittest.mock.patch("nordigen_lib.sensor.datetime")
    def test_state_attributes(self, mocked_datatime):
        mocked_datatime.now.return_value = "last_update"
        sensor = BalanceSensor(**self.data)

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


class TestNordigenUnconfirmedSensor(unittest.TestCase):
    data = {
        "domain": "foobar",
        "coordinator": MagicMock(),
        "id": "account_id",
        "enduser_id": "enduser_id",
        "reference": "reference",
        "initiate": "initiate",
        "icons": {
            "auth": "something",
            "default": "something-else",
        },
        "config": "config",
    }

    def test_device_info(self):
        sensor = RequisitionSensor(**self.data)
        self.assertEqual(
            {
                "identifiers": {("foobar", "account_id")},
                "name": "reference enduser_id",
            },
            sensor.device_info,
        )

    def test_unique_id(self):
        sensor = RequisitionSensor(**self.data)

        self.assertEqual("reference", sensor.unique_id)

    def test_name(self):
        sensor = RequisitionSensor(**self.data)

        self.assertEqual("reference", sensor.name)

    def test_state_on(self):
        mocked_coordinator = MagicMock()
        mocked_coordinator.data = {"status": "LN"}

        sensor = RequisitionSensor(**{**self.data, "coordinator": mocked_coordinator})

        self.assertEqual(True, sensor.state)

    def test_state_off(self):
        mocked_coordinator = MagicMock()
        mocked_coordinator.data = {"status": "Not LN"}

        sensor = RequisitionSensor(**{**self.data, "coordinator": mocked_coordinator})

        self.assertEqual(False, sensor.state)

    def test_icon(self):
        sensor = RequisitionSensor(**self.data)

        self.assertEqual("something", sensor.icon)

    def test_available_true(self):
        sensor = RequisitionSensor(**self.data)

        self.assertEqual(True, sensor.available)

    @unittest.mock.patch("nordigen_lib.sensor.datetime")
    def test_state_attributes_not_linked(self, mocked_datatime):
        mocked_datatime.now.return_value = "last_update"
        mocked_coordinator = MagicMock()
        mocked_coordinator.data = {"accounts": ["account-1", "account-2"]}
        sensor = RequisitionSensor(**{**self.data, "coordinator": mocked_coordinator})

        print(sensor.state_attributes)
        self.assertEqual(
            {
                "initiate": "initiate",
                "info": (
                    "Authenticate to your bank with this link. This sensor will "
                    "monitor the requisition every few minutes and update once "
                    "authenticated. Once authenticated this sensor will be replaced "
                    "with the actual account sensor. If you will not authenticate "
                    "this service consider removing the config entry."
                ),
                "accounts": ["account-1", "account-2"],
                "last_update": "last_update",
            },
            sensor.state_attributes,
        )

    @unittest.mock.patch("nordigen_lib.sensor.datetime")
    def test_state_attributes_linked(self, mocked_datatime):
        mocked_datatime.now.return_value = "last_update"
        mocked_coordinator = MagicMock()
        mocked_coordinator.data = {"accounts": ["account-1", "account-2"], "status": "LN"}
        sensor = RequisitionSensor(**{**self.data, "coordinator": mocked_coordinator})

        print(sensor.state_attributes)
        self.assertEqual(
            {
                "initiate": "initiate",
                "info": (
                    "Authentication is complete, restart Home Assistant to start "
                    "collecting account data from 2 accounts."
                ),
                "accounts": ["account-1", "account-2"],
                "last_update": "last_update",
            },
            sensor.state_attributes,
        )


class TestBuildUnconfirmedSensor:
    @unittest.mock.patch("nordigen_lib.sensor.timedelta")
    @unittest.mock.patch("nordigen_lib.sensor.build_coordinator")
    @pytest.mark.asyncio
    async def test_build_requisition_sensor(self, mocked_build_coordinator, mocked_timedelta):
        hass = MagicMock()
        logger = MagicMock()
        requisition = {
            "id": "req-id",
            "enduser_id": "user-123",
            "reference": "ref-123",
            "initiate": "https://whatever.com",
            "config": "config",
        }

        const = {"DOMAIN": "foo", "ICON": {}}

        mocked_coordinator = MagicMock()
        mocked_coordinator.async_config_entry_first_refresh = AsyncMagicMock()
        mocked_build_coordinator.return_value = mocked_coordinator

        sensors = await build_requisition_sensor(hass, logger, requisition, const)

        case.assertEqual(1, len(sensors))

        sensor = sensors[0]
        assert isinstance(sensor, RequisitionSensor)
        assert sensor.name == "ref-123"

        mocked_timedelta.assert_called_with(minutes=2)
