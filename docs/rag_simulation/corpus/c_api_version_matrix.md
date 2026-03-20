# C1 API Version Matrix

## Public API Lifecycle

- `v1` is legacy read-only and will reach EOL on `2026-06-30`.
- `v2` is stable default since `2025-01-15`.
- `v3` is beta since `2026-02-01` and has no formal SLA yet.

## Versioning Rules

- Clients calling `v3` must send `X-API-Version` header.
- Deprecation notice must be announced at least `90 days` before EOL.

## SDK Compatibility

- `sdk-java 2.x` supports `v2` and `v3` from `2025-09`.
- `sdk-python 1.8+` supports `v2`.
- `sdk-go 1.6+` supports `v2` only.
