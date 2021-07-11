"""Platform for sensor integration."""
import random
from datetime import datetime, timedelta

from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed


def random_balance(*args, **kwargs):
    """Generate random balances for testing."""
    return {
        "balances": [
            {
                "balanceAmount": {
                    "amount": random.randrange(0, 100000, 1) / 100,
                    "currency": "SEK",
                },
                "balanceType": "interimAvailable",
                "creditLimitIncluded": True,
            },
            {
                "balanceAmount": {
                    "amount": random.randrange(0, 100000, 1) / 100,
                    "currency": "SEK",
                },
                "balanceType": "interimBooked",
            },
        ]
    }


def balance_update(LOGGER, async_executor, fn, account_id):
    """Fetch latest information."""

    async def update():
        LOGGER.debug("Getting balance for account :%s", account_id)
        try:
            data = (await async_executor(fn, account_id))["balances"]
        except Exception as err:
            raise UpdateFailed(f"Error updating Nordigen sensors: {err}")

        data = {
            **{
                "closingBooked": None,
                "expected": None,
                "openingBooked": None,
                "interimAvailable": None,
                "interimBooked": None,
                "forwardAvailable": None,
                "nonInvoiced": None,
            },
            **{balance["balanceType"]: balance["balanceAmount"]["amount"] for balance in data},
        }

        LOGGER.debug("balance for %s : %s", account_id, data)
        return data

    return update


def requisition_update(LOGGER, async_executor, fn, requisition_id):
    """Fetch latest information."""

    async def update():
        LOGGER.debug("Getting requisition for account :%s", requisition_id)
        try:
            data = await async_executor(fn, requisition_id)
        except Exception as err:
            raise UpdateFailed(f"Error updating Nordigen sensors: {err}")

        LOGGER.debug("balance for %s : %s", requisition_id, data)
        return data

    return update


def build_coordinator(hass, LOGGER, updater, interval, reference):
    return DataUpdateCoordinator(
        hass,
        LOGGER,
        name="nordigen-balance-{}".format(reference),
        update_method=updater,
        update_interval=interval,
    )


async def build_account_sensors(hass, LOGGER, account, CONST, debug):
    fn = random_balance if debug else hass.data[CONST["DOMAIN"]]["client"].account.balances
    updater = balance_update(
        LOGGER=LOGGER,
        async_executor=hass.async_add_executor_job,
        fn=fn,
        account_id=account["id"],
    )
    interval = timedelta(minutes=int(account["config"][CONST["REFRESH_RATE"]]))
    balance_coordinator = build_coordinator(
        hass=hass, LOGGER=LOGGER, updater=updater, interval=interval, reference=account.get("unique_ref")
    )

    await balance_coordinator.async_config_entry_first_refresh()

    LOGGER.debug("listeners: %s", balance_coordinator._listeners)

    entities = []
    if account["config"][CONST["AVAILABLE_BALANCE"]] is not False:
        entities.append(
            NordigenBalanceSensor(
                domain=CONST["DOMAIN"],
                icons=CONST["ICON"],
                balance_type="interimAvailable",
                coordinator=balance_coordinator,
                **account,
            )
        )

    if account["config"][CONST["BOOKED_BALANCE"]] is not False:
        entities.append(
            NordigenBalanceSensor(
                domain=CONST["DOMAIN"],
                icons=CONST["ICON"],
                balance_type="interimBooked",
                coordinator=balance_coordinator,
                **account,
            )
        )

    return entities


async def build_unconfirmed_sensor(hass, LOGGER, requisition, CONST, debug):
    updater = requisition_update(
        LOGGER=LOGGER,
        async_executor=hass.async_add_executor_job,
        fn=hass.data[CONST["DOMAIN"]]["client"].requisitions.by_id,
        requisition_id=requisition["id"],
    )
    interval = timedelta(minutes=2)
    coordinator = build_coordinator(
        hass=hass, LOGGER=LOGGER, updater=updater, interval=interval, reference=requisition.get("reference")
    )

    await coordinator.async_config_entry_first_refresh()

    LOGGER.debug("listeners: %s", coordinator._listeners)

    return [
        NordigenUnconfirmedSensor(
            domain=CONST["DOMAIN"],
            icons=CONST["ICON"],
            coordinator=coordinator,
            **requisition,
        )
    ]


async def build_sensors(hass, LOGGER, account, CONST, debug=False):
    if account.get("requires_auth") is True:
        return await build_unconfirmed_sensor(hass, LOGGER, account, CONST, debug)

    return await build_account_sensors(hass, LOGGER, account, CONST, debug)


class NordigenUnconfirmedSensor(CoordinatorEntity):
    def __init__(self, coordinator, domain, id, enduser_id, reference, initiate, icons, *args, **kwargs):
        """Unconfirmed sensor entity."""
        self._domain = domain
        self._id = id
        self._enduser_id = enduser_id
        self._reference = reference
        self._initiate = initiate
        self._icons = icons

        super().__init__(coordinator)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(self._domain, self._id)},
            "name": "{} {}".format(self._reference, self._enduser_id),
        }

    @property
    def unique_id(self):
        """Return the ID of the sensor."""
        return self._reference

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._reference

    @property
    def state(self):
        """Return the sensor state."""
        return self.coordinator.data.get("status") == "LN"

    @property
    def state_attributes(self):
        """Return State attributes."""
        info = (
            "Authenticate to your bank with this link. This sensor will "
            "monitor the requisition every few minutes and update once "
            "authenticated. "
            ""
            "Once authenticated this sensor will be replaced with the actual "
            "account sensor. If you will not authenticate this service "
            "consider removing the config entry."
        )

        if self.state:
            count = len(self.coordinator.data.get("accounts"))
            info = (
                "Authentication is complete, restart Home Assistant to "
                f"start collecting account data from {count} accounts."
            )

        return {
            "initiate": self._initiate,
            "info": info,
            "accounts": self.coordinator.data.get("accounts"),
            "last_update": datetime.now(),
        }

    @property
    def icon(self):
        """Return the entity icon."""
        return self._icons.get("auth")

    @property
    def available(self) -> bool:
        """Return True when account is enabled."""
        return True


class NordigenBalanceSensor(CoordinatorEntity):
    """Nordigen Balance Sensor."""

    def __init__(
        self,
        domain,
        icons,
        coordinator,
        id,
        iban,
        bban,
        unique_ref,
        name,
        owner,
        currency,
        product,
        status,
        bic,
        requisition,
        balance_type,
        config,
    ):
        """Initialize the sensor."""
        self._icons = icons
        self._domain = domain
        self._balance_type = balance_type
        self._id = id
        self._iban = iban
        self._bban = bban
        self._unique_ref = unique_ref
        self._name = name
        self._owner = owner
        self._currency = currency
        self._product = product
        self._status = status
        self._bic = bic
        self._requisition = requisition
        self._config = config

        super().__init__(coordinator)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(self._domain, self._requisition["id"])},
            "name": "{} {}".format(self._bic, self.name),
        }

    @property
    def unique_id(self):
        """Return the ID of the sensor."""
        return "{}-{}".format(self._unique_ref, self.balance_type)

    @property
    def balance_type(self):
        """Return the sensors balance type."""
        return self._balance_type.replace("interim", "").lower()

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} {}".format(self._unique_ref, self.balance_type)

    @property
    def state(self):
        """Return the sensor state."""
        return round(float(self.coordinator.data[self._balance_type]), 2)

    @property
    def state_attributes(self):
        """Return State attributes."""
        return {
            "balance_type": self.balance_type,
            "iban": self._iban,
            "unique_ref": self._unique_ref,
            "name": self._name,
            "owner": self._owner,
            "product": self._product,
            "status": self._status,
            "bic": self._bic,
            "enduser_id": self._requisition["enduser_id"],
            "reference": self._requisition["reference"],
            "last_update": datetime.now(),
        }

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._currency

    @property
    def icon(self):
        """Return the entity icon."""
        return self._icons.get(self._currency, self._icons.get("default"))

    @property
    def available(self) -> bool:
        """Return True when account is enabled."""
        return True
