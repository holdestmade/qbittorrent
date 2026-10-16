"""Support for monitoring the qBittorrent API."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import QBittorrentConfigEntry, QBittorrentDataCoordinator
from .entity import QBittorrentEntity


@dataclass(frozen=True, kw_only=True)
class QBittorrentSwitchEntityDescription(SwitchEntityDescription):
    """Describes qBittorrent switch."""

    is_on_func: Callable[[QBittorrentDataCoordinator], bool]
    turn_on_fn: Callable[[QBittorrentDataCoordinator], None]
    turn_off_fn: Callable[[QBittorrentDataCoordinator], None]
    toggle_func: Callable[[QBittorrentDataCoordinator], None]


SWITCH_TYPES: tuple[QBittorrentSwitchEntityDescription, ...] = (
    QBittorrentSwitchEntityDescription(
        key="alternative_speed",
        translation_key="alternative_speed",
        is_on_func=lambda coordinator: coordinator.get_alt_speed_enabled(),
        turn_on_fn=lambda coordinator: coordinator.set_alt_speed_enabled(True),
        turn_off_fn=lambda coordinator: coordinator.set_alt_speed_enabled(False),
        toggle_func=lambda coordinator: coordinator.toggle_alt_speed_enabled(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: QBittorrentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up qBittorrent switch entries."""

    coordinator = config_entry.runtime_data

    async_add_entities(
        QBittorrentSwitch(coordinator, config_entry, description)
        for description in SWITCH_TYPES
    )


class QBittorrentSwitch(QBittorrentEntity, SwitchEntity):
    """Representation of a qBittorrent switch."""

    entity_description: QBittorrentSwitchEntityDescription

    @property
    @override
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self.entity_description.is_on_func(self.coordinator)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on this switch."""
        await self.coordinator.async_run_action(
            self.entity_description.turn_on_fn, self.coordinator
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off this switch."""
        await self.coordinator.async_run_action(
            self.entity_description.turn_off_fn, self.coordinator
        )

    @override
    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the device."""
        await self.coordinator.async_run_action(
            self.entity_description.toggle_func, self.coordinator
        )
