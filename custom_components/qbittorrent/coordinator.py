"""The QBittorrent coordinator."""

from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any, override

from qbittorrentapi import (
    APIConnectionError,
    Client,
    Forbidden403Error,
    LoginFailed,
    SyncMainDataDictionary,
    TorrentInfoList,
)
from qbittorrentapi.torrents import TorrentStatusesT

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type QBittorrentConfigEntry = ConfigEntry[QBittorrentDataCoordinator]


class QBittorrentDataCoordinator(DataUpdateCoordinator[SyncMainDataDictionary]):
    """Coordinator for updating QBittorrent data."""

    config_entry: QBittorrentConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: QBittorrentConfigEntry, client: Client
    ) -> None:
        """Initialize coordinator."""
        self.client = client
        self._is_alternative_mode_enabled = False
        # self.main_data: dict[str, int] = {}
        self.total_torrents: dict[str, int] = {}
        self.active_torrents: dict[str, int] = {}
        self.inactive_torrents: dict[str, int] = {}
        self.paused_torrents: dict[str, int] = {}
        self.seeding_torrents: dict[str, int] = {}
        self.started_torrents: dict[str, int] = {}

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    @override
    async def _async_update_data(self) -> SyncMainDataDictionary:
        try:
            data = await self.hass.async_add_executor_job(self.client.sync_maindata)
            self._is_alternative_mode_enabled = (
                await self.hass.async_add_executor_job(
                    self.client.transfer_speed_limits_mode
                )
                == "1"
            )
        except (LoginFailed, Forbidden403Error) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="login_error"
            ) from exc
        except APIConnectionError as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from exc
        return data

    def set_alt_speed_enabled(self, is_enabled: bool) -> None:
        """Set the alternative speed mode."""
        self.client.transfer_toggle_speed_limits_mode(is_enabled)

    def toggle_alt_speed_enabled(self) -> None:
        """Toggle the alternative speed mode."""
        self.client.transfer_toggle_speed_limits_mode()

    def get_alt_speed_enabled(self) -> bool:
        """Get the alternative speed mode."""
        return self._is_alternative_mode_enabled

    async def get_torrents(self, torrent_filter: TorrentStatusesT) -> TorrentInfoList:
        """Async method to get QBittorrent torrents."""
        try:
            torrents = await self.hass.async_add_executor_job(
                lambda: self.client.torrents_info(torrent_filter)
            )
        except (LoginFailed, Forbidden403Error) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="login_error"
            ) from exc
        except APIConnectionError as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from exc

        return torrents

    async def async_run_action(self, func: Callable[..., Any], **kwargs: Any) -> None:
        """Run a qBittorrent client action and refresh data afterwards."""
        try:
            await self.hass.async_add_executor_job(lambda: func(**kwargs))
        except (LoginFailed, Forbidden403Error) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="login_error"
            ) from exc
        except APIConnectionError as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from exc
        await self.async_request_refresh()

    def resolve_torrent_hashes(self, torrents: list[str]) -> list[str]:
        """Resolve torrent names or hashes to hashes of known torrents."""
        known = self.data.get("torrents") or {}
        hashes: list[str] = []
        unknown: list[str] = []
        for item in torrents:
            if item.lower() in known:
                hashes.append(item.lower())
                continue
            matches = [h for h, t in known.items() if t.get("name") == item]
            if matches:
                hashes.extend(matches)
            else:
                unknown.append(item)
        if unknown:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_torrents",
                translation_placeholders={"torrents": ", ".join(unknown)},
            )
        return hashes
