# Code Formatting

This project uses [Black](https://github.com/psf/black) for code formatting.

## Format Code

Before committing, always format your code:

```bash
# Install black (if not already installed)
pip install black

# Format all Python files
black src/

# Or check formatting without changing files
black --check src/
```

## Pre-commit Hook (Optional)

To automatically format code before each commit, install pre-commit:

```bash
pip install pre-commit
pre-commit install
```

This will automatically format your code before each commit.

## CI/CD

GitHub Actions will check code formatting on every push. If formatting fails:

1. Run `black src/` locally
2. Commit the formatted files
3. Push again

## Black Configuration

Black uses default settings (line length: 88 characters). No configuration file needed.

