<!-- Markdownlint-disable MD024 -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-08-27

### Added

- BREAKING: Enabled support for localStorage of summaries in Open Knowledge Format (OKF) bundles with YAML frontmatter, requiring explicit output directory or Notion configuration to ensure seamless transition from existing Notion-based deployments. [682ccab5](https://github.com/electrocucaracha/yt-summarizer/commit/682ccab538d8295ce27f7a9314057c0c062a758e)

## [2.0.0] - 2026-08-27

### Removed

- Simplified the development and lint environments by eliminating redundant formatting steps and removing the unnecessary dependency on pyink, as other tools such as black, ruff, and isort already cover necessary formatting and style checks. [2c576e28](https://github.com/electrocucaracha/yt-summarizer/commit/2c576e28f64948eec53e1648d1043245fcb4e4bf)

## [1.33.4] - 2026-08-27

### Changed

- Updated dependencies to their latest versions, ensuring compatibility and reducing maintenance burden by addressing upstream bugfixes, security patches, and new features. [77b414fc](https://github.com/electrocucaracha/yt-summarizer/commit/77b414fc5302280f22e88abc2ae32b8681309107)

## [1.33.3] - 2026-05-15

### Changed

- Upgraded the scheduled update workflow to securely use the WORKFLOW_TOKEN, suppressing secrets-outside-env warnings and addressing CVE-2026-44431 and CVE-2026-44432 by upgrading urllib3 to 2.7.0. [39bee61f](https://github.com/electrocucaracha/yt-summarizer/commit/39bee61f12def9770f5c0d376aeede261c92f895)

## [1.33.2] - 2026-05-08

### Changed

- The update workflow now uses the github.token environment variable for creating pull requests, replacing the need for a WORKFLOW_TOKEN secret. [6d63ed58](https://github.com/electrocucaracha/yt-summarizer/commit/6d63ed58ae9a55bb8ad3918a95167c16180f3989)

## [1.33.1] - 2026-05-06

### Changed

- Stabilized the formatter workflow, addressing super-linter failures and improving overall project stability with refined error handling and compliance with linter rules. [762bc849](https://github.com/electrocucaracha/yt-summarizer/commit/762bc84970b8c7b3c86a41263a877c7ca8df60c1)

## [1.33.0] - 2026-05-06

### Added

- Enabled robust handling of LLM providers and Notion data by resolving effective API base URLs, normalizing rich text fields, and improving error handling for transcript API failures, with comprehensive tests added to ensure compatibility and reliability. [271bb586](https://github.com/electrocucaracha/yt-summarizer/commit/271bb58690a6beed14b78b8aa9f7177c46c90757)

## [1.32.1] - 2026-05-06

### Changed

- Simplified the dependencies of workflow files by updating GitHub Actions to their latest available versions, including setup-uv, setup-go, Docker actions, and actions/ai-inference, thereby improving security and ensuring compatibility with upstream changes and bugfixes. [662b5e4b](https://github.com/electrocucaracha/yt-summarizer/commit/662b5e4be43b0c33c6e7cd6cb05681d0476cbfd7)

## [1.32.0] - 2026-05-06

### Added

- Enabled translation features by adding `googletrans` to the main dependencies and updating several other dependencies to newer versions, ensuring compatibility and keeping the environment up to date with upstream improvements and security fixes. [fc75447f](https://github.com/electrocucaracha/yt-summarizer/commit/fc75447f82e313f5a6f4c0230c428d7cb46cc838)

## [1.31.0] - 2026-05-06

### Added

- Enabled automated pre-commit checks for the repository, enforcing code quality and consistency before changes are committed, with tools for linting, formatting, and generating commit messages. [ad33c0ef](https://github.com/electrocucaracha/yt-summarizer/commit/ad33c0ef3ea2adc35fd82fc68fa0d9615657be45)

## [1.30.2] - 2026-04-24

### Changed

- Resolved Trivy vulnerability scan failures by updating the super-linter to version 8.6.0 and making related configuration changes to prevent crashes and suppress warnings. [716fbdcb](https://github.com/electrocucaracha/yt-summarizer/commit/716fbdcb8ba927b7f2850111cd322e3527c83906)

## [1.30.1] - 2026-04-24

### Fixed

- Resolved the issue of creating pull requests by passing the WORKFLOW_TOKEN to PR-creation actions in the update workflow, requiring no migration steps. [39bb4dbd](https://github.com/electrocucaracha/yt-summarizer/commit/39bb4dbd644bcf02bd30af3f21cc4071164f97ef)

## [1.30.0] - 2026-04-14

### Added

- Enabled support for the MCP Dev Summit 2026, a pivotal event for the Model Context Protocol (MCP) ecosystem, allowing the community to scale rapidly and tackle foundational challenges. [90081696](https://github.com/electrocucaracha/yt-summarizer/commit/90081696a4fd77e661388d4563361829fc9d6ec3)

## [1.29.5] - 2026-04-14

### Fixed

- The GitHub Actions, linter configuration, and project setup were updated to improve code quality and security, with no breaking changes introduced. [c3f6c8dd](https://github.com/electrocucaracha/yt-summarizer/commit/c3f6c8dd4bc5a182b06b3e358e0ab9428424cca7)

## [1.29.4] - 2026-04-14

### Changed

- Improved the documentation and usability of the `yt_summarizer` library by updating its docstrings and example usage. [f3750367](https://github.com/electrocucaracha/yt-summarizer/commit/f37503672b7a8213914bd73425b9ff551105b627)

## [1.29.3] - 2026-04-14

### Fixed

- Enforced semantic line breaks in Markdown to ensure consistent formatting and maintain high code quality for developers integrating with the yt-summarizer project via GitHub Copilot. [a8e83cb0](https://github.com/electrocucaracha/yt-summarizer/commit/a8e83cb09e3ef1754b45075d94a1bd18aba073ee)

## [1.29.2] - 2026-04-14

### Changed

- Updated the README.md file to accurately reflect the yt-summarizer tool's new features and capabilities. [17d58924](https://github.com/electrocucaracha/yt-summarizer/commit/17d58924c99306b73e171ffd67df0671569c56a6)

## [1.29.1] - 2026-04-13

### Changed

- Simplified markdownlint configuration to resolve CI failures in summary-samples.md, enabling longer line lengths and duplicate headings under different parent headings. [d972fbae](https://github.com/electrocucaracha/yt-summarizer/commit/d972fbae874733ae27cb5d9c8932781e997cfaa5)

## [1.29.0] - 2026-04-13

### Added

- Updated the documentation set to include reordered summary samples and updated links to the full sample collection. [c93f74ce](https://github.com/electrocucaracha/yt-summarizer/commit/c93f74ce637bc488fb2a398d6a3efa18236aed82)

## [1.28.1] - 2026-04-12

### Fixed

- Resolved line-length violations in the summary-samples.md file to adhere to MD013 and SEMBR conventions, resulting in a revised documentation file with improved formatting. [bc6dca6c](https://github.com/electrocucaracha/yt-summarizer/commit/bc6dca6c023c9455d4d9b83b885be2d104ec3705)

## [1.28.0] - 2026-04-12

### Added

- Improved the readability of documentation by introducing semantic breaks in Markdown prose. [83d26e72](https://github.com/electrocucaracha/yt-summarizer/commit/83d26e72966d1435a39de681ddf4670070494ef1)

## [1.27.0] - 2026-04-12

### Added

- Increased character limits for various summary types to 2000 for transcript and main points summaries and 6000 for executive summaries, requiring updates to user prompts and tests to reflect the new limits. [6468d195](https://github.com/electrocucaracha/yt-summarizer/commit/6468d1950419ddd33369b4a19bd25f5bb49ce5bf)

## [1.26.0] - 2026-04-12

### Added

- The summaries table in the README.md file has been modernized to include detailed descriptions of each event, providing a more comprehensive view of the content and improving understanding and access to the event summaries. [7421aa7b](https://github.com/electrocucaracha/yt-summarizer/commit/7421aa7b2a3a0c8f8d8478bff63cdfa044760df3)

## [1.25.1] - 2026-04-12

### Changed

- The required Python version has been hardened to 3.13, and several dependencies, including aiohttp and aiohappyeyeballs, have been updated, with aiohttp's version bumped to 3.13.5. [9045666d](https://github.com/electrocucaracha/yt-summarizer/commit/9045666d83f077bcf09872b4b9198c4f27321629)

## [1.25.0] - 2026-04-12

### Added

- Enabled generation of executive summaries for playlists through the CLI, where the CLI function now generates and prints a concise summary. [1ad79b39](https://github.com/electrocucaracha/yt-summarizer/commit/1ad79b390dc2cd2ed1d3e189def0a11bfcf4e568)

## [1.24.0] - 2026-04-12

### Added

- Optimized fetching pages from Notion databases by leveraging the data source query endpoint when available, reducing the number of API calls and increasing efficiency without altering the API contract or requiring migration steps. [3c540669](https://github.com/electrocucaracha/yt-summarizer/commit/3c540669e8bc882bcc535798e0785ed03414e11a)

## [1.23.1] - 2026-04-12

### Fixed

- The documentation for the yt-summarizer project now includes a note on how to troubleshoot unreachable LLM endpoints, providing users with the necessary information to resolve connection issues. [2e9a5c13](https://github.com/electrocucaracha/yt-summarizer/commit/2e9a5c1381d7021b928cd6c8e314d973ac7d1d3a)

## [1.23.0] - 2026-04-11

### Added

- Introduced comprehensive documentation and coding guidelines that emphasize clarity, accuracy, and user-centricity, enabling developers to write clean and maintainable code. [a92141cc](https://github.com/electrocucaracha/yt-summarizer/commit/a92141cc35b42896c46201b581ab92d43e0f77f5)

## [1.22.4] - 2026-04-11

### Fixed

- Resolved the warning about secrets outside of environment variables in the update.yml file and updated the Dockerfile to use the latest versions of gcc and musl-dev. [6dce804e](https://github.com/electrocucaracha/yt-summarizer/commit/6dce804ebc906714797b1a5421cb955fa4b3de76)

## [1.22.3] - 2026-03-25

### Fixed

- Skip artifact attestation on pull requests to avoid unnecessary checks. [0f0739c2](https://github.com/electrocucaracha/yt-summarizer/commit/0f0739c26748085353c94d43bdfb8b04f7c8e67f)

## [1.22.2] - 2026-03-25

### Changed

- Optimized code formatting and linting in the **init**.py and notion.py files to improve code quality and maintainability. [26add623](https://github.com/electrocucaracha/yt-summarizer/commit/26add623762663c3659353966bc1e3bebe84c7e7)

## [1.22.1] - 2026-03-25

### Fixed

- Simplified the YAML linting configuration format to remove an unnecessary line, resulting in a slightly more streamlined configuration file with no breaking changes or migration requirements. [b5e65c0c](https://github.com/electrocucaracha/yt-summarizer/commit/b5e65c0cf2fbbfcbf5aae75e1c6a562ad7237860)

## [1.22.0] - 2026-03-25

### Added

- Enabled improved visibility into playlist contents by displaying the title of a YouTube playlist and its videos. [945cfe37](https://github.com/electrocucaracha/yt-summarizer/commit/945cfe372d31a31e5fcea4d9e7511ece286a48e0)

## [1.21.2] - 2026-03-25

### Fixed

- Truncates text properties to 2000 characters to prevent errors when saving summaries and main points, logging warnings for affected users who save large text blocks. [f9a08d3f](https://github.com/electrocucaracha/yt-summarizer/commit/f9a08d3f6d8007f58d9cf0a832ddb442d73ce306)

## [1.21.1] - 2026-03-25

### Changed

- Enabled yamllint scanning for the project, resolving super-linter failures and improving code quality. [1700b030](https://github.com/electrocucaracha/yt-summarizer/commit/1700b03035b7a064677b2ff15a251fbbc9933cbd)

## [1.21.0] - 2026-03-25

### Added

- Enabled a click progress bar in the CLI to display the current item being processed during video processing, and introduced a specific connection error message with the failing API base and model values when the LLM endpoint is unavailable. [90991b85](https://github.com/electrocucaracha/yt-summarizer/commit/90991b85cc7fb3a1e4855ad734532c679a720056)

## [1.20.1] - 2026-03-17

### Changed

- Enabled super-linter CI to pass by updating multiple linter configurations and dependencies, resolving issues with pylint docstrings, mypy type annotations, action versions, shell, and ruff formatting, as well as fixing the EditorConfig linter and a KeyError in the og:title meta tag. [28339e40](https://github.com/electrocucaracha/yt-summarizer/commit/28339e401ad3b8fb4c000b200f03d34828448103)

## [1.20.0] - 2026-03-16

### Added

- Enabled seamless integration of multiple video processing and summarization for users, allowing them to efficiently process and summarize multiple videos from a single YouTube playlist. [3d23f2d9](https://github.com/electrocucaracha/yt-summarizer/commit/3d23f2d9a87d1c602f79ccd8d3ff743d8f453e46)

## [1.19.0] - 2026-03-08

### Added

- Enabled the processing of YouTube playlists, allowing the application to update the Notion database with video summaries from playlists. [61543ed0](https://github.com/electrocucaracha/yt-summarizer/commit/61543ed0554ee15a639bdab8a9aa3af5040cb529)

## [1.18.0] - 2026-03-07

### Added

- Enabled lint checks for code style by introducing a new tox environment that utilizes ruff, black, isort, and pyink, replacing outdated uvx installation scripts with Astral's uv installer. [f40d64a0](https://github.com/electrocucaracha/yt-summarizer/commit/f40d64a0adf5fc192bf3a762952cfd6c27308115)

## [1.17.0] - 2026-03-07

### Added

- Enabled users to run tests with a simplified command by introducing a new `test` target in the Makefile. [fb109c55](https://github.com/electrocucaracha/yt-summarizer/commit/fb109c55527afd704c5f2ea9d673b89c9e36a90f)

## [1.16.0] - 2026-03-07

### Added

- Enabled additional code style and formatting checks through the introduction of linters uvx, ruff, black, isort, and pyink, requiring users to run additional commands to format their code and leading to improved code consistency and adherence to best practices. [49ad2eca](https://github.com/electrocucaracha/yt-summarizer/commit/49ad2eca2bacefc9f9dcf1d2c53f7abab4b3ee20)

## [1.15.2] - 2026-03-06

### Changed

- Optimized the project's CI pipeline by resolving linter failures due to improved handling of empty response files, suppressed false positives, and corrected code style issues, ensuring all checks pass successfully. [1b3cead6](https://github.com/electrocucaracha/yt-summarizer/commit/1b3cead6b457b582d1e365ebb842dd9372252317)

## [1.15.1] - 2026-03-06

### Changed

- Enabled comprehensive error handling for age-restricted videos, improved code formatting, and updated configuration files to ensure compatibility with linters and formatters. [49312b05](https://github.com/electrocucaracha/yt-summarizer/commit/49312b05dfbbea03d27e763f71000acf3a8aa7b7)

## [1.15.0] - 2026-03-06

### Added

- Enabled detailed documentation for the process_playlist method through the addition of a docstring, providing users with improved understanding of its arguments, return value, and processing flow without introducing any breaking behavior or API contract changes. [56549ebb](https://github.com/electrocucaracha/yt-summarizer/commit/56549ebb7b84aa9fe8e345838839ff431e7d63aa)

## [1.14.0] - 2026-03-06

### Added

- Enabled the processing of YouTube playlists via the CLI, allowing users to update the Notion database with video summaries. [ec1d04c1](https://github.com/electrocucaracha/yt-summarizer/commit/ec1d04c1a699cb01f6c7f870946f60d491db8e12)

## [1.13.0] - 2026-02-18

### Added

- Enabled a clean make target, allowing users to easily remove temporary files and directories generated by the build process, with the 'lint' target now depending on it. [d51aa81f](https://github.com/electrocucaracha/yt-summarizer/commit/d51aa81fbf5e9a0e58b95c6889dbe5b9a56d7b5b)

## [1.12.3] - 2026-02-18

### Fixed

- Resolved Kubernetes deployment configuration issues to meet best practices and improve security by specifying resource requests and limits, and updating security settings. [8c3ed26e](https://github.com/electrocucaracha/yt-summarizer/commit/8c3ed26ee572a3f3be3e34154cf6682fdef341fb)

## [1.12.2] - 2026-02-18

### Fixed

- Resolved documentation linting issues by updating the GitHub Actions workflow to include necessary permissions for accessing documentation files. [4c48c39e](https://github.com/electrocucaracha/yt-summarizer/commit/4c48c39e16633244b0a64e7534920a4374fbb4f5)

## [1.12.1] - 2026-02-18

### Fixed

- Resolved potential encoding-related errors in file handling by ensuring consistent encoding of file contents. [ad14a634](https://github.com/electrocucaracha/yt-summarizer/commit/ad14a63470f0aeebcb46979d5d4df454f883194b)

## [1.12.0] - 2026-02-17

### Added

- Optimized the YouTube summarizer service to update only modified records, resulting in improved performance and reduced database load. [2c2f7dd6](https://github.com/electrocucaracha/yt-summarizer/commit/2c2f7dd6c56a573b6be6ef7060738cd51171276a)

## [1.11.2] - 2026-02-17

### Changed

- Updated the dependencies to their latest versions with no impact on system behavior. [c47c9aec](https://github.com/electrocucaracha/yt-summarizer/commit/c47c9aec015cfde43dee04497fdeae389c057273)

## [1.11.1] - 2026-02-17

### Fixed

- Resolved the Docker build dependencies to use newer versions of gcc and musl-dev, requiring users who build the Docker image to adjust their build process accordingly. [aa5dc54e](https://github.com/electrocucaracha/yt-summarizer/commit/aa5dc54ee2bd1b5881f7bad8f130e9e14e4c8e75)

## [1.11.0] - 2026-02-17

### Added

- Enabled runme support for easier development and testing, updating the GitHub workflows for documentation and linter checks, and the contributing guide to reflect new installation and verification processes. [a7c58e84](https://github.com/electrocucaracha/yt-summarizer/commit/a7c58e8495a287a3a9e7cc09e55596c2dea0a5a9)

## [1.10.1] - 2026-02-16

### Fixed

- The GitHub workflow now correctly listens for pushes and pull requests on the "master" branch, resolving a workflow behavior issue. [f545ffe2](https://github.com/electrocucaracha/yt-summarizer/commit/f545ffe28cc1a59b82caad4cf580030dc06b82fc)

## [1.10.0] - 2026-02-16

### Added

- Enabled the automation of the summarization process on a daily basis by providing a Kubernetes deployment resource that runs a container with the yt-summarizer image, connecting to a Notion database and using a specified LLM model. [e2e829d0](https://github.com/electrocucaracha/yt-summarizer/commit/e2e829d0028457aaf6ff799625fbe20f07877313)

## [1.9.2] - 2026-02-16

### Fixed

- Standardized the project's code formatting with the adoption of the `fmt` tool, which now automatically reformats code to conform to the project's coding style, affecting the `ci/update_versions.sh` script and the `README.md` file. [4e1dde7d](https://github.com/electrocucaracha/yt-summarizer/commit/4e1dde7d3b4db6740f847bfd2ae66ac448c609b3)

## [1.9.1] - 2026-02-16

### Fixed

- Resolved several linting issues across the codebase including APK package version pinning, line length adjustments, import ordering corrections, and Python type annotation fixes. [8801dcbd](https://github.com/electrocucaracha/yt-summarizer/commit/8801dcbd4f59a09b34333183353d292d5db73337)

## [1.9.0] - 2026-02-16

### Added

- Enabled automated version updates on Fridays at midnight, triggered by a schedule and workflow dispatch, with no breaking changes to APIs or existing functionality. [63e3d465](https://github.com/electrocucaracha/yt-summarizer/commit/63e3d465649eda79da907399ff25b3da0f27fbde)

## [1.8.0] - 2026-02-16

### Added

- Introduced automatic code formatting capabilities through the addition of a fmt target to the build process, allowing maintainers to easily format the codebase using tools like shfmt, yamlfmt, and prettier. [94c46dbe](https://github.com/electrocucaracha/yt-summarizer/commit/94c46dbe2a9f786b06cb3b30dca7e33d548b6ef4)

## [1.7.0] - 2026-02-16

### Added

- Enabled a visual representation of the tool's functionality in the README.md file, providing users with a clearer understanding of how it works. [e341c1ae](https://github.com/electrocucaracha/yt-summarizer/commit/e341c1ae20a5f4b4524dd8e5b950fae7734f58ed)

## [1.6.0] - 2026-02-16

### Added

- Enabled contributors to more easily get started with the project by providing a pull request template and a CONTRIBUTING.md file that outlines development setup, code standards, testing, and commit/pull request process. [6a833d87](https://github.com/electrocucaracha/yt-summarizer/commit/6a833d877e7e7696d3e6c5a144698aed8fc08a6e)

## [1.5.0] - 2026-02-16

### Added

- Automated code quality checks and syntax validation are now enabled through the addition of a linter CI task that includes multiple linters and provides detailed analysis. [3ac246f9](https://github.com/electrocucaracha/yt-summarizer/commit/3ac246f952b3e90e4ab077bcd30c049e3b6f6496)

## [1.4.0] - 2026-02-16

### Added

- Automated build and Docker image publishing are now enabled for main branch pushes and tag pushes, streamlining the project's build and deployment process. [a553a03c](https://github.com/electrocucaracha/yt-summarizer/commit/a553a03c19b19fcd9ffdb8e2c8b0819e2dc52818)

## [1.3.0] - 2026-02-16

### Added

- Introduced a new configuration option that allows users to specify a custom Notion API token file location, requiring a valid token file for the application to function correctly. [84dc7f0b](https://github.com/electrocucaracha/yt-summarizer/commit/84dc7f0b71b4fcd0a303b92f7fd50b2270d2e390)

## [1.2.0] - 2026-02-16

### Added

- Enabled users to package the application into a container for easier deployment with the addition of a Dockerfile, which minimizes dependencies and includes environment variables for configuration. [9a0ff98a](https://github.com/electrocucaracha/yt-summarizer/commit/9a0ff98a6c01aefefa9d20bab476f0c834016ca8)

## [1.1.0] - 2026-02-16

### Added

- Enabled improved integration with Notion, enhanced YouTube transcript extraction, and more flexible configuration options for language models, resulting in improved functionality for content curation, research archives, team collaboration, and knowledge base development. [bebcbf21](https://github.com/electrocucaracha/yt-summarizer/commit/bebcbf210b97628865b5a0ab6e3cc21594346b6c)

## [1.0.0] - 2026-02-15

### Added

- Enabled a YouTube video summarizer application that retrieves videos, extracts transcripts, generates summaries using Large Language Models, and updates a Notion database with analysis results. [67debed3](https://github.com/electrocucaracha/yt-summarizer/commit/67debed3f03776325f4e3cd62021f310b21a53ad)
