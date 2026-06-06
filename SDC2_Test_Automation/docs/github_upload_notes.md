# GitHub Upload Notes

## Recommended Commit Strategy

Use one initial commit for the organized archive:

```bash
git init
git add README.md docs releases src .gitignore
git commit -m "Add SDC2 test automation release archive v0.1-v0.22"
```

For GitHub web upload, upload this extracted folder structure directly. If Git LFS is available, use it for `.zip`, `.png`, `.pdf`, and other generated binary artifacts.

## Recommended Branching

- `main`: stable documentation and approved release artifacts.
- `dev`: active development of firmware/GUI/scripts.
- `archive/preliminary`: optional branch if the team wants to isolate v0.1-v0.8 preliminary work.

## Release Artifact Policy

- Treat files in `releases/` as immutable.
- Put active source edits under `src/` or a new `firmware/`, `gui/`, `analysis/`, and `docs/` layout after the team chooses the baseline.
- Use semantic pre-release style names until the system is production-ready: `v0.23`, `v0.24`, etc.

## CUI / Protected-Research Hygiene

Before making the repository broadly visible, confirm that filenames, screenshots, comments, and documentation do not reveal restricted details, sponsor-sensitive identifiers, controlled test article details, or sensitive operating parameters. Keep public-facing text generic where needed.
