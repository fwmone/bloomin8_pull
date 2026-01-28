# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
