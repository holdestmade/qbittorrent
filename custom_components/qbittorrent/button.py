"""Support for qBittorrent buttons."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from qbittorrentapi import Client

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import QBittorrentConfigEntry, QBittorrentDataCoordinator


@dataclass(frozen=True, kw_only=True)
class QBittorrentButtonEntityDescription(ButtonEntityDescription):
    """Entity description class for qBittorrent buttons."""

    press_fn: Callable[[Client], Callable[..., Any]]


BUTTON_TYPES: tuple[QBittorrentButtonEntityDescription, ...] = (
    QBittorrentButtonEntityDescription(
        key="start_all_torrents",
        translation_key="start_all_torrents",
        press_fn=lambda client: client.torrents_start,
    ),
    QBittorrentButtonEntityDescription(
        key="stop_all_torrents",
        translation_key="stop_all_torrents",
        press_fn=lambda client: client.torrents_stop,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: QBittorrentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up qBittorrent button entries."""

    coordinator = config_entry.runtime_data

    async_add_entities(
        QBittorrentButton(coordinator, config_entry, description)
        for description in BUTTON_TYPES
    )


class QBittorrentButton(CoordinatorEntity[QBittorrentDataCoordinator], ButtonEntity):
    """Representation of a qBittorrent button."""

    _attr_has_entity_name = True
    entity_description: QBittorrentButtonEntityDescription

    def __init__(
        self,
        coordinator: QBittorrentDataCoordinator,
        config_entry: QBittorrentConfigEntry,
        entity_description: QBittorrentButtonEntityDescription,
    ) -> None:
        """Initialize the qBittorrent button."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{config_entry.entry_id}-{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer="QBittorrent",
        )

    @override
    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_run_action(
            self.entity_description.press_fn(self.coordinator.client),
            torrent_hashes="all",
        )
