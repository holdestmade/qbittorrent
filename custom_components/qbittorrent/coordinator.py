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

from .const import (
    ACTIVE_TORRENT_STATES,
    CONF_ACTIVE_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL,
    DEFAULT_ACTIVE_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# qBittorrent applies start/stop asynchronously, so refresh again shortly after
# an action to pick up the new torrent states.
ACTION_FOLLOW_UP_REFRESH_DELAY = 2

type QBittorrentConfigEntry = ConfigEntry[QBittorrentDataCoordinator]


def _is_active(data: SyncMainDataDictionary) -> bool:
    """Return whether any torrent is active or data is being transferred."""
    server_state = data.get("server_state") or {}
    if server_state.get("dl_info_speed") or server_state.get("up_info_speed"):
        return True
    torrents = data.get("torrents") or {}
    return any(
        torrent.get("state") in ACTIVE_TORRENT_STATES for torrent in torrents.values()
    )


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
        options = config_entry.options
        self._idle_interval = timedelta(
            seconds=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        self._active_interval = timedelta(
            seconds=options.get(CONF_ACTIVE_SCAN_INTERVAL, DEFAULT_ACTIVE_SCAN_INTERVAL)
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=self._idle_interval,
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
        # Poll faster while torrents are active; the next refresh is scheduled
        # with this interval once this update completes.
        self.update_interval = (
            self._active_interval if _is_active(data) else self._idle_interval
        )
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
