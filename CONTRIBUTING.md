# Contributing to Devgraph Integrations

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful and inclusive in all interactions.

## Developer Certificate of Origin (DCO)

All commits must include a `Signed-off-by` line to certify that you have the right to submit the code under the project's license. See the [DCO](DCO) file for details.

### How to Sign Off Commits

Add `-s` flag when committing:

```bash
git commit -s -m "feat(github): add webhook support"
```

This adds a sign-off line automatically:
```
Signed-off-by: Your Name <your.email@example.com>
```

### Configure Git Identity

Ensure your git identity is set:

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

## GPG Commit Signing (Recommended)

We strongly encourage GPG signing for all commits.

### Setup GPG Signing

1. **Generate GPG key** (if you don't have one):
   ```bash
   gpg --full-generate-key
   # Select RSA and RSA, 4096 bits, key doesn't expire
   ```

2. **List your keys**:
   ```bash
   gpg --list-secret-keys --keyid-format=long
   ```

3. **Configure git to use GPG**:
   ```bash
   git config --global user.signingkey YOUR_KEY_ID
   git config --global commit.gpgsign true
   ```

4. **Add GPG key to GitHub**:
   - Export public key: `gpg --armor --export YOUR_KEY_ID`
   - Add to GitHub: Settings → SSH and GPG keys → New GPG key

5. **Commit with signing** (automatic if configured):
   ```bash
   git commit -s -m "feat(fossa): add support for custom endpoints"
   ```

## Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

Signed-off-by: Your Name <your.email@example.com>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Maintenance tasks

### Scopes

Use molecule names or component names:
- Molecules: `fossa`, `github`, `gitlab`, `docker`, `argo`, `file`, etc.
- Components: `core`, `config`, `cli`, `types`, `tests`

### Examples

```bash
# Feature with sign-off
git commit -s -m "feat(fossa): add relation creation for repositories

This adds support for creating relations between FOSSA projects
and their corresponding repositories in the graph.

Signed-off-by: Jane Doe <jane@example.com>"

# Bug fix
git commit -s -m "fix(github): handle rate limiting gracefully

Signed-off-by: Jane Doe <jane@example.com>"

# Breaking change
git commit -s -m "feat(gitlab)!: change relation type naming

BREAKING CHANGE: GitLabProjectRepository relation renamed to
GitLabProjectHostedByRepository for consistency.

Signed-off-by: Jane Doe <jane@example.com>"
```

## Development Workflow

1. **Fork and clone**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/devgraph-integrations.git
   cd devgraph-integrations
   ```

2. **Create a branch**:
   ```bash
   git checkout -b feat/my-feature
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   ```

4. **Make changes and test**:
   ```bash
   # Run tests
   poetry run pytest

   # Run tests with coverage
   poetry run pytest --cov=devgraph_integrations

   # Run linting
   poetry run ruff check .
   poetry run mypy devgraph_integrations
   ```

5. **Commit with sign-off** (and GPG signature if configured):
   ```bash
   git commit -s -m "feat(scope): description"
   ```

6. **Push and create PR**:
   ```bash
   git push origin feat/my-feature
   ```

## Pull Request Guidelines

- **Title**: Use conventional commit format
- **Description**: Explain what and why
- **Tests**: Add tests for new functionality
- **Documentation**: Update docs if needed
- **Sign-off**: All commits must be signed off
- **GPG Signing**: Strongly encouraged
- **Conventional Commits**: Required for automatic versioning

### PR Checklist

- [ ] Commits follow conventional commit format
- [ ] All commits are signed off (`-s` flag)
- [ ] Commits are GPG signed (recommended)
- [ ] Tests pass (`poetry run pytest`)
- [ ] Added/updated tests for changes
- [ ] Updated documentation if needed
- [ ] No breaking changes (or documented with `!` and `BREAKING CHANGE:`)

## Adding a New Molecule

See [CONTRIBUTING_MOLECULES.md](CONTRIBUTING_MOLECULES.md) for detailed instructions on adding new molecules.

Quick checklist:
1. Create molecule directory structure
2. Implement provider class
3. Add metadata with version and logo
4. Write comprehensive tests
5. Update documentation

## Testing

See [TESTING.md](TESTING.md) for testing framework documentation.

```bash
# Run all tests
poetry run pytest

# Run specific molecule tests
poetry run pytest tests/molecules/test_fossa.py

# Run with coverage
poetry run pytest --cov=devgraph_integrations --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Attribution

Contributors are automatically attributed through:

1. **Git commit metadata**: Your name and email from git config
2. **DCO sign-off**: Legal certification of your contribution rights
3. **GPG signature**: Cryptographic proof of commit authenticity
4. **GitHub profile**: Linked to commits in repository history

All contributions are acknowledged in the project's git history and GitHub contributors page.

## Questions?

- **Issues**: [GitHub Issues](https://github.com/arctir/devgraph-integrations/issues)
- **Discussions**: [GitHub Discussions](https://github.com/arctir/devgraph-integrations/discussions)
- **Documentation**: [docs.devgraph.ai](https://docs.devgraph.ai)

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
