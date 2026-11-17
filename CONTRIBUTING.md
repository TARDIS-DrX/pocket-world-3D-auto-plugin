# Contributing

## Development Setup

1. Install Python 3.10 or later.
2. Install dependencies:

```powershell
pip install -r work\plugin\requirements.txt
```

3. Install Zig 0.13+ if you need to rebuild the native library.

## Change Rules

- Keep IL2CPP targets resolved by class and method name, not fixed RVA.
- Do not commit game APKs, extracted game files, save data, or account data.
- Add a changelog entry for behavior changes.
- Check Python and PowerShell syntax before opening a pull request.

## Pull Requests

Describe these items:

1. The game version and version code.
2. The commands that you ran.
3. The log result, including `main thread dispatch active` or `worker thread fallback`.
4. Any remaining version-specific risk.
