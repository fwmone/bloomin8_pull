# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.3] - 2026-10-21

### Added
- **Local brand assets:** Added native support for Home Assistant 2026.3+ by bundling integration icons directly in `custom_components/bloomin8_pull/brand/`.
- Included standard and high-resolution (`@2x`) icons for both light and dark themes.
- Brand assets are now served locally by Home Assistant, without requiring the external Home Assistant Brands repository.

### Changed
- No changes to integration functionality or configuration.

### Contributors
- Special thanks to [@frenck](https://github.com/frenck) for contributing the local brand assets in [PR #2](https://github.com/fwmone/bloomin8_pull/pull/2).

## [0.2.2] - 2026-09-26

### Changed
- Prefixed per-device entity names with `BLOOMIN8 Pull` so newly created Home Assistant entity IDs use the `bloomin8_pull_...` namespace.
- This avoids collisions with similarly named entities from the official BLOOMIN8 integration.

## [0.2.1] - 2026-09-26

### Fixed
- Removed YAML-platform entity-to-device attachment that caused Home Assistant to warn that an entity was being attached to a device without a Config Entry.
- Included the configured BLOOMIN8 device name directly in each entity name instead.
- Keeps the integration compatible with its current YAML-based setup while avoiding a Home Assistant 2027.8 deprecation path.

## [0.2.0] - 2026-09-26

### Added - BREAKING CHANGE
- Added first-class support for multiple BLOOMIN8 frames.
- Added mandatory `devices:` configuration keyed by each frame's actual `device_id`.
- Added per-device `name`, `orientation`, and `wake_up_hours` settings.
- Added independent per-device state for battery, last pull result, last seen timestamp, pull enabled state, and last image URL.
- Added one battery sensor, pull-success binary sensor, and pull-enabled switch per configured device.
- Added per-device recent-image history to avoid repetitions independently on each frame.
- Added persistent `pull_id` -> `device_id` mapping so `/eink_signal` updates the frame that initiated the corresponding pull.
- Outstanding pull mappings are persisted and expire after 24 hours.
- Added rejection of unknown `device_id` values with HTTP 400.
- Added automatic migration of the legacy 0.1.x state file to the first configured device.

### Changed - BREAKING CHANGE
- `wake_up_hours` and `orientation` moved from global configuration to each entry under `devices:`.
- `image_dir` is now treated as a root directory containing `portrait/` and `landscape/` subdirectories.
- Image selection uses the subdirectory matching each device's configured orientation (`P` -> `portrait`, `L` -> `landscape`).
- Published images are now stored below a per-device subdirectory under `publish_dir`, preventing one frame from deleting another frame's image during overlapping pulls.
- Pull enable/disable state is now per device instead of global.
- Recent-image history is now stored per device instead of globally.
- Entity unique IDs are now derived from the BLOOMIN8 `device_id`.

### Migration notes
- Existing YAML using global `wake_up_hours` and `orientation` must be converted to the new `devices:` structure.
- Existing image pools must be moved into `portrait/` and/or `landscape/` below `image_dir`.
- Existing 0.1.x entities may remain as orphaned Entity Registry entries and can be removed after verifying the new entities.
- The old global recent-image history is not migrated automatically. A new per-device history is created on first use.

## [0.1.17] - 2026-07-19

### Added
- "X-Server-Timestamp" header sends the server time as Unix timestamp so that the frame can use it

## [0.1.16] - 2026-06-21

### Changed
- Fixed an issue where some BLOOMIN8 devices could fail to refresh images when identical published filenames were reused. Images are now published using a timestamp-based filename to ensure reliable refresh behaviour.

## [0.1.15] - 2026-05-11

### Changed
- Returning HTTP 200 (with status 204) when there is no new picture available so that frame still gets next_cron_time. HTTP 204 may not contain additional information.
- Fixing wrong logger output
- Removing deprecated python dt.datetime.utcnow() call

## [0.1.14] - 2026-04-25

### Changed
- changing max length of file list from 50 to 250 to have better randomization

## [0.1.13] - 2026-04-07

### Changed
- removed ```bloomin8_battery``` icon to use Home Assistant default icon

## [0.1.12] - 2026-02-09

### Changed
- changed ```bloomin8_battery``` to SensorDeviceClass.BATTERY

## [0.1.11] - 2026-02-09

### Added
- Added `switch.bloomin8_pull_enabled` to enable or disable image pulling
- Pull disabling allows pausing image rotation (e.g. during vacations)
- Switch state is persisted across Home Assistant restarts

### Changed
- `/eink_pull` endpoint now respects the pull enabled state
- When pulling is disabled, the endpoint responds without serving a new image

## [0.1.10] - 2026-01-30

### Changed

- take care of device time drift of up to 30 minutes, e. g. device is set to wake up at 6am but wakes at 5:47 (seems to be a firmware bug) - do not set the time to 6am again but to the next time slot (e. g. 18:00 when wake_up_hours is "6,18").
- translated all comments to English

## [0.1.9] - 2026-01-29

### Added - BREAKING CHANGE

- parameter "wake_up_hours" instead of "next_interval_minutes" because BLOOMIN8 frame does not wake at exact time but seems to drift a few minutes. "wake_up_hours" is a comma-separated list of hours you want the frame to wake at, e. g. "6,18" = 6:00 and 18:00. "next_interval_minutes" does not work anymore, sorry.

## [0.1.8] - 2026-01-28

### Changed

- larger history of last shown pictures (50% instead of 25%, min 5, max 50)

## [0.1.7] - 2026-01-25

### Added

- history of last shown pictures to avoid repetitions

## [0.1.6] - 2026-01-22

### Changed

- file suffix only .jpg possible due to limitations of Bloomin8 frame

## [0.1.5] - 2026-01-22

### Changed

- file suffix does not need to be _opt.jpg anymore - .jpg or .jpeg are both possible now

## [0.1.4] - 2026-01-22

### Added

- added "publish_webpath" configuration parameter that is the counterpart of "publish_dir" on filesystem level
- added "orientation" configuration parameter so that the endpoint can be used with both portrait and landscape frames
- more description and explanation in README.md

### Changed

- moved default path of media folder to /media/bloomin8 so that it is more easy to exclude of Home Assistant backups

## [0.1.3] - 2026-01-20

### Fixed

- Typo in view.py

## [0.1.2] - 2026-01-20

### Fixed

- Updating blocking calls to async calls
- Bloomin8 to "official" spelling BLOOMIN8

## [0.1.1] - 2026-01-20

### Fixed

- Wrong imports after refactoring

## [0.1.0] - 2026-01-20

### Added

- Initial release of the BLOOMIN8 Pull custom integration.
