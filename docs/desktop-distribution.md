# Desktop Packaging and Distribution Pipeline

This repository packages desktop **release artifacts** using the GitHub Actions workflow at `.github/workflows/release-desktop.yml`.

> Current scope: the workflow archives the `apps/desktop` module plus `RELEASE_METADATA.json` as `VaultVoice-<version>.tar.gz`. It does **not** currently produce a signed `.app` bundle installer.

## Versioning
- Source of truth: Git tag in the format `vMAJOR.MINOR.PATCH`.
- Release workflow behavior:
  - Tag build (`v1.2.3`) -> artifact version `1.2.3`.
  - Manual `workflow_dispatch` build -> pre-release version `0.0.0-dev+<short-sha>`.
- Artifact naming: `VaultVoice-<version>.tar.gz` and `VaultVoice-<version>.sha256`.

## What the workflow does today
1. Runs local-service and desktop unit test gates.
2. Creates `dist/desktop/VaultVoice-<version>/`.
3. Copies `apps/desktop` into the artifact root.
4. Writes `RELEASE_METADATA.json` including version, install path target, and signing strategy state.
5. Produces tarball + SHA-256 checksum.
6. Uploads artifacts to the workflow run and attaches them to a GitHub Release on tag builds.

## Signed Build Artifact Strategy
1. **CI package stage (implemented)** creates an **unsigned** versioned artifact and checksum for reproducibility.
2. **Promotion stage (future/required before public binary distribution)** builds the macOS `.app`, signs, and notarizes with Apple Developer ID credentials.
3. Release metadata and release notes must reflect final signing/notarization status before user delivery.

Signing policy for promotion stage:
- Signing identity: Apple Developer ID Application certificate.
- Notarization: `notarytool` ticket submission + staple to app bundle.
- Verification gates before publish:
  - `codesign --verify --deep --strict`
  - `spctl --assess --type execute`
  - notarization acceptance and stapling confirmation

## Install Path
Planned install targets for signed macOS app bundles:
- System-wide default target: `/Applications/VaultVoice.app`
- Per-user fallback target (non-admin): `~/Applications/VaultVoice.app`

For every release, include install path in release notes and in `RELEASE_METADATA.json` packaged with the artifact.
