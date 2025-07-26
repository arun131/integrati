# CI/CD Pipeline Documentation

This repository uses GitHub Actions for continuous integration and deployment.

## Workflows

### Backend Tests (`backend-tests.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Only runs when backend files are modified

**Jobs:**

1. **Test Job** (runs on Python 3.11 and 3.12)
   - Installs Python dependencies
   - Runs Ruff linting and formatting checks
   - Runs unit tests with coverage (minimum 70% required)
   - Uploads coverage reports to Codecov
   - Uploads test artifacts

2. **Security Job** (runs after tests pass)
   - Runs Bandit for security vulnerability scanning
   - Runs Safety for known package vulnerabilities
   - Uploads security reports as artifacts

### Frontend Tests (`frontend-tests.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Only runs when frontend files are modified

**Jobs:**

1. **Test Job**
   - Installs Node.js dependencies
   - Runs linting
   - Runs tests with coverage
   - Uploads coverage reports to Codecov
   - Uploads test artifacts

## Local Development

### Pre-commit Hooks

Install pre-commit hooks to run checks locally:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hook scripts
pre-commit install

# Run against all files
pre-commit run --all-files
```

### Running Tests Locally

**Backend:**
```bash
cd backend

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run linting
ruff check app/
ruff format --check app/

# Run tests
pytest tests/unit/ -v --cov=app --cov-report=html

# Run security checks
pip install bandit safety
bandit -r app/
safety check
```

**Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Run linting
npm run lint

# Run tests
npm test -- --coverage --watchAll=false
```

## Coverage Requirements

- **Backend**: Minimum 70% code coverage required
- **Frontend**: Coverage reports generated but no minimum requirement

## Security Scanning

- **Bandit**: Scans for common security issues in Python code
- **Safety**: Checks for known vulnerabilities in Python packages

## Artifacts

The following artifacts are uploaded and retained for 30 days:
- Test results and coverage reports
- Security scan reports
- Linting output

## Configuration Files

- `backend/pyproject.toml`: Ruff configuration for linting and formatting
- `.pre-commit-config.yaml`: Pre-commit hooks configuration
- `backend/requirements-test.txt`: Testing dependencies

## Troubleshooting

### Common Issues

1. **Tests failing locally but passing in CI**
   - Ensure you're using the same Python version
   - Check that all dependencies are installed
   - Run `pip install -r requirements-test.txt`

2. **Linting errors**
   - Run `ruff check app/` to see specific issues
   - Run `ruff check app/ --fix` to auto-fix issues
   - Check the `pyproject.toml` configuration

3. **Coverage below threshold**
   - Add more tests to increase coverage
   - Check which lines are not covered
   - Consider if uncovered code is necessary

### Adding New Tests

1. Create test files in the appropriate directory under `backend/tests/`
2. Follow the existing naming convention: `test_*.py`
3. Use descriptive test names
4. Include both positive and negative test cases
5. Mock external dependencies

### Adding New Dependencies

1. Update `backend/requirements.txt` for production dependencies
2. Update `backend/requirements-test.txt` for testing dependencies
3. Update the CI workflow if needed

## Best Practices

1. **Write tests first** (TDD approach)
2. **Keep tests independent** and fast
3. **Mock external dependencies** in unit tests
4. **Use descriptive test names**
5. **Include edge cases** and error conditions
6. **Maintain good test coverage**
7. **Run tests locally** before pushing

## Monitoring

- Check the "Actions" tab in GitHub for workflow status
- Review coverage reports in Codecov
- Monitor security scan results
- Address failing tests promptly 