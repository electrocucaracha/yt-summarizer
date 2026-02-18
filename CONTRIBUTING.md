# Contributing to YouTube Summarizer

Thank you for your interest in contributing to the YouTube Summarizer project. This document provides guidelines and instructions for developers.

## Development Setup

### Prerequisites

- Python 3.10 or higher

### Installation

1. Install dependencies using uv:

```bash { name=contributing.install }
uv sync
source .venv/bin/activate
```

2. Verify installation:

```bash { name=contributing.verify }
yt_summarizer --help
```

## Code Standards

### Style Guidelines

- **Python**: Follow PEP 8 standards with Black formatter
- **Code formatting**: Black with default settings (line length: 88 characters)
- **Linting**: Super-Linter validates all code contributions

### Running Code Quality Checks

Run linting validation:

```bash { name=contributing.lint }
make lint
```

### Formatting code

Run formatting fixer:

```bash { name=contributing.fmt }
make fmt
```

## Testing

All contributions must include tests that cover the new functionality.

### Running Tests

Execute all tests:

```bash { name=contributing.test }
uvx tox
```

### Test Requirements

- Test files must be placed in the `tests/` directory
- Use pytest fixtures for setup and teardown
- Mock external dependencies (Notion API, YouTube API, LLM services)
- Maintain minimum code coverage expectations

## Commits and Pull Requests

### Commit Messages

Use Conventional Commits specification for commit messages:

- **Format**: `<type>(<scope>): <description>`
- **Types**: feat, fix, docs, style, refactor, test, chore
- **Examples**:
  - `feat(notion): add support for custom database queries`
  - `fix(youtube): handle unavailable transcripts gracefully`
  - `docs: update installation instructions`

### Pull Request Process

1. Create a feature branch from `master`

2. Make your changes and test thoroughly

3. Ensure all tests pass and there is no linting issues

4. Push to your fork and submit a pull request

5. In the PR description:
   - Explain the changes clearly
   - Reference related issues
   - Describe any configuration changes needed

### Review Process

- All PRs require code review before merging
- Address feedback promptly
- Automated checks must pass before merging

## Documentation

- Update README.md if adding features or changing behavior
- Add docstrings to all functions and classes
- Include type hints for better code clarity

## Reporting Issues

When reporting bugs:

- Describe the problem clearly
- Include steps to reproduce
- Provide environment details (Python version, OS)
- Share error messages and logs

## License

By contributing to this project, you agree that your contributions will be licensed under the Apache License 2.0.
