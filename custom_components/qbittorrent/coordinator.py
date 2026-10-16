"""The QBittorrent coordinator."""

from collections.abc import Callable
from datetime import timedelta
from functools import partial
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
from homeassistant.core import CALLBACK_TYPE, HassJob, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# qBittorrent applies start/stop asynchronously, so refresh again shortly after
# an action to pick up the new torrent states.
ACTION_FOLLOW_UP_REFRESH_DELAY = 2

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
        self._unsub_follow_up_refresh: CALLBACK_TYPE | None = None
        self._follow_up_refresh_job = HassJob(
            self._async_follow_up_refresh, cancel_on_shutdown=True
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_call[T](
        self, func: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """Run a blocking client call in the executor, mapping client errors."""
        try:
            return await self.hass.async_add_executor_job(
                partial(func, *args, **kwargs)
            )
        except (LoginFailed, Forbidden403Error) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="login_error"
            ) from exc
        except APIConnectionError as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from exc

    @override
    async def _async_update_data(self) -> SyncMainDataDictionary:
        try:
            data = await self._async_call(self.client.sync_maindata)
            self._is_alternative_mode_enabled = (
                await self._async_call(self.client.transfer_speed_limits_mode) == "1"
            )
        except HomeAssistantError as exc:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key=exc.translation_key
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
        return await self._async_call(
            self.client.torrents_info, status_filter=torrent_filter
        )

    async def async_run_action(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """Run a qBittorrent client action and refresh data afterwards."""
        await self._async_call(func, *args, **kwargs)
        await self.async_refresh()

        if self._unsub_follow_up_refresh:
            self._unsub_follow_up_refresh()
        self._unsub_follow_up_refresh = async_call_later(
            self.hass, ACTION_FOLLOW_UP_REFRESH_DELAY, self._follow_up_refresh_job
        )

    async def _async_follow_up_refresh(self, _now: Any) -> None:
        """Refresh data once qBittorrent has applied an action."""
        self._unsub_follow_up_refresh = None
        await self.async_refresh()

    @override
    async def async_shutdown(self) -> None:
        """Cancel any pending follow-up refresh."""
        await super().async_shutdown()
        if self._unsub_follow_up_refresh:
            self._unsub_follow_up_refresh()
            self._unsub_follow_up_refresh = None

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
