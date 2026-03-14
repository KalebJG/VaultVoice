# VaultVoice Release Checklist

Use this checklist before promoting any desktop release artifact to end users.

## 1) Retention and privacy gates
- [ ] Confirm no transcript/audio persistence is enabled by default.
- [ ] Verify retention policy behavior with `apps/local-service/tests/test_retention.py`.
- [ ] Review logs/telemetry output to ensure no raw transcript leakage.
- [ ] Validate privacy claims in docs (`docs/privacy-model.md`) still match implementation.

## 2) Benchmark thresholds
- [ ] Run baseline benchmark suite (`apps/local-service/benchmarks/run_benchmark.py`).
- [ ] Compare results to `apps/local-service/benchmarks/baseline_results.json`.
- [ ] Block release if latency or quality metrics regress beyond approved tolerance.

## 3) Core flow smoke test
- [ ] Launch app and start dictation with push-to-talk.
- [ ] Confirm HUD state transitions Idle -> Listening -> Processing -> Idle.
- [ ] Confirm final transcript is produced in normal flow.

## 4) Shortcut fallback validation
- [ ] Validate default shortcut registration (`fn`).
- [ ] Validate fallback shortcut (`fn + Space`) when default is unavailable.
- [ ] Validate user-selected custom shortcut persists and re-registers.

## 5) Microphone permission UX validation
- [ ] Verify first-run mic permission prompt appears when expected.
- [ ] Verify denied-permission UX gives clear recovery steps to System Settings.
- [ ] Verify post-grant UX returns user to a successful dictation flow.

## 6) Distribution and signing gates
- [ ] Confirm release artifact version matches git tag (`vMAJOR.MINOR.PATCH`).
- [ ] Confirm SHA-256 checksum matches distributed artifact.
- [ ] Confirm app bundle signing and notarization are complete before public publish.
- [ ] Confirm install path in release notes (`/Applications/VaultVoice.app`, fallback `~/Applications/VaultVoice.app`).
