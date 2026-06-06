#!/usr/bin/env python3
"""Regenerate SHA-256 manifest for release zip artifacts."""
from pathlib import Path
import csv, hashlib, re

root = Path(__file__).resolve().parents[1]
rows = []
for p in sorted((root / 'releases').rglob('*.zip')):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    m = re.search(r'_v(\d+\.\d+)_', p.name)
    rows.append({
        'track': p.parent.name,
        'version': m.group(1) if m else '',
        'filename': str(p.relative_to(root)).replace('\\', '/'),
        'size_bytes': p.stat().st_size,
        'sha256': h.hexdigest(),
    })

out = root / 'docs' / 'combined_release_manifest.csv'
with out.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['track', 'version', 'filename', 'size_bytes', 'sha256'])
    w.writeheader()
    w.writerows(rows)
print(f'Wrote {out}')
