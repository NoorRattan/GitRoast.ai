# Security Policy

## Reporting a vulnerability

Do not disclose vulnerabilities, credentials, private URLs, access tokens, or
reproduction data in a public issue or discussion.

Use GitHub's private vulnerability reporting for this repository when it is
enabled, or contact the repository owner privately. Include the affected URL
or component, impact, reproducible steps, and any safe proof of concept.

## Scope notes

- The public API gateway is the only supported entry point for protected API
  routes. Direct protected requests to the Render origin should be rejected.
- Do not submit gateway secrets, GitHub tokens, database URLs, Upstash tokens,
  or admin credentials in a report.
- Reports receive acknowledgement and remediation timing based on severity and
  reproducibility.
