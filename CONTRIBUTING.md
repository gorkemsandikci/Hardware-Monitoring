# Contributing to Hardware Monitor System

Thank you for your interest in contributing to the Hardware Monitor System! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/hardware-monitoring.git`
3. Create a virtual environment: `python3 -m venv .venv`
4. Activate it: `source .venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Create a new branch: `git checkout -b feature/your-feature-name`

## Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write docstrings in Google style
- Maximum line length: 100 characters

### Code Formatting

We use `black` for code formatting:

```bash
black src/
```

### Linting

We use `pylint` for code quality:

```bash
pylint src/
```

### Testing

- Write tests for new features
- Ensure all tests pass before submitting
- Aim for >70% code coverage

```bash
pytest tests/
```

## Commit Messages

Use clear, descriptive commit messages:

- `feat: Add new feature`
- `fix: Fix bug in GPU detection`
- `docs: Update README`
- `refactor: Improve code structure`
- `test: Add tests for inventory module`

## Pull Request Process

1. Update README.md if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Submit pull request with clear description

## Reporting Issues

When reporting issues, please include:

- Operating system and version
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant error messages

## Feature Requests

Feature requests are welcome! Please:

- Check if the feature already exists
- Explain the use case
- Suggest implementation approach if possible

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback

Thank you for contributing!

