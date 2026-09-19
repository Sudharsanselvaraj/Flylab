# Security policy

## Supported version

Security fixes are made on the latest `main` branch. This project is a research prototype and does not provide a hosted multi-user service or security SLA.

## Reporting a vulnerability

Please do not report security vulnerabilities in a public issue. Use GitHub's [private vulnerability reporting](https://github.com/Sudharsanselvaraj/The-Hawking-Fly/security/advisories/new) for this repository. If private reporting is unavailable, contact the maintainer through the repository's GitHub profile and provide only a minimal description until a private channel is arranged.

Include the affected path or feature, a clear reproduction, impact, and any suggested mitigation. We aim to acknowledge reports within seven days and will coordinate disclosure after a fix or mitigation is available.

## Scope notes

Treat any credential, token, private capture, or unexpected browser/network access as sensitive. Do not include secrets in reports. FlyLab's local browser automation is intended for its isolated benchmark workspace; changes that widen its access to user files, browser profiles, networks, or credentials need a security review before merge.
