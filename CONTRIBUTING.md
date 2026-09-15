# Contributing to GEMINI-CLI-API

Thank you for your interest in contributing to GEMINI-CLI-API.

## Getting Started

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/your-username/gemini-cli-api.git
   cd gemini-cli-api
   ```

2. **Set up Environment**:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # Windows
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Run Test Suite**:
   Always ensure that all tests pass before submitting changes:
   ```bash
   python tests/runner.py
   ```

## Development Guidelines

- Follow PEP 8 style conventions.
- Write unit tests under `tests/` for any new endpoints, schemas, or features.
- Keep the terminal CLI responsive, zero-emoji, and clean.
- Do not commit `.env` or personal session directories.

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`.
2. Commit your changes: `git commit -m "feat: add feature description"`.
3. Push to your branch: `git push origin feature/my-feature`.
4. Open a Pull Request against the `main` branch.
