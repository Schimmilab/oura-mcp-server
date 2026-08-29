# Privacy Policy

**oura-mcp-server** is a self-hosted, open-source MCP (Model Context Protocol) server
that lets its operator read **their own** Oura Ring data.

_Last updated: 2026-08-29_

## Who this applies to

This software is run by the person who installs it, on their own machine. There is no
hosted service, no shared backend and no operator-run infrastructure. "We" below means
the maintainer of this repository; "you" means the person running the software.

## What data is processed

When you authorize the application, it requests read access to your own Oura account
data (for example sleep, readiness, activity, heart rate, workouts, tags, SpO₂ and ring
configuration, depending on the scopes you grant).

## Where the data goes

- Data is fetched **directly from the Oura API to the machine you run this on**.
- It is used only to answer requests made by your own MCP client.
- **Nothing is transmitted to the maintainer or to any third party.**
- There is no analytics, no telemetry and no tracking of any kind.

## Storage

- OAuth tokens are stored **locally**, in a `.env` file on your machine.
- API responses may be held in an in-memory cache for the lifetime of the process, and
  optionally in a local cache if you enable one. Both live only on your machine.
- The maintainer has no access to your tokens or your data.

## Retention and deletion

Because all data stays on your machine, you delete it by deleting the local files
(`.env`, any cache or log files) and uninstalling the software.

## Revoking access

You can revoke this application's access at any time in your Oura account under
**Applications**. Revocation takes effect immediately and independently of this software.

## Contact

Questions or issues: https://github.com/Schimmilab/oura-mcp-server/issues
