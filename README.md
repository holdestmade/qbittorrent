# qBittorrent for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/holdestmade/qbittorrent/actions/workflows/validate.yml/badge.svg)](https://github.com/holdestmade/qbittorrent/actions/workflows/validate.yml)

A custom integration for monitoring and controlling a [qBittorrent](https://www.qbittorrent.org/) client from Home Assistant through its Web API.

It replaces Home Assistant's built-in qBittorrent integration (it uses the same `qbittorrent` domain), adding sensors, buttons and actions on top of what the built-in integration provides.

## Credits

This integration is based on the [qBittorrent integration](https://www.home-assistant.io/integrations/qbittorrent) that ships with Home Assistant, and has been enhanced with the help of AI ([Claude](https://claude.ai) by Anthropic).

## Requirements

- Home Assistant 2026.10.0 or newer
- qBittorrent with the Web UI enabled (Tools → Options → Web UI)

## Installation

### HACS (recommended)

1. In HACS, open the menu in the top right and choose **Custom repositories**.
2. Add `https://github.com/holdestmade/qbittorrent` with the type **Integration**.
3. Search for **qBittorrent** in HACS and download it.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/qbittorrent` into the `custom_components` folder of your Home Assistant configuration directory.
2. Restart Home Assistant.

## Configuration

Go to **Settings → Devices & services → Add integration**, search for **qBittorrent** and enter:

| Field | Description |
| --- | --- |
| URL | Address of the qBittorrent Web UI, for example `http://192.168.1.10:8080` |
| Username | Web UI username |
| Password | Web UI password |
| Verify SSL certificate | Turn off if the Web UI uses a self-signed certificate |
| Home IP address | Optional. Your public IP address when *not* using a VPN |
| Home IP address entity | Optional. An entity (sensor or input_text) whose state is your public IP address when not using a VPN |

Data is refreshed every 30 seconds.

The home IP settings can be changed later from the integration's **Configure** button. Set one of them (not both) to enable the **VPN connected** binary sensor.

## Entities

### Sensors

| Sensor | Description | Enabled by default |
| --- | --- | --- |
| Status | `idle`, `downloading`, `seeding` or `up_down` | Yes |
| Connection status | `connected`, `firewalled` or `disconnected` | Yes |
| Download speed | Current download speed | Yes |
| Upload speed | Current upload speed | Yes |
| Download speed limit | Current global download limit | No |
| Upload speed limit | Current global upload limit | No |
| All-time download | Total data downloaded | Yes |
| All-time upload | Total data uploaded | Yes |
| Global ratio | Overall share ratio | No |
| All torrents | Number of torrents | Yes |
| Active torrents | Torrents downloading or uploading | Yes |
| Inactive torrents | Stalled torrents | Yes |
| Paused torrents | Stopped / paused torrents | Yes |
| Errored torrents | Torrents with errors or missing files | Yes |
| External IPv4 address | Last external IPv4 address detected by qBittorrent | Yes |
| External IPv6 address | Last external IPv6 address detected by qBittorrent | No |

The external address sensors read `last_external_address_v4` / `last_external_address_v6` from qBittorrent and show as unknown until qBittorrent has detected an address.

### Binary sensors

| Binary sensor | Description |
| --- | --- |
| VPN connected | On when qBittorrent's external IP address differs from your home IP address, off when it matches (qBittorrent is not behind the VPN). Only created when a home IP address or home IP entity is configured. |

The sensor is unknown until qBittorrent has detected an external address, or while the home IP entity has no valid IP address. When an entity is used, the sensor updates as soon as that entity changes. A good source is a sensor from your router that reports its WAN IP address, as that does not go through the VPN.

Example: stop all torrents if the VPN drops:

```yaml
automation:
  - alias: Stop torrents when VPN drops
    triggers:
      - trigger: state
        entity_id: binary_sensor.qbittorrent_vpn_connected
        to: "off"
    actions:
      - action: button.press
        target:
          entity_id: button.qbittorrent_stop_all_torrents
```

### Buttons

| Button | Description |
| --- | --- |
| Start all torrents | Starts (resumes) every torrent |
| Stop all torrents | Stops (pauses) every torrent |

### Switches

| Switch | Description |
| --- | --- |
| Alternative speed | Turns qBittorrent's alternative speed limits on or off |

## Actions

All actions that target a single client take a `device_id` of the qBittorrent device. Torrents can be given by name or by info hash; if several torrents share a name, all of them are affected.

| Action | Description |
| --- | --- |
| `qbittorrent.get_torrents` | Returns the torrents of one client, filtered by state |
| `qbittorrent.get_all_torrents` | Returns the torrents of every configured client, filtered by state |
| `qbittorrent.start_torrents` | Starts one or more torrents |
| `qbittorrent.stop_torrents` | Stops one or more torrents |
| `qbittorrent.delete_torrents` | Removes one or more torrents; set `delete_files: true` to also delete the downloaded data |

### Examples

Stop a torrent:

```yaml
action: qbittorrent.stop_torrents
data:
  device_id: 0123456789abcdef0123456789abcdef
  torrents:
    - ubuntu-24.04-desktop-amd64.iso
```

Pause everything when the house goes into "away" mode:

```yaml
automation:
  - alias: Pause torrents when away
    triggers:
      - trigger: state
        entity_id: alarm_control_panel.home
        to: armed_away
    actions:
      - action: button.press
        target:
          entity_id: button.qbittorrent_stop_all_torrents
```

List active torrents:

```yaml
action: qbittorrent.get_torrents
data:
  device_id: 0123456789abcdef0123456789abcdef
  torrent_filter: active
response_variable: torrents
```

## Troubleshooting

To get debug logs, add the following to `configuration.yaml` and restart:

```yaml
logger:
  logs:
    custom_components.qbittorrent: debug
    qbittorrentapi: debug
```

Problems and feature requests: [GitHub issues](https://github.com/holdestmade/qbittorrent/issues).

## License

[MIT](LICENSE)
