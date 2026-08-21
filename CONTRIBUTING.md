# Contributing to Sovereign OCI Proxy

Thank you for your interest in contributing! This project is built by and for the privacy community, and we welcome all forms of contribution.

## How to Report Bugs

If you encounter a bug, please [open an issue](https://github.com/Mohamed-DN/sovereign-oci-proxy/issues/new?template=bug_report.md) on GitHub. Include:
- A clear description of the problem
- Steps to reproduce the issue
- Your environment (OS, 3x-ui version, client application)
- Relevant log output (sanitize any secrets before posting!)

## How to Suggest Features

Feature requests are welcome! [Open an issue](https://github.com/Mohamed-DN/sovereign-oci-proxy/issues/new?template=feature_request.md) and describe:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## How to Submit Pull Requests

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes: `git checkout -b feature/my-improvement`
4. **Make your changes** following the code style guidelines below
5. **Test** your changes by running `sudo ./tests/sovereign-test.sh` on a live server
6. **Commit** with a clear message: `git commit -m "feat: add XYZ"`
7. **Push** to your fork: `git push origin feature/my-improvement`
8. **Open a Pull Request** against the `main` branch

## Code Style Guidelines

### Shell Scripts (`.sh`)
- Always start with `#!/bin/bash`
- Use `set -e` to exit on errors
- All comments and output messages must be in **English**
- Use uppercase for environment variables: `BACKUP_DIR`, `LOG_FILE`
- Never hardcode secrets — use placeholders like `YOUR-TOKEN-HERE`
- Quote all variables: `"$VAR"` not `$VAR`

### Python Scripts (`.py`)
- Use Python 3.8+ syntax
- Include a module-level docstring explaining purpose
- Use `snake_case` for functions and variables
- Handle exceptions gracefully with try/except

### Configuration Files
- Include inline comments explaining non-obvious settings
- Use templates with placeholder values for secrets

## Security

**Never commit credentials, tokens, passwords, UUIDs, or private keys to this repository.** If you accidentally commit a secret, notify the maintainers immediately. See [SECURITY.md](SECURITY.md) for our full security policy.

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code restructuring without behavior change
- `test:` — Adding or updating tests
- `chore:` — Maintenance tasks

## Questions?

Feel free to open a [Discussion](https://github.com/Mohamed-DN/sovereign-oci-proxy/discussions) or reach out via Issues.
