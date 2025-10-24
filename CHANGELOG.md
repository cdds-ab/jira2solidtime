# Changelog

## 0.1.0 (2025-10-24)


### ⚠ BREAKING CHANGES

* radical simplification - remove bloat, keep only core functionality

### Features

* add change detection to prevent unnecessary UPDATEs ([88fdb7a](https://github.com/cdds-ab/jira2solidtime/commit/88fdb7ab5940892126db1099493c1de19e6cba6f))
* add comprehensive Docker and YAML security scanning ([49cf0cd](https://github.com/cdds-ab/jira2solidtime/commit/49cf0cd6c43df9e22526e792c0793b74b5306d55))
* add comprehensive status badges to README ([4d998ae](https://github.com/cdds-ab/jira2solidtime/commit/4d998ae8a869312da33f51f7de0ad3d9d9bebb87))
* add Docker security checks to pre-commit hooks ([51f610d](https://github.com/cdds-ab/jira2solidtime/commit/51f610df0dc120d364c1d045e2cb3ca199a9e0f4))
* add Jira issue summary to time entry descriptions ([f1beee1](https://github.com/cdds-ab/jira2solidtime/commit/f1beee1441f3c7f90cf7899ed1c33f21fd3b0dc1))
* comprehensive history tracking with detailed sync actions ([6235c8a](https://github.com/cdds-ab/jira2solidtime/commit/6235c8a0434a19bff153e9917c69725a8eb13d76))
* implement centralized configuration management system ([d1a7354](https://github.com/cdds-ab/jira2solidtime/commit/d1a735418f177af01f8e61961e0991b62f3b8059))
* implement full sync with UPDATE/DELETE and detailed action tracking ([5d2ea65](https://github.com/cdds-ab/jira2solidtime/commit/5d2ea65960f99fd976b86d141533098fa2c35b7e))
* simulate feature to establish clean release pattern ([2dc3bce](https://github.com/cdds-ab/jira2solidtime/commit/2dc3bce8a637a844f0dc933d614476349f0a2c81))


### Bug Fixes

* add config.json to .gitignore to prevent credential exposure ([3a139e8](https://github.com/cdds-ab/jira2solidtime/commit/3a139e85743d249282a47fe6c5df5175eea6da78))
* add entrypoint script and fix data directory permissions ([8f43595](https://github.com/cdds-ab/jira2solidtime/commit/8f4359534427a380900e7b0f1076501856eccb8a))
* add explicit GitHub token for release-please ([c743652](https://github.com/cdds-ab/jira2solidtime/commit/c7436520cc09ff2c03414a6a5a47926c23c4d743))
* add mypy and ruff to pre-commit hooks ([f168cb2](https://github.com/cdds-ab/jira2solidtime/commit/f168cb20ec0c580cc9cf483cdc40d663188731aa))
* add uv.lock and update Dockerfile for reproducible builds ([665bacd](https://github.com/cdds-ab/jira2solidtime/commit/665bacd66d2b860650f7f37ec3bcc6b7c8f00ec3))
* always try UPDATE to detect deleted entries (404) ([f4d8901](https://github.com/cdds-ab/jira2solidtime/commit/f4d8901eb6f48e52df9ede11717a79307b5cd603))
* clean descriptions and handle broken mappings gracefully ([cbf078d](https://github.com/cdds-ab/jira2solidtime/commit/cbf078dcfbf046acf9d3bac0ed2e1685366643a1))
* configure release-please properly ([f020a7a](https://github.com/cdds-ab/jira2solidtime/commit/f020a7a0d064089ff448d2bf2e3b444fa7b630fa))
* correct Solidtime API payload and member_id retrieval ([4d21b47](https://github.com/cdds-ab/jira2solidtime/commit/4d21b4788d6ebb1e4b5c7f2e882c567d32c84a23))
* critical security and documentation updates ([133af22](https://github.com/cdds-ab/jira2solidtime/commit/133af225c3ea2c15edd65cd787b836224bcc7c16))
* disable prerelease mode for clean 0.2.0 release ([0c63bf3](https://github.com/cdds-ab/jira2solidtime/commit/0c63bf393ec30af9191346bec7303419ff8b5a12))
* fetch Jira issue key from API when not in Tempo worklog ([da81c7e](https://github.com/cdds-ab/jira2solidtime/commit/da81c7e3d2080e8bd572dc3fe19b3b2a1019fa7e))
* hadolint Docker security scan warnings ([0174131](https://github.com/cdds-ab/jira2solidtime/commit/01741311e8f9b0921af7da84e0048b144309eb36))
* implement external sync schedule configuration ([2f917ce](https://github.com/cdds-ab/jira2solidtime/commit/2f917ce0f1217723fad3c124e2d4cdea83d812ba))
* implement two-mode Docker setup for development and production ([700674e](https://github.com/cdds-ab/jira2solidtime/commit/700674eb81b20ed8b49a45d9ddeae326495877a7))
* move gitignore comments to separate lines ([9492dc1](https://github.com/cdds-ab/jira2solidtime/commit/9492dc14309174141b637943ae2336847a70f41d))
* prevent duplicates by checking entry existence before UPDATE ([63eaafe](https://github.com/cdds-ab/jira2solidtime/commit/63eaafee1ded0eed538c2eae5625259ff1ceb456))
* remove all hardcoded customer data and strengthen security ([7feafb8](https://github.com/cdds-ab/jira2solidtime/commit/7feafb812f6a6b507481283059e20d7b41a8694d))
* remove broken import from web/__init__.py ([03598c1](https://github.com/cdds-ab/jira2solidtime/commit/03598c18c06272df56faa0fcf027c9d5cc2e80fb))
* remove readonly variable export from rebuild.sh ([c8e764f](https://github.com/cdds-ab/jira2solidtime/commit/c8e764fef85d678bc79b5737c8b8effcd0bfc285))
* revert to simple UPDATE-404-CREATE pattern (no existence check) ([8956844](https://github.com/cdds-ab/jira2solidtime/commit/89568440023fd167164ed565a939e79a532f708a))
* standardize Python version requirement to 3.11+ ([d4dd94b](https://github.com/cdds-ab/jira2solidtime/commit/d4dd94bc3e7b2714661541c7f910c92d2847234b))
* update CI workflow for simplified architecture ([b9b98aa](https://github.com/cdds-ab/jira2solidtime/commit/b9b98aa6dddbc0de0a90c226320869c48b2a044a))
* update release workflow for simplified architecture ([e80b476](https://github.com/cdds-ab/jira2solidtime/commit/e80b4761840ccc5611295c842da8c64c93f3d5c6))
* update Solidtime API endpoints to include organization_id ([47e8926](https://github.com/cdds-ab/jira2solidtime/commit/47e8926502717679401b2a2ecc652ea38b94219d))
* update to non-deprecated googleapis/release-please-action ([01f6cc7](https://github.com/cdds-ab/jira2solidtime/commit/01f6cc75a580e47e19e06199261cbd06460a997a))
* use Tempo 'description' field instead of 'comment' for worklog text ([78a9b56](https://github.com/cdds-ab/jira2solidtime/commit/78a9b5648223901032bd8ef36b35575ce8b170d0))


### Documentation

* enhance README with sync features and process details ([76febc6](https://github.com/cdds-ab/jira2solidtime/commit/76febc6155294cac97d385b90e94c1a0b962999f))


### Code Refactoring

* radical simplification - remove bloat, keep only core functionality ([82d4da0](https://github.com/cdds-ab/jira2solidtime/commit/82d4da078b699d9b0449306feae76ab05aa579e8))
