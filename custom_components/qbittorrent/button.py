"""Support for qBittorrent buttons."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from qbittorrentapi import Client

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import QBittorrentConfigEntry
from .entity import QBittorrentEntity


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


class QBittorrentButton(QBittorrentEntity, ButtonEntity):
    """Representation of a qBittorrent button."""

    entity_description: QBittorrentButtonEntityDescription

    @override
    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_run_action(
            self.entity_description.press_fn(self.coordinator.client),
            torrent_hashes="all",
        )
