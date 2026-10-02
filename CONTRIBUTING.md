# Contributing

Thanks for helping improve Editorial Document HTML.

## Development

The project intentionally uses Python's standard library and plain HTML, CSS, and JavaScript. Python 3.9 or newer is recommended.

```bash
python3 scripts/check_skill.py
python3 scripts/build_previews.py
python3 scripts/build_gallery.py
```

Please preserve source wording and semantic structure. New visual behavior should work across desktop and narrow widths, light and dark themes, print, text-size controls, and keyboard navigation.

## Pull requests

- Keep changes focused and explain the source-fidelity impact.
- Add or update a deterministic fixture when behavior changes.
- Run `python3 scripts/check_skill.py` before opening a pull request.
- Do not add third-party logos, site chrome, proprietary assets, or branded imitation copy.

