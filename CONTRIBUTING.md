# Contributing

## Development Setup

1. Install Python 3.10 or later.
2. Install the .NET 6 runtime.
3. Run the unit tests.

```powershell
python -m unittest discover -s tests -v
```

## Change Rules

- Keep version-specific patch data in `patch_manifest.json`.
- Do not commit APKs, extracted game files, save data, or account data.
- Add a manifest entry when a game version needs new offsets.
- Add or update tests for branch encoding and manifest checks.
- Run `selftest` before you open a pull request.

## Pull Requests

Describe these items:

1. The game version and version code.
2. The commands that you ran.
3. The test result.
4. Any remaining version-specific risk.
