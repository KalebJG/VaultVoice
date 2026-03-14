# Desktop Packaging and Distribution Pipeline

This repository ships desktop build artifacts using the GitHub Actions workflow at `.github/workflows/release-desktop.yml`.

## Versioning
- Source of truth: Git tag in the format `vMAJOR.MINOR.PATCH`.
- Release workflow behavior:
  - Tag build (`v1.2.3`) -> artifact version `1.2.3`.
  - Manual `workflow_dispatch` build -> pre-release version `0.0.0-dev+<short-sha>`.
- Artifact naming: `VaultVoice-<version>.tar.gz` and `VaultVoice-<version>.sha256`.

## Signed Build Artifact Strategy
1. **CI package stage** creates an **unsigned** versioned artifact and checksum for reproducibility.
2. **Promotion stage (required before public distribution)** signs and notarizes the app bundle using Apple Developer ID credentials.
3. Release metadata must be updated to reflect signing/notarization status before user delivery.

Signing policy:
- Signing identity: Apple Developer ID Application certificate.
- Notarization: `notarytool` ticket submission + staple to app bundle.
- Verification gates before publish:
  - `codesign --verify --deep --strict`
  - `spctl --assess --type execute`
  - notarization acceptance and stapling confirmation

## Install Path
- System-wide default target: `/Applications/VaultVoice.app`
- Per-user fallback target (non-admin): `~/Applications/VaultVoice.app`

For every release, include install path in release notes and in `RELEASE_METADATA.json` packaged with the artifact.
