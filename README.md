# File Integrity Monitor

An offline Python CLI that creates a SHA-256 baseline and reports added, removed, and modified files. Useful for learning integrity monitoring and automating checks on a local lab directory.

**Python 3.11+ · Standard library only · JSON output**

## Quick start

```bash
git clone https://github.com/bajily/file-integrity-monitor.git
cd file-integrity-monitor
mkdir demo
python -c "from pathlib import Path; Path('demo/example.txt').write_text('original')"
python integrity.py baseline demo baseline.json
python integrity.py check demo baseline.json
python -c "from pathlib import Path; Path('demo/example.txt').write_text('changed')"
python integrity.py check demo baseline.json
```

The last command reports `example.txt` as modified and exits with status `1`.

## Behavior

| Exit status | Meaning |
|---|---|
| `0` | Baseline created, or no file-content changes detected |
| `1` | Changes detected |
| `2` | Invalid input or filesystem error |

Files are read in chunks and identified by relative path. Symbolic links are skipped and reported; directory links are not traversed. Store the baseline **outside** the monitored directory. Baseline creation refuses to overwrite an existing file.

```json
{"added": [], "removed": [], "modified": ["example.txt"], "skipped_symlinks": [], "changed": true}
```

## Validate

```bash
python -m unittest discover -s tests -v
```

Tests cover change classification, nested binary files, missing paths, symlinks, invalid manifests, and baseline placement.

## Limitations

This is a content-integrity checker, not malware detection. It does not monitor permissions, ownership, empty directories, or live filesystem events. Use the same root for baseline and check; the manifest is not cryptographically signed, so keep it in a trusted location. A file changed during scanning may produce an inconsistent snapshot. Unreadable files cause an error rather than a clean report.

## بالعربية

أداة محلية لإنشاء بصمات SHA-256 للملفات ومقارنتها لاحقًا لاكتشاف الإضافة والحذف والتعديل. تعرض النتائج بصيغة JSON وتناسب المختبرات والمهام المجدولة.
