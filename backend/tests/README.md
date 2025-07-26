# Backend Test Suite

This directory contains comprehensive unit tests for the backend application using pytest.

## Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and fixtures
├── unit/                       # Unit tests
│   ├── api/                    # API endpoint tests
│   │   └── test_auth.py       # Authentication API tests
│   ├── core/                   # Core functionality tests
│   │   └── test_security.py   # Security module tests
│   ├── crud/                   # Database CRUD operation tests
│   │   ├── test_user.py       # User CRUD tests
│   │   └── test_pending_action.py # Pending action CRUD tests
│   ├── integrations/           # Integration tests
│   │   └── gmail/             # Gmail integration tests
│   │       └── test_api.py    # Gmail API tests
│   ├── models/                 # Model validation tests
│   │   ├── test_user.py       # User model tests
│   │   ├── test_integration.py # Integration model tests
│   │   └── test_pending_action.py # Pending action model tests
│   ├── test_main.py           # Main application tests
│   └── test_database.py       # Database connection tests
└── integration/                # Integration tests (future)
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Basic Test Commands

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```

Run specific test types:
```bash
# Unit tests only
pytest -m unit

# API tests only
pytest -m api

# CRUD tests only
pytest -m crud

# Model tests only
pytest -m models

# Security tests only
pytest -m security
```

### Using the Test Runner Script

The `run_tests.py` script provides an easy way to run tests:

```bash
# Run all tests with coverage
python run_tests.py

# Run only unit tests
python run_tests.py --type unit

# Run without coverage
python run_tests.py --no-coverage

# Run in quiet mode
python run_tests.py --quiet
```

## Test Categories

### Unit Tests (`-m unit`)
- **API Tests**: Test API endpoints and their responses
- **CRUD Tests**: Test database operations (Create, Read, Update, Delete)
- **Model Tests**: Test Pydantic model validation
- **Security Tests**: Test JWT token creation and verification
- **Core Tests**: Test core application functionality

### Integration Tests (`-m integration`)
- **Gmail Integration**: Test Gmail API interactions
- **Calendar Integration**: Test Calendar API interactions
- **Authentication**: Test OAuth flows

## Test Fixtures

The `conftest.py` file provides several useful fixtures:

- `client`: FastAPI test client
- `db_session`: Database session for testing
- `test_user`: A test user instance
- `mock_google_credentials`: Mock Google credentials
- `valid_token`: Valid JWT token for testing
- `auth_headers`: Headers with authentication token
- `mock_firebase_auth`: Mock Firebase authentication

## Coverage

The test suite aims for comprehensive coverage of:

- **Models**: All Pydantic models and SQLAlchemy models
- **CRUD Operations**: All database operations
- **API Endpoints**: All FastAPI endpoints
- **Security**: JWT token handling and authentication
- **Core Functions**: Configuration and utility functions

## Adding New Tests

### For New Models

1. Create a test file in `tests/unit/models/`
2. Test both Pydantic validation and SQLAlchemy model creation
3. Include edge cases and error conditions

Example:
```python
def test_new_model_validation():
    """Test new model validation"""
    data = {"field": "value"}
    model = NewModel(**data)
    assert model.field == "value"
```

### For New API Endpoints

1. Create a test file in `tests/unit/api/`
2. Test successful responses and error cases
3. Mock external dependencies

Example:
```python
def test_new_endpoint_success(client, auth_headers):
    """Test successful endpoint call"""
    response = client.get("/api/new-endpoint", headers=auth_headers)
    assert response.status_code == 200
```

### For New CRUD Operations

1. Create a test file in `tests/unit/crud/`
2. Test all CRUD operations (Create, Read, Update, Delete)
3. Test edge cases and error conditions

Example:
```python
def test_create_new_item(db_session):
    """Test creating new item"""
    item = create_new_item(db_session, data)
    assert item.id is not None
```

## Best Practices

1. **Use Descriptive Test Names**: Test names should clearly describe what is being tested
2. **Test Both Success and Failure Cases**: Always test error conditions
3. **Mock External Dependencies**: Don't rely on external services in unit tests
4. **Use Fixtures**: Reuse common test data and setup
5. **Keep Tests Independent**: Each test should be able to run independently
6. **Test Edge Cases**: Include boundary conditions and error scenarios

## Continuous Integration

The test suite is designed to run in CI/CD pipelines. Key considerations:

- Tests use in-memory SQLite database
- External services are mocked
- No external dependencies required
- Fast execution for quick feedback

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all test dependencies are installed
2. **Database Issues**: Tests use in-memory database, no setup required
3. **Mock Issues**: Check that mocks are properly configured
4. **Coverage Issues**: Ensure all code paths are tested

### Debugging Tests

Run tests with verbose output:
```bash
pytest -v -s
```

Run a specific test:
```bash
pytest tests/unit/api/test_auth.py::TestAuthAPI::test_read_users_me_success -v
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain good test coverage
4. Update this README if needed 