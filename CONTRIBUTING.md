# Contributing to ISO-DART

Thank you for considering contributing to ISO-DART! This document provides guidelines and instructions for contributing to the project.

## 🌟 Ways to Contribute

### 1. Report Bugs 🐛

Found a bug? Please create an issue with:

- **Clear title**: Describe the issue in a few words
- **Environment**: OS, Python version, ISO-DART version
- **Steps to reproduce**: Detailed steps to recreate the bug
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Error messages**: Full error output with stack trace
- **Sample code**: Minimal code that reproduces the issue

**Template**:
```markdown
## Bug Description
Brief description of the bug

## Environment
- OS: Ubuntu 22.04
- Python: 3.10.8
- ISO-DART: v2.0.0

## Steps to Reproduce
1. Run `python isodart.py --iso caiso...`
2. Observe error...

## Expected Behavior
Should download data without errors

## Actual Behavior
Raises ConnectionError after 3 retries

## Error Output
```python
Traceback (most recent call last):
...
```

## Additional Context
Only happens with dates in October 2024
```

### 2. Suggest Features 💡

Have an idea? Create an issue with:

- **Feature description**: What you'd like to see
- **Use case**: Why this would be useful
- **Proposed solution**: How it might work (optional)
- **Alternatives considered**: Other approaches

### 3. Improve Documentation 📝

Documentation improvements are always welcome:

- Fix typos or unclear explanations
- Add examples or tutorials
- Improve API documentation
- Translate documentation (future)

### 4. Submit Code 🔧

#### Small Changes
For typos, small bug fixes, or minor improvements:
1. Fork the repository
2. Make your changes
3. Submit a pull request

#### Large Changes
For significant features or refactoring:
1. Create an issue first to discuss the approach
2. Wait for maintainer feedback
3. Fork and implement
4. Submit a pull request

## 📋 Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv, conda, etc.)

### Setup Steps

```bash
# 1. Fork and clone
git clone https://github.com/YOUR-USERNAME/ISO-DART.git
cd ISO-DART

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install in development mode
pip install -e .
pip install -r requirements.txt

# 4. Install development dependencies
pip install pytest pytest-cov black flake8 mypy types-requests

# 5. Verify installation
pytest tests/ -v
```

### Development Workflow

```bash
# 1. Create a feature branch
git checkout -b feature/your-feature-name

# 2. Make changes and commit
git add .
git commit -m "Add feature X"

# 3. Run tests
pytest tests/ -v

# 4. Format code
black lib/ tests/

# 5. Lint code
flake8 lib/ tests/

# 6. Type check
mypy lib/

# 7. Push and create PR
git push origin feature/your-feature-name
```

## 🎨 Code Style

### Python Style Guide

We follow PEP 8 with these modifications:

```python
# Maximum line length: 100 characters
# Use Black for formatting
# Use type hints everywhere

from typing import Optional, List
from datetime import date

def download_data(
    start_date: date,
    end_date: date,
    market: str = "DAM",
    nodes: Optional[List[str]] = None
) -> bool:
    """
    Download data from ISO.
    
    Args:
        start_date: Start date for data
        end_date: End date for data
        market: Market type (default: "DAM")
        nodes: Optional list of pricing nodes
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> download_data(date(2024, 1, 1), date(2024, 1, 31))
        True
    """
    # Implementation
    pass
```

### Documentation Style

```python
def complex_function(param1: str, param2: int) -> dict:
    """
    Brief one-line description.
    
    More detailed description if needed. Can span multiple lines
    and include usage examples.
    
    Args:
        param1: Description of param1. Be specific about format,
                constraints, and expected values.
        param2: Description of param2
        
    Returns:
        Dictionary with keys:
            - 'status': Success/failure status
            - 'data': Downloaded data as DataFrame
            - 'errors': List of errors if any
            
    Raises:
        ValueError: If param1 is empty
        ConnectionError: If API is unreachable
        
    Example:
        >>> result = complex_function("test", 42)
        >>> print(result['status'])
        'success'
        
    Note:
        This function requires API credentials to be configured.
        See configuration guide for details.
    """
    pass
```

### Naming Conventions

```python
# Classes: PascalCase
class DataDownloader:
    pass

class CAISOClient:
    pass

# Functions and variables: snake_case
def download_lmp_data():
    pass

user_name = "example"
max_retries = 3

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 5
DEFAULT_TIMEOUT = 30

# Private methods: _leading_underscore
def _internal_helper():
    pass

# Type hints
from typing import Optional, List, Dict, Any

def process_data(
    data: List[Dict[str, Any]],
    output_file: Optional[str] = None
) -> bool:
    pass
```

## 🧪 Testing Guidelines

### Writing Tests

Every new feature or bug fix should include tests:

```python
# tests/test_caiso.py
import pytest
from datetime import date
from lib.iso.caiso import CAISOClient, Market

class TestCAISOClient:
    """Tests for CAISO client functionality."""
    
    def test_lmp_download_success(self):
        """Test successful LMP download."""
        client = CAISOClient()
        
        result = client.get_lmp(
            market=Market.DAM,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1)
        )
        
        assert result is True
        # Additional assertions
        
    def test_lmp_download_invalid_dates(self):
        """Test LMP download with invalid dates."""
        client = CAISOClient()
        
        with pytest.raises(ValueError):
            client.get_lmp(
                market=Market.DAM,
                start_date=date(2024, 1, 31),
                end_date=date(2024, 1, 1)  # End before start
            )
            
    @pytest.mark.integration
    def test_lmp_download_integration(self):
        """Integration test - requires API access."""
        # Mark integration tests that hit real APIs
        pass
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_caiso.py -v

# Specific test
pytest tests/test_caiso.py::TestCAISOClient::test_lmp_download_success -v

# Skip integration tests (faster)
pytest tests/ -v -m "not integration"

# With coverage
pytest tests/ --cov=lib --cov-report=html

# Watch mode (run on file changes)
pytest-watch tests/
```

### Test Coverage

Aim for at least 80% coverage for new code:

```bash
# Generate coverage report
pytest tests/ --cov=lib --cov-report=html

# View report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

## 🔧 Adding a New ISO

To add support for a new ISO, follow this checklist:

### 1. Research Phase

- [ ] Identify data sources (API, FTP, web scraping)
- [ ] Review API documentation
- [ ] Test API access and understand authentication
- [ ] Document data formats and schemas
- [ ] Identify update frequencies and historical availability

### 2. Implementation

Create `lib/iso/new_iso.py`:

```python
"""
NewISO Client for ISO-DART v2.0

Client for New Independent System Operator data retrieval.
"""

from typing import Optional, List
from datetime import date, timedelta
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging
import requests

logger = logging.getLogger(__name__)


class NewISOMarket(Enum):
    """NewISO market types."""
    DAM = "DAM"
    RTM = "RTM"


@dataclass
class NewISOConfig:
    """Configuration for NewISO client."""
    base_url: str = "https://api.newiso.com"
    api_key: Optional[str] = None
    data_dir: Path = Path("data/NEWISO")
    max_retries: int = 3
    timeout: int = 30


class NewISOClient:
    """Client for retrieving data from NewISO."""
    
    def __init__(self, config: Optional[NewISOConfig] = None):
        self.config = config or NewISOConfig()
        self._ensure_directories()
        self.session = requests.Session()
        
    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        
    def get_lmp(
        self,
        market: NewISOMarket,
        start_date: date,
        end_date: date
    ) -> bool:
        """
        Get Locational Marginal Price data.
        
        Args:
            market: Market type
            start_date: Start date
            end_date: End date
            
        Returns:
            True if successful, False otherwise
        """
        # Implementation
        pass
        
    def cleanup(self):
        """Clean up temporary files."""
        pass
```

### 3. Add Tests

Create `tests/test_new_iso.py`:

```python
import pytest
from datetime import date
from lib.iso.new_iso import NewISOClient, NewISOMarket

class TestNewISOClient:
    """Tests for NewISO client."""
    
    def test_initialization(self):
        """Test client initialization."""
        client = NewISOClient()
        assert client.config is not None
        
    def test_lmp_download(self):
        """Test LMP download."""
        # Add test implementation
        pass
```

### 4. Add CLI Support

Update `lib/interactive.py`:

```python
def run_newiso_mode():
    """Interactive mode for NewISO data."""
    from lib.iso.new_iso import NewISOClient, NewISOMarket
    
    print("\n" + "=" * 60)
    print("NEWISO DATA SELECTION")
    print("=" * 60)
    
    # Implementation
    pass
```

Update `isodart.py`:

```python
def handle_newiso(args):
    """Handle NewISO-specific data download logic."""
    from lib.iso.new_iso import NewISOClient, NewISOMarket
    
    # Implementation
    pass

# Add to handlers dictionary
handlers = {
    "caiso": handle_caiso,
    "miso": handle_miso,
    "nyiso": handle_nyiso,
    "newiso": handle_newiso,  # Add here
}
```

### 5. Documentation

Create documentation files:
- `docs/isos/newiso/overview.md`
- `docs/isos/newiso/pricing.md`
- `docs/isos/newiso/api-guide.md`

Update main README.md with NewISO support.

### 6. Submit PR

When ready, submit a PR with:
- [ ] Implementation code
- [ ] Tests (with good coverage)
- [ ] Documentation
- [ ] Updated README.md
- [ ] Example usage in PR description

## 📝 Commit Message Guidelines

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Examples

```bash
# Simple commit
git commit -m "feat(caiso): add support for EIM transfer limits"

# Detailed commit
git commit -m "fix(miso): correct API endpoint for load forecast

The load forecast endpoint was using the wrong date format,
causing 400 errors. Updated to use YYYY-MM-DD format per
MISO API documentation.

Fixes #123"

# Breaking change
git commit -m "refactor(api)!: change Market enum values

BREAKING CHANGE: Market enum values changed from lowercase
to uppercase for consistency. Update all code using
Market.dam to Market.DAM"
```

## 🔍 Code Review Process

### What Reviewers Look For

1. **Functionality**: Does the code work as intended?
2. **Tests**: Are there adequate tests?
3. **Documentation**: Is the code well-documented?
4. **Style**: Does it follow our style guide?
5. **Performance**: Are there any performance concerns?
6. **Security**: Are there any security issues?
7. **Compatibility**: Does it break existing functionality?

### Responding to Reviews

- Be receptive to feedback
- Ask questions if unclear
- Make requested changes promptly
- Explain your reasoning if you disagree
- Mark conversations as resolved when done

### Example Review Response

```markdown
> Should we add input validation here?

Good catch! Added validation for date range and market type.
See commit abc123.

> This could be simplified using a list comprehension

Agreed, simplified in commit def456. Much cleaner now!
```

## 🚀 Release Process

### Version Numbering

We use Semantic Versioning (SemVer):

- **MAJOR**: Breaking changes (v1.0.0 → v2.0.0)
- **MINOR**: New features, backwards compatible (v2.0.0 → v2.1.0)
- **PATCH**: Bug fixes, backwards compatible (v2.0.0 → v2.0.1)

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in `pyproject.toml`
- [ ] Git tag created
- [ ] GitHub release created
- [ ] PyPI package published (if applicable)

## 💬 Communication

### Getting Help

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, show-and-tell
- **Email**: For private/security concerns

### Community Guidelines

- Be respectful and inclusive
- Welcome newcomers
- Give constructive feedback
- Assume good intentions
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)

## 🏆 Recognition

Contributors are recognized in:
- README.md contributor section
- Release notes
- Project documentation
- GitHub's contributor graph

## 📚 Additional Resources

### Learning Resources

- [Git Basics](https://git-scm.com/book/en/v2)
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Type Hints Guide](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)

### ISO Resources

- [CAISO API Documentation](http://www.caiso.com/Documents/OASIS-InterfaceSpecification.pdf)
- [MISO Data Exchange](https://data-exchange.misoenergy.org/)
- [NYISO Developer Resources](http://www.nyiso.com/public/markets_operations/market_data/index.jsp)

## ❓ FAQ

**Q: How long does code review take?**
A: Usually 1-3 days for small PRs, up to a week for large ones.

**Q: Can I work on multiple features at once?**
A: Yes, but create separate branches and PRs for each feature.

**Q: What if my PR isn't accepted?**
A: We'll explain why and suggest alternatives or improvements.

**Q: How do I become a maintainer?**
A: Consistent, quality contributions over time. We'll reach out!

**Q: Can I use ISO-DART code in my commercial project?**
A: Yes! MIT license allows commercial use. See LICENSE file.

## 🙏 Thank You!

Every contribution, no matter how small, helps make ISO-DART better. Thank you for being part of this project!

---

**Questions?** Open an issue or start a discussion on GitHub.

**Found a security issue?** Email the maintainers privately (see README.md).