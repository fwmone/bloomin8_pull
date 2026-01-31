# BLOOMIN8 Pull – Home Assistant Custom Integration

`bloomin8_pull` is a custom integration for Home Assistant that allows content from a [**BLOOMIN8 e-ink picture frame**](https://www.bloomin8.com/) to be retrieved from the Home Assistant server using a pull mechanism. It implements the [Schedule Pull API](https://github.com/ARPOBOT-BLOOMIN8/eink_canvas_home_assistant_component/blob/main/docs/Schedule_Pull_API.md) that BLOOMIN8 has provided as a code example. The official [BLOOMIN8 integration](https://github.com/ARPOBOT-BLOOMIN8/eink_canvas_home_assistant_component?tab=readme-ov-file) is independent of this. It is not required for this integration, but can of course be installed independently.

The integration is aimed in particular at users who do not just want to use BLOOMIN8 as a passive picture frame, but want to control content, status, or image changes **automatically and context-dependently**. It is still in the very early stages of its development cycle and was created primarily out of my personal desire to be able to display images locally on the frame.

## 📖 Table of content

- [BLOOMIN8 Pull – Home Assistant Custom Integration](#bloomin8-pull--home-assistant-custom-integration)
  - [📖 Table of content](#-table-of-content)
  - [✨ Features](#-features)
  - [🧩 Requirements](#-requirements)
  - [📦 Installation](#-installation)
    - [Option A: Installation via HACS (recommended)](#option-a-installation-via-hacs-recommended)
    - [Option B: Manual installation](#option-b-manual-installation)
  - [⚙️ Configuration](#️-configuration)
    - [Configuration of the BLOOMIN8 picture frame](#configuration-of-the-bloomin8-picture-frame)
    - [Testing](#testing)
  - [🚫 Limitations](#-limitations)
  - [📊 Entities](#-entities)
  - [🧠 Application examples](#-application-examples)
  - [🛠️ Development \& status](#️-development--status)
  - [🐞 Report a bug](#-report-a-bug)
  - [🙏 Note](#-note)

## ✨ Features

- Pull-based retrieval of content/status information
- Provision of sensors for further processing in automations
- Local communication (no cloud requirement)

## 🧩 Requirements

- Home Assistant **2024.12** or newer. I personally always work on the current version of Home Assistant, so I cannot guarantee compatibility with older versions.
- The BLOOMIN8 picture frame must be able to access the Home Assistant server.
- The images to be retrieved must be available on the Home Assistant server, optimized for the frame, which means: in the correct resolution (1600x1200px for the 13.3" frame), in JPEG format, and already adjusted for the Spectra 6 display, e.g., brightened or increased in saturation. In my setup, I synchronize the images from a local [Immich](https://immich.app/) server and then optimize them automatically. I wrote separate scripts for this, which I will post on GitHub when I get a chance. 
- The images must be in <image_dir> (see configuration below) as JPEGs and end with the suffix “.jpg”.

## 📦 Installation

### Option A: Installation via HACS (recommended)

1. Open **HACS → Integrations**
2. Click on **“Custom Repositories”**
3. Add this repository: https://github.com/fwmone/bloomin8_pull, Category: **Integration**
4. Install **BLOOMIN8 Pull**
5. Restart Home Assistant

### Option B: Manual installation

1. Download this repository
2. Copy the custom_components/bloomin8_pull folder to: <config>/custom_components/bloomin8_pull (this is usually /config/custom_components)
3. Restart Home Assistant

## ⚙️ Configuration

The integration is currently configured **via YAML**. I added a section to <configuration.yaml> using Home Assistant's file editor:

```yaml
bloomin8_pull:
  access_token: !secret bloomin8_pull_token
  image_dir: /media/bloomin8
  publish_dir: /config/www/bloomin8
  publish_webpath: /local/bloomin8
  wake_up_hours: "6,18" # 6:00 and 18:00
  orientation: P   # P = portrait format, L = landscape format
```

|key|explanation|
|----------|---------|
|*access_token*|A token specified by you that the picture frame uses for identification. This should usually be “!secret bloomin8_pull_token.” In *secrets.yaml* (see below), you then store the actual token and transfer this configured token to the picture frame via “token” (see also below).|
|*image_dir*|This is where all the images on the Home Assistant server are stored, from which the pull endpoint selects one for the picture frame.|
|*publish_dir*|The directory that can be accessed via a web browser. This is usually /config/www, which contains a directory for the picture frame, e.g. bloomin8. The pull endpoint copies the selected image here and replaces it with a new one the next time it is retrieved.|
|*publish_webpath*|The web path to “publish_dir”. For “/config/www/bloomin8,” this is usually “/local/bloomin8.” Only the path is configured here, not the server address. You specify the server address via the configuration of *upstream_url* below the image frame. For the image frame, the complete URL would therefore be http://<IP-AND-PORT-OF-HOME-ASSISTANT>/local/bloomin8|
|*wake_up_hours*|At which time should the picture frame retrieve a new image? Specify in comma-separated hours, e.g., "6,18" for 6:00 and 18:00. The component takes care of the device's firmware bug of waking up too early (e. g. 5:47 instead of 6:00) for up to 30 minutes and then skips to the next time slot (-> do not send 6:00 again, but 18:00).|
|*orientation*|The orientation of the picture frame - P = portrait format, L = landscape format.|

And for the access token in <secrets.yaml>:

```yaml
bloomin8_pull_token: “<YOUR_TOKEN_HERE>”
```

### Configuration of the BLOOMIN8 picture frame

The [configuration](https://github.com/ARPOBOT-BLOOMIN8/eink_canvas_home_assistant_component/blob/main/docs/Schedule_Pull_API.md) contains the crucial services under “1. Device Endpoint: /upstream/pull_settings”. For configuration, the picture frame must be accessible via Wi-Fi, so it must be woken up via the BLOOMIN8 mobile app before the services can be accessed. Once configured, it automatically wakes up at the time set in <next_cron_time> and then connects to the Home Assistant server. 

Example:

```json
PUT http://{device_ip}/upstream/pull_settings
Content-Type: application/json

{
    “upstream_on”: true,
    “upstream_url”: “http://<IP-AND-PORT-OF-HOME-ASSISTANT>”,
    “token”: “<YOUR_TOKEN_HERE>”,
    “cron_time”: “2025-11-01T08:30:00Z”
}
```

For IP-AND-PORT-OF-HOME-ASSISTANT, for example, http://192.168.0.1:8123. The framework then automatically appends the path to the pull service.

### Testing

You can use the following commands to test:

Test whether the custom component works and provides the pull service:


```bash
curl -i -H “X-Access-Token: <YOUR_TOKEN_HERE>” “http://<IP-AND-PORT-OF-HOME-ASSISTANT>/eink_pull?device_id=abc&pull_id=uuid&cron_time=2026-01-04T09:00:00Z&battery=80”
```

Test whether the success call works after the frame has retrieved the image:

```bash
curl -i -H “X-Access-Token: <YOUR_TOKEN_HERE>” “http://<IP-AND-PORT-OF-HOME-ASSISTANT>/eink_signal?pull_id=uuid&success=1”
```

This allows you to “configure” your picture frame:

```bash
curl -X PUT “http://<IP-OF-BLOOMIN8-FRAME>/upstream/pull_settings” -H "Content-Type: application/json“ -d ”{\“upstream_on\”:true,\“upstream_url\”:\“http://<IP-AND-PORT-OF-HOME-ASSISTANT>\”,\“token\”:\" <YOUR_TOKEN_HERE>\“,\”cron_time\“:\”2026-01-17T05:00:00Z\“}”
```

<cron_time> must be UTC time.

## 🚫 Limitations

Currently, only one frame is supported. Actually, you can use with several frames but they have to be in the same orientation.

## 📊 Entities

After successful setup, the integration provides two entities:

- sensor.bloomin8_battery (the frame reports its charge level with each pull)
- binary_sensor.bloomin8_last_pull_success (the frame confirms the retrieval; as an attribute, the sensor returns when it was last retrieved)

The entities can be used directly in dashboards, automations, or scripts.

## 🧠 Application examples

- Automatic image change depending on time of day or weather
- Display of context-related content (e.g., calendar, notes, moods)
- Integration into existing smart home scenarios

## 🛠️ Development & status

This integration is currently under active development. 
Feedback, bug reports, and pull requests are welcome.

## 🐞 Report a bug

Please use the issue tracker on GitHub:

👉 https://github.com/fwmone/bloomin8_pull/issues

## 🙏 Note

This integration has no official connection to the manufacturer of BLOOMIN8.