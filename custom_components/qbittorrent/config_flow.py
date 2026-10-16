"""Config flow for qBittorrent."""

import ipaddress
import logging
from typing import Any, override

import probatio
from qbittorrentapi import APIConnectionError, Forbidden403Error, LoginFailed

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
)

from .const import CONF_HOME_IP, CONF_HOME_IP_ENTITY, DEFAULT_NAME, DEFAULT_URL, DOMAIN
from .helpers import setup_client

_LOGGER = logging.getLogger(__name__)

HOME_IP_FIELDS = {
    probatio.Optional(CONF_HOME_IP): TextSelector(),
    probatio.Optional(CONF_HOME_IP_ENTITY): EntitySelector(
        EntitySelectorConfig(domain=["sensor", "input_text"])
    ),
}

USER_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_URL, default=DEFAULT_URL): str,
        probatio.Required(CONF_USERNAME): str,
        probatio.Required(probatio.Secret(CONF_PASSWORD)): str,
        probatio.Optional(CONF_VERIFY_SSL, default=True): bool,
        **HOME_IP_FIELDS,
    }
)

OPTIONS_SCHEMA = probatio.Schema(HOME_IP_FIELDS)


def _validate_home_ip(
    user_input: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    """Validate the home IP options and return (options, errors)."""
    options: dict[str, str] = {}
    home_ip = (user_input.get(CONF_HOME_IP) or "").strip()
    home_ip_entity = user_input.get(CONF_HOME_IP_ENTITY)

    if home_ip and home_ip_entity:
        return options, {"base": "home_ip_and_entity"}
    if home_ip:
        try:
            ipaddress.ip_address(home_ip)
        except ValueError:
            return options, {CONF_HOME_IP: "invalid_ip"}
        options[CONF_HOME_IP] = home_ip
    if home_ip_entity:
        options[CONF_HOME_IP_ENTITY] = home_ip_entity
    return options, {}


class QbittorrentConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for the qBittorrent integration."""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "QbittorrentOptionsFlow":
        """Get the options flow for this handler."""
        return QbittorrentOptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a user-initiated config flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match({CONF_URL: user_input[CONF_URL]})
            options, errors = _validate_home_ip(user_input)
            if not errors:
                try:
                    await self.hass.async_add_executor_job(
                        setup_client,
                        user_input[CONF_URL],
                        user_input[CONF_USERNAME],
                        user_input[CONF_PASSWORD],
                        user_input[CONF_VERIFY_SSL],
                    )
                except (LoginFailed, Forbidden403Error):
                    errors = {"base": "invalid_auth"}
                except APIConnectionError:
                    errors = {"base": "cannot_connect"}
                else:
                    data = {
                        key: user_input[key]
                        for key in (
                            CONF_URL,
                            CONF_USERNAME,
                            CONF_PASSWORD,
                            CONF_VERIFY_SSL,
                        )
                    }
                    return self.async_create_entry(
                        title=DEFAULT_NAME, data=data, options=options
                    )

        schema = self.add_suggested_values_to_schema(USER_DATA_SCHEMA, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class QbittorrentOptionsFlow(OptionsFlowWithReload):
    """Options flow for the qBittorrent integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the home IP options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            options, errors = _validate_home_ip(user_input)
            if not errors:
                return self.async_create_entry(data=options)

        schema = self.add_suggested_values_to_schema(
            OPTIONS_SCHEMA, user_input or self.config_entry.options
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
