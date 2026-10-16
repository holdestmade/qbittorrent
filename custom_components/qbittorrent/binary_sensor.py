"""Support for qBittorrent binary sensors."""

from collections.abc import Mapping
import ipaddress
from typing import cast, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_HOME_IP, CONF_HOME_IP_ENTITY, DOMAIN
from .coordinator import QBittorrentConfigEntry
from .entity import QBittorrentEntity

VPN_CONNECTED_DESCRIPTION = BinarySensorEntityDescription(
    key="vpn_connected",
    translation_key="vpn_connected",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
)


def _parse_ip(
    value: str | None,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse an IP address, returning None if it is empty or invalid."""
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: QBittorrentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up qBittorrent binary sensor entries."""
    options = config_entry.options
    if not options.get(CONF_HOME_IP) and not options.get(CONF_HOME_IP_ENTITY):
        # Remove the sensor if the home IP was cleared in the options
        entity_registry = er.async_get(hass)
        if entity_id := entity_registry.async_get_entity_id(
            "binary_sensor",
            DOMAIN,
            f"{config_entry.entry_id}-{VPN_CONNECTED_DESCRIPTION.key}",
        ):
            entity_registry.async_remove(entity_id)
        return

    async_add_entities(
        [
            QBittorrentVpnBinarySensor(
                config_entry.runtime_data, config_entry, VPN_CONNECTED_DESCRIPTION
            )
        ]
    )


class QBittorrentVpnBinarySensor(QBittorrentEntity, BinarySensorEntity):
    """Binary sensor that is on when qBittorrent's external IP is not the home IP."""

    @property
    def _home_ip(self) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        """Return the configured home IP address."""
        options = self.coordinator.config_entry.options
        if entity_id := options.get(CONF_HOME_IP_ENTITY):
            state = self.hass.states.get(entity_id)
            return _parse_ip(state.state if state else None)
        return _parse_ip(options.get(CONF_HOME_IP))

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if the VPN is connected."""
        home_ip = self._home_ip
        server_state = cast(Mapping, self.coordinator.data.get("server_state"))
        external_ips = {
            ip
            for key in ("last_external_address_v4", "last_external_address_v6")
            if (ip := _parse_ip(server_state.get(key))) is not None
        }
        if home_ip is None or not external_ips:
            return None
        return home_ip not in external_ips

    @override
    async def async_added_to_hass(self) -> None:
        """Track the home IP entity, if one is configured."""
        await super().async_added_to_hass()
        if entity_id := self.coordinator.config_entry.options.get(CONF_HOME_IP_ENTITY):
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [entity_id], self._handle_home_ip_change
                )
            )

    @callback
    def _handle_home_ip_change(self, event: Event[EventStateChangedData]) -> None:
        """Update when the home IP entity changes."""
        self.async_write_ha_state()
