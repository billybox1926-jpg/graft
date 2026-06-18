# Security Policy

Graft is a small local CLI, but security reports are welcome if you find behavior that could harm users or their files.

## Supported versions

Security reports should target the latest released version and the current `master` branch.

## Reporting a concern

If GitHub private vulnerability reporting is available for this repository, please use it for sensitive reports.

If private reporting is not available, open a GitHub issue with a minimal description of the concern. Please avoid posting exploit details, real secrets, or private data in a public issue.

Useful reports include:

- The affected command or option.
- The operating system and Python version.
- A small reproduction case that does not include private files or credentials.
- The expected behavior and the actual behavior.

## Scope

Graft has no network server, authentication layer, database, or remote execution feature. Reports are most likely to involve local file handling, generated output, packaging metadata, or CI configuration.

## Response expectations

This project is maintained as a small project with limited capacity. Reports will be reviewed as maintainers are available, but no fixed response time is promised.

## Dependency posture

Graft has zero runtime dependencies. Security updates should preserve that posture unless a maintainer explicitly approves a change.
