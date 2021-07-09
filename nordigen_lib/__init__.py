import requests

from nordigen import Client

PLATFORMS = ["sensor"]


def config_schema(vol, cv, CONST):
    return vol.Schema(
        {
            CONST["DOMAIN"]: vol.Schema(
                {
                    vol.Required(CONST["TOKEN"]): cv.string,
                    vol.Optional(CONST["DEBUG"], default=False): cv.string,
                    vol.Required(CONST["REQUISITIONS"]): [
                        {
                            vol.Required(CONST["ENDUSER_ID"]): cv.string,
                            vol.Required(CONST["ASPSP_ID"]): cv.string,
                            vol.Optional(CONST["REFRESH_RATE"], default=240): cv.string,
                            vol.Optional(CONST["AVAILABLE_BALANCE"], default=True): cv.string,
                            vol.Optional(CONST["BOOKED_BALANCE"], default=True): cv.string,
                            vol.Optional(CONST["HISTORICAL_DAYS"], default=30): cv.string,
                            vol.Optional(CONST["IGNORE_ACCOUNTS"], default=[]): [cv.string],
                            vol.Optional(CONST["ICON_FIELD"], default="mdi:currency-usd-circle"): cv.string,
                        },
                    ],
                },
                extra=vol.ALLOW_EXTRA,
            )
        },
        extra=vol.ALLOW_EXTRA,
    )


def get_config(configs, requisition):
    """Get the associated config."""
    for config in configs:
        ref = "{}-{}".format(config["enduser_id"], config["aspsp_id"])
        if requisition["reference"] == ref:
            return config


def get_reference(enduser_id, aspsp_id, *args, **kwargs):
    return "{}-{}".format(enduser_id, aspsp_id)


def unique_ref(id, account):
    for key in ["iban", "bban", "resourceId"]:
        val = account.get(key)
        if val:
            return val
    return id


def get_account(fn, id, requisition, LOGGER, ignored=[], config={}):
    account = {}
    try:
        account = fn(id)
        account = account.get("account", {})
    except requests.exceptions.HTTPError as error:
        LOGGER.error("Unable to fetch account details from Nordigen: %s", error)
        return

    if not account.get("iban"):
        LOGGER.warn("Strange account: %s | %s", requisition, account)

    ref = unique_ref(id, account)

    if ref in ignored:
        LOGGER.info("Account ignored due to configuration :%s", ref)
        return

    account = {
        "id": id,
        "unique_ref": ref,
        "name": account.get("name"),
        "owner": account.get("ownerName"),
        "currency": account.get("currency"),
        "product": account.get("product"),
        "status": account.get("status"),
        "bic": account.get("bic"),
        "iban": account.get("iban"),
        "bban": account.get("bban"),
        "requisition": {
            "id": requisition.get("id"),
            "status": requisition.get("status"),
            "reference": requisition.get("reference"),
            "redirect": requisition.get("redirect"),
            "enduser_id": requisition.get("enduser_id"),
        },
        "config": config,
    }
    LOGGER.info("Loaded account info for account # :%s", id)
    return account


def matched_requisition(ref, requisitions):
    """Get the requisition for current ref."""
    for requisition in requisitions:
        if requisition["reference"] == ref:
            return requisition

    return {}


def get_or_create_requisition(fn_create, fn_initiate, requisitions, reference, enduser_id, aspsp_id, LOGGER):
    requisition = matched_requisition(reference, requisitions)
    if not requisition:
        requisition = fn_create(
            **{
                "redirect": "http://127.0.0.1/",
                "reference": reference,
                "enduser_id": enduser_id,
                "agreements": [],
            }
        )
        LOGGER.debug("No requisition found, created :%s", requisition)

    if requisition.get("status") != "LN":
        print(requisition)
        requisition = {
            **requisition,
            **fn_initiate(
                **{
                    "id": requisition["id"],
                    "aspsp_id": aspsp_id,
                }
            ),
            "requires_auth": True,
        }
        LOGGER.info("Authenticate and accept connection and restart :%s", requisition["initiate"])

    return requisition


def get_accounts(client, configs, LOGGER, CONST):
    """Get a list of the accounts."""
    accounts = []
    requisitions = []
    try:
        requisitions = client.requisitions.list()["results"]
    except (requests.exceptions.HTTPError, KeyError) as error:
        LOGGER.error("Unable to fetch Nordigen requisitions: %s", error)

    for config in configs:
        requisition = get_or_create_requisition(
            fn_create=client.requisitions.create,
            fn_initiate=client.requisitions.initiate,
            requisitions=requisitions,
            reference=get_reference(**config),
            aspsp_id=config[CONST["ASPSP_ID"]],
            enduser_id=config[CONST["ENDUSER_ID"]],
            LOGGER=LOGGER,
        )

        accounts.extend(handle_requisition(client, config, LOGGER, CONST, requisition))
    return accounts


def handle_requisition(client, config, LOGGER, CONST, requisition):
    """Handle requisition."""
    if requisition.get("requires_auth"):
        return [requisition]

    accounts = []
    LOGGER.debug("Handling requisition :%s", requisition.get("id"))
    for account_id in requisition.get("accounts", []):
        accounts.append(
            get_account(
                fn=client.account.details,
                id=account_id,
                requisition=requisition,
                LOGGER=LOGGER,
                ignored=config[CONST["IGNORE_ACCOUNTS"]],
                config=config,
            )
        )

    return accounts


def entry(hass, config, CONST, LOGGER):
    """Nordigen platform entry."""
    domain_config = config.get(CONST["DOMAIN"])
    if domain_config is None:
        LOGGER.warning("Nordigen not configured")
        return True

    LOGGER.debug("config: %s", config[CONST["DOMAIN"]])
    client = Client(token=domain_config[CONST["TOKEN"]])
    hass.data[CONST["DOMAIN"]] = {
        "client": client,
    }

    accounts = get_accounts(client=client, configs=domain_config[CONST["REQUISITIONS"]], LOGGER=LOGGER, CONST=CONST)
    discovery = {"accounts": accounts}
    for platform in PLATFORMS:
        hass.helpers.discovery.load_platform(platform, CONST["DOMAIN"], discovery, config)

    return True
