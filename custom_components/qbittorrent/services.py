"""Services for the qBittorrent integration."""

from typing import Any

import probatio

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import (
    ATTR_DELETE_FILES,
    ATTR_TORRENTS,
    DOMAIN,
    SERVICE_DELETE_TORRENTS,
    SERVICE_GET_ALL_TORRENTS,
    SERVICE_GET_TORRENTS,
    SERVICE_START_TORRENTS,
    SERVICE_STOP_TORRENTS,
    STATE_ATTR_ALL_TORRENTS,
    STATE_ATTR_TORRENTS,
    TORRENT_FILTER,
)
from .coordinator import QBittorrentConfigEntry, QBittorrentDataCoordinator
from .helpers import format_torrents

TORRENTS_SCHEMA = probatio.Schema(
    {
        probatio.Required(ATTR_DEVICE_ID): cv.string,
        probatio.Required(ATTR_TORRENTS): probatio.All(cv.ensure_list, [cv.string]),
    }
)

DELETE_TORRENTS_SCHEMA = TORRENTS_SCHEMA.extend(
    {probatio.Optional(ATTR_DELETE_FILES, default=False): cv.boolean}
)


def _get_coordinator(service_call: ServiceCall) -> QBittorrentDataCoordinator:
    """Get the coordinator for the device targeted by a service call."""
    hass = service_call.hass
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(service_call.data[ATTR_DEVICE_ID])

    if device_entry is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_device",
            translation_placeholders={"device_id": service_call.data[ATTR_DEVICE_ID]},
        )

    entry_id = None

    for key, value in device_entry.identifiers:
        if key == DOMAIN:
            entry_id = value
            break
    else:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_entry_id",
            translation_placeholders={"device_id": entry_id or ""},
        )

    entry: QBittorrentConfigEntry | None = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_entry_id",
            translation_placeholders={"device_id": entry_id},
        )
    return entry.runtime_data


async def _handle_get_torrents(service_call: ServiceCall) -> dict[str, Any] | None:
    coordinator = _get_coordinator(service_call)
    items = await coordinator.get_torrents(service_call.data[TORRENT_FILTER])
    info = format_torrents(items)
    return {
        STATE_ATTR_TORRENTS: info,
    }


async def _handle_start_torrents(service_call: ServiceCall) -> None:
    coordinator = _get_coordinator(service_call)
    hashes = coordinator.resolve_torrent_hashes(service_call.data[ATTR_TORRENTS])
    await coordinator.async_run_action(
        coordinator.client.torrents_start, torrent_hashes=hashes
    )


async def _handle_stop_torrents(service_call: ServiceCall) -> None:
    coordinator = _get_coordinator(service_call)
    hashes = coordinator.resolve_torrent_hashes(service_call.data[ATTR_TORRENTS])
    await coordinator.async_run_action(
        coordinator.client.torrents_stop, torrent_hashes=hashes
    )


async def _handle_delete_torrents(service_call: ServiceCall) -> None:
    coordinator = _get_coordinator(service_call)
    hashes = coordinator.resolve_torrent_hashes(service_call.data[ATTR_TORRENTS])
    await coordinator.async_run_action(
        coordinator.client.torrents_delete,
        torrent_hashes=hashes,
        delete_files=service_call.data[ATTR_DELETE_FILES],
    )


async def _handle_get_all_torrents(
    service_call: ServiceCall,
) -> dict[str, Any] | None:
    hass = service_call.hass
    torrents = {}

    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator: QBittorrentDataCoordinator = entry.runtime_data
        items = await coordinator.get_torrents(service_call.data[TORRENT_FILTER])
        torrents[entry.entry_id] = format_torrents(items)

    return {
        STATE_ATTR_ALL_TORRENTS: torrents,
    }


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the services for the qBittorrent integration."""

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_TORRENTS,
        _handle_get_torrents,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_ALL_TORRENTS,
        _handle_get_all_torrents,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_TORRENTS,
        _handle_start_torrents,
        schema=TORRENTS_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_TORRENTS,
        _handle_stop_torrents,
        schema=TORRENTS_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_TORRENTS,
        _handle_delete_torrents,
        schema=DELETE_TORRENTS_SCHEMA,
    )
