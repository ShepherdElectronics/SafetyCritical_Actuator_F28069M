# SDC2 Test Automation and Characterization Toolkit

This repository bundle organizes the SDC2 test-automation packages for team upload and version-controlled review. It combines the preliminary release archive and the later development release archive into a single GitHub-ready structure.

## Repository Layout

```text
.
├── README.md
├── .gitignore
├── docs/
│   ├── combined_release_manifest.csv
│   ├── release_history.md
│   ├── github_upload_notes.md
│   ├── preliminary_manifest_original.csv
│   └── development_manifest_original.csv
├── releases/
│   ├── preliminary_v0.1-v0.8/
│   └── development_v0.1-v0.22/
└── src/
    ├── latest_v0.22/
    └── stable_raw_live_v0.18/
```

## What This Contains

- Early preliminary test packages, v0.1 through v0.8.
- Main development packages, v0.1 through v0.22.
- A latest extracted source snapshot from v0.22.
- A stable raw-live extracted source snapshot from v0.18 for comparison.
- Manifests with SHA-256 checksums for release traceability.

## Recommended Team Workflow

1. Upload this repository structure to the team GitHub site.
2. Keep the `releases/` folder as immutable release artifacts.
3. Use `src/latest_v0.22/` as the current working snapshot for code review.
4. Use `src/stable_raw_live_v0.18/` as the known-good reference if live plotting or real-time changes regress.
5. Add future releases as `v0.23`, `v0.24`, etc., and update `docs/combined_release_manifest.csv` and `docs/release_history.md`.

## Notes

The package is organized for engineering review, not as a polished production release. Some later versions include experimental dual-core and real-time architecture scaffolding; preserve stable versions for rollback.
