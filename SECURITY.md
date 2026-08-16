# Security policy

## Supported versions

Security fixes are applied to the latest release on the default branch.

## Reporting a vulnerability

Please do not open a public issue containing private learner data, database
contents, credentials, or an undisclosed vulnerability. Use GitHub's private
vulnerability reporting feature when it is available for this repository.

If private reporting is unavailable, open a minimal issue asking the maintainer
for a secure contact channel without including sensitive details.

## Data boundary

Open Review Assistant stores data locally but does not encrypt the SQLite file.
Users are responsible for device security, backups, filesystem permissions, and
avoiding publication of their database. Database files and SQLite journals are
excluded by the repository's `.gitignore`.
