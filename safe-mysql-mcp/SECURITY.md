# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately through GitHub Security Advisories: go to the repository's
**Security** tab and click **Report a vulnerability**. We aim to respond within
7 days.

## Supported versions

Only the latest released version is supported.

## Security model

This project is meant to be handed to an LLM agent, so it is designed to fail
closed:

- read-only by default;
- dangerous SQL statements / shell commands are blocked **in code**;
- production targets are disabled by default and must be enabled explicitly;
- credentials are never stored in the repository.

The rules live in pure functions (see each package's `guard.py` / `policy.py`)
and are covered by unit tests.

## In scope

- Bypassing the guardrails: any SQL statement or remote command that passes
  validation but should not.
- Credential leakage (logs, errors, examples, commits).
- Path traversal or scope escapes (e.g. reading data outside the configured
  database / log root).

## Out of scope

- Issues caused by credentials the operator chose to expose.
- Consequences of deliberately enabling write access.

## Please do not

Do not include real credentials, hostnames, or internal addresses in issues,
pull requests, examples, or logs.
