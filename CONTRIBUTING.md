# Contributing to RealAI

Thank you for your interest in contributing to RealAI! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/realai.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes: `python test_realai.py`
6. Commit your changes: `git commit -m "Description of changes"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Open a Pull Request

## Development Setup

```bash
cd realai
pip install -e .
```

## Running Tests

```bash
python test_realai.py
```

All tests should pass before submitting a PR.

## Code Style

- Follow PEP 8 guidelines for Python code
- Use type hints where appropriate
- Add docstrings to all public methods and classes
- Keep functions focused and single-purpose

## Adding New Capabilities

To add a new capability to RealAI:

1. Add the capability to the `ModelCapability` enum
2. Implement the method in the `RealAI` class
3. Add a corresponding method in `RealAIClient` if needed
4. Update the API server endpoints in `api_server.py`
5. Add tests in `test_realai.py`
6. Add examples in `examples.py`
7. Update documentation in README.md and API.md

## Testing

When adding new features:
- Add unit tests to `test_realai.py`
- Ensure all existing tests still pass
- Add examples demonstrating the new feature

## Documentation

When changing functionality:
- Update README.md if user-facing changes
- Update API.md for API changes
- Add/update docstrings in code
- Add examples if introducing new features

## Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Ensure all tests pass
- Update documentation as needed
- Keep changes focused and atomic

## Questions?

If you have questions, open an issue on GitHub.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
