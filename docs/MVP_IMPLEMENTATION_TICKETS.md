# VaultVoice MVP — Implementation-Ready Ticket Plan (Exact Build Order)

Product constraints baked into this plan:
- macOS first
- CPU-only target (no GPU assumptions)
- Short-form dictation
- Accuracy-first profile
- Push-to-talk default
- Default shortcut: `fn` (with fallback if unsupported)
- Tiny floating HUD required
- No transcript/audio persistence
- No export features

## Epic 0 — Project Foundation (must complete first)

**Implementation Status:**
- Completed: T0.1, T0.2
- Next up: T2.4 benchmark harness and baseline results

### T0.1 Initialize repository structure and standards ✅ Completed
**Goal:** Create a predictable skeleton for desktop app + local transcription service.
**Tasks:**
- Create folders: `apps/desktop`, `apps/local-service`, `docs`.
- Add root `README.md` with architecture and local run instructions.
- Add coding and logging standards in `docs/engineering-standards.md`.
**Acceptance Criteria:**
- Team can clone repo and understand module boundaries from README.
- Standards doc defines no-transcript logging rule.

### T0.2 Finalize PRD and acceptance metrics ✅ Completed
**Goal:** Lock scope to prevent drift.
**Tasks:**
- Create `docs/PRD.md` with confirmed decisions and non-goals.
- Add measurable MVP targets (WER/latency/reliability/no-retention).
**Acceptance Criteria:**
- PRD explicitly states no export, no persistence, macOS-first, push-to-talk + HUD.
- PM/engineering sign off on targets.

---

## Epic 1 — Security/Privacy Guardrails (before core features)

**Implementation Status:**
- Completed: T1.1, T1.2

### T1.1 Implement no-retention policy framework ✅ Completed
**Goal:** Ensure architecture cannot accidentally persist user speech data.
**Tasks:**
- Create `docs/privacy-model.md` with data lifecycle (audio + transcript in-memory only).
- Add runtime config surface with `retention_mode=memory_only` hard-default.
- Add guard utility in local-service to block disk writes for transcript/audio paths.
**Acceptance Criteria:**
- No transcript/audio written to files, temp dirs, db, or crash payloads in default mode.
- Policy documented and testable.

### T1.2 Privacy-safe observability ✅ Completed
**Goal:** Collect health metrics without collecting user content.
**Tasks:**
- Implement structured metrics for latency, chunk count, errors, CPU load.
- Add redaction/assertion layer preventing transcript text/audio bytes from logs.
**Acceptance Criteria:**
- Logs contain zero transcript content in normal and error paths.
- Dash/console metrics available for performance debugging.

---

## Epic 2 — Core Local Transcription Engine (CPU accuracy-first)

**Implementation Status:**
- Completed: T2.1, T2.2, T2.3
- In progress: T2.4 (benchmark harness + baseline results)

### T2.1 Transcription provider interface and service skeleton ✅ Completed
**Goal:** Decouple app from specific STT backend.
**Tasks:**
- Define `TranscriptionProvider` contract in `apps/local-service`.
- Implement local provider stub first; optional cloud provider deferred.
- Add local API/IPC endpoints for start, stream chunk, finalize.
**Acceptance Criteria:**
- Desktop app can call stable interface without provider-specific logic.
- Service responds to health check and transcription lifecycle commands.

### T2.2 Audio capture + preprocessing pipeline ✅ Completed
**Goal:** Improve accuracy and CPU efficiency.
**Progress Notes:**
- ✅ Implemented normalization, VAD-style speech detection, and overlap forwarding in local-service preprocessing path.
- ✅ Wired preprocessing into service stream flow so silence chunks are skipped before provider inference.
- ✅ Added live microphone frame chunking in the service flow, including finalize-time flush of remaining buffered audio.
**Tasks:**
- Implement mic capture pipeline.
- Add VAD-based chunking, normalization, and chunk overlap.
- Tune for short-form utterances.
**Acceptance Criteria:**
- Silence is mostly ignored.
- Captured chunks feed inference without clipped first words under normal usage.

### T2.3 Accuracy-first CPU profile with fallback ✅ Completed
**Progress Notes:**
- ✅ Added an accuracy-first profile controller that monitors CPU load windows and switches to a balanced fallback during sustained pressure.
- ✅ Exposed active profile and fallback state via service health responses.
- ✅ Added tests covering fallback activation and recovery after CPU pressure drops.
**Goal:** Deliver highest practical quality on CPU while remaining usable.
**Tasks:**
- Set default `Accuracy` profile decoding parameters.
- Implement overload detection and controlled fallback policy.
- Surface active profile and fallback state via API.
**Acceptance Criteria:**
- Default mode prioritizes quality.
- Service degrades gracefully on sustained CPU pressure.

### T2.4 Benchmark harness and baseline results
**Goal:** Validate quality/perf objectively before UI polish.
**Tasks:**
- Create benchmark script + dataset manifest in `apps/local-service/benchmarks`.
- Measure WER and latency for short-form cases (clean + moderate noise).
- Publish baseline in `docs/stt-baseline.md`.
**Acceptance Criteria:**
- Reproducible benchmark output exists.
- Team agrees baseline meets or is close to MVP targets.

---

## Epic 3 — Desktop App UX (push-to-talk + HUD)

### T3.1 macOS desktop shell and service integration
**Goal:** Connect UI shell to local-service end-to-end.
**Tasks:**
- Scaffold lightweight macOS desktop app.
- Wire start/stop/finalize dictation controls to service API.
- Display live partial and final transcript in-memory only.
**Acceptance Criteria:**
- User can run app, dictate, and see text appear.
- No persistence side effects.

### T3.2 Global shortcut system with fn-default + fallback
**Goal:** Provide reliable push-to-talk activation.
**Tasks:**
- Implement global hotkey manager.
- Set default to `fn`; validate capture reliability on supported macOS configs.
- If unsupported, auto-fallback to `fn + Space` and show guidance.
- Add user shortcut picker in Settings.
**Acceptance Criteria:**
- Push-to-talk works from background apps.
- Unsupported shortcut path is clearly handled with fallback + user messaging.

### T3.3 Push-to-talk lifecycle hardening
**Goal:** Ensure keydown/keyup feels precise and safe.
**Tasks:**
- Start capture on keydown, finalize on keyup.
- Add debounce + minimum utterance length logic.
- Add tiny pre-roll buffer to avoid clipped starts.
**Acceptance Criteria:**
- Rapid taps and long holds behave predictably.
- No “stuck recording” state after key transitions.

### T3.4 Tiny floating HUD
**Goal:** Instant user trust in recording state.
**Tasks:**
- Build always-on-top mini HUD states: Idle / Listening / Processing / Error.
- Show current shortcut and mic status.
- Add drag reposition and opacity option.
**Acceptance Criteria:**
- HUD state changes track dictation lifecycle in real time.
- HUD remains unobtrusive and stable across app focus changes.

---

## Epic 4 — Reliability, Hardening, and Release Prep

### T4.1 Failure handling and recovery
**Goal:** Prevent common runtime failures from breaking flow.
**Tasks:**
- Handle mic permission denial, device disconnect, service timeout, provider failure.
- Provide concise user-facing recovery actions.
**Acceptance Criteria:**
- Errors are actionable and app returns to usable state without restart in most cases.

### T4.2 End-to-end validation suite (content-safe)
**Goal:** Gate release quality without violating privacy constraints.
**Tasks:**
- Add integration tests for hotkey lifecycle, dictation flow, no-retention invariants.
- Add smoke checklist for macOS manual QA.
**Acceptance Criteria:**
- Critical flows are tested and repeatable.
- No-retention checks are part of release gate.

### T4.3 MVP packaging and release checklist
**Goal:** Ship a usable internal/alpha build.
**Tasks:**
- Create macOS build/distribution pipeline.
- Add release checklist (`docs/release-checklist.md`).
- Include user onboarding note for shortcut config and permissions.
**Acceptance Criteria:**
- Installable macOS build produced.
- Release checklist completed and signed off.

---

## Deferred (Post-MVP)
- Chrome extension integration
- Cloud STT fallback providers
- Domain vocabulary boosting
- Transcript export/history
- Enterprise/compliance workflows
