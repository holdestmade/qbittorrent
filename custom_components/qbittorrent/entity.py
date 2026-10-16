"""Base entity for the qBittorrent integration."""

from homeassistant.const import CONF_URL
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import QBittorrentConfigEntry, QBittorrentDataCoordinator


class QBittorrentEntity(CoordinatorEntity[QBittorrentDataCoordinator]):
    """Base class for qBittorrent entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: QBittorrentDataCoordinator,
        config_entry: QBittorrentConfigEntry,
        entity_description: EntityDescription,
    ) -> None:
        """Initialize the qBittorrent entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{config_entry.entry_id}-{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer="QBittorrent",
            configuration_url=config_entry.data[CONF_URL],
        )
