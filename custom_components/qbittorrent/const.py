"""Constants for qBittorrent."""

from typing import Final

DOMAIN: Final = "qbittorrent"

DEFAULT_NAME = "qBittorrent"
DEFAULT_URL = "http://127.0.0.1:8080"

STATE_ATTR_TORRENTS = "torrents"
STATE_ATTR_ALL_TORRENTS = "all_torrents"

STATE_UP_DOWN = "up_down"
STATE_SEEDING = "seeding"
STATE_DOWNLOADING = "downloading"

SERVICE_GET_TORRENTS = "get_torrents"
SERVICE_GET_ALL_TORRENTS = "get_all_torrents"
TORRENT_FILTER = "torrent_filter"
SERVICE_START_TORRENTS = "start_torrents"
SERVICE_STOP_TORRENTS = "stop_torrents"
SERVICE_DELETE_TORRENTS = "delete_torrents"
ATTR_TORRENTS = "torrents"
ATTR_DELETE_FILES = "delete_files"

CONF_HOME_IP = "home_ip"
CONF_HOME_IP_ENTITY = "home_ip_entity"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_ACTIVE_SCAN_INTERVAL = "active_scan_interval"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_ACTIVE_SCAN_INTERVAL = 5

# Torrent states that mean qBittorrent is doing work worth polling faster for
ACTIVE_TORRENT_STATES = frozenset(
    {
        "downloading",
        "forcedDL",
        "metaDL",
        "forcedMetaDL",
        "uploading",
        "forcedUP",
        "checkingDL",
        "checkingUP",
        "checkingResumeData",
        "moving",
    }
)
