# Continuous Integration Setup

This project uses GitHub Actions with a self-hosted Mac mini runner for continuous integration.

## CI Workflow Features

### 🏗️ Build & Test Pipeline
- **Build Verification**: Validates imports and MCP server functionality
- **Code Quality**: Runs `ruff` linting and `black` formatting checks
- **Test Execution**: Full pytest suite with coverage reporting
- **Coverage Enforcement**: Maintains minimum 80% test coverage
- **Integration Validation**: Verifies MCP server can start properly

### 📊 Coverage & Reporting
- HTML coverage reports generated for detailed analysis
- JSON coverage data for programmatic access
- Markdown summaries in GitHub Actions job summaries
- Coverage artifacts uploaded for 7-day retention

### 🔒 Security & Secrets
- **FASTMAIL_CREDENTIALS_BASE64**: Base64-encoded .env file with Fastmail credentials
- Falls back to `.env.example` or creates minimal test config if secret not available
- Proper file permissions (600) for sensitive credential files

## Runner Configuration

The CI expects a self-hosted Mac mini runner with these labels:
```yaml
runs-on: [self-hosted, macos, mac-mini]
```

### Setting up the Runner
1. Configure your Mac mini as a GitHub Actions runner
2. Use labels: `--labels mac-mini,python,fastmail-mcp` when configuring
3. Ensure Python 3.14+ is installed and available as `python3`

## Environment Requirements

### Python Environment
- Python 3.14+ (currently using 3.14.2)
- Dependencies installed from `requirements.txt`
- pytest-cov for coverage reporting

### System Requirements
- macOS (tested on latest versions)
- Git (for repository operations)
- Base64 utility (for secret decoding)

## CI Trigger

The workflow triggers **only on pull requests**:
```yaml
on:
  pull_request:
```

This ensures:
- Main branch stays stable
- All changes are validated before merging
- No unnecessary runs on direct pushes to main

## Secrets Setup

### Required Secrets
Add these to your GitHub repository secrets:

#### `FASTMAIL_CREDENTIALS_BASE64`
Base64-encoded content of your `.env` file:

```bash
# Create base64-encoded secret
base64 -i .env | pbcopy
```

Then paste into GitHub repository settings > Secrets and variables > Actions

### Example .env Structure
```env
FASTMAIL_BASE_URL=https://api.fastmail.com
FASTMAIL_USERNAME=your-username
FASTMAIL_APP_PASSWORD=your-app-password
FASTMAIL_TOKEN=your-optional-token
```

## Validation Pipeline

The CI follows the validation pipeline defined in WARP.md:

### 1. Build Verification ✅
```bash
python3 -c "import sys; sys.path.insert(0, 'src'); import fastmail_mcp"
```

### 2. Test Suite Execution ✅
```bash
python3 -m pytest tests/ --cov=fastmail_mcp --cov-report=term-missing --cov-fail-under=80 -v
```

### 3. Code Quality Checks ✅
```bash
ruff check src tests
black --check src tests
```

### 4. Integration Validation ✅
```bash
PYTHONPATH=src python3 src/fastmail_mcp/server.py --help
```

## Coverage Requirements

- **Minimum**: 80% overall coverage
- **Current**: ~82% coverage maintained
- **Failing threshold**: CI fails if coverage drops below 80%
- **Reports**: Multiple formats (terminal, HTML, JSON, markdown)

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH=src` is set properly
2. **Coverage Below Threshold**: Add tests or mark untestable code with `# pragma: no cover`
3. **Formatting Failures**: Run `black src tests` to fix formatting
4. **Linting Errors**: Run `ruff check src tests` and fix reported issues

### Debug Information
The CI includes extensive debug output:
- Python version and location
- Git repository state
- Project structure
- Test execution logs

### Artifact Access
After each run, download:
- `test-report` artifact containing coverage data
- HTML coverage reports for detailed analysis
- Test execution logs for debugging

## Local Testing

Before pushing, run the same validation pipeline locally:

```bash
# Build verification
python3 -c "import sys; sys.path.insert(0, 'src'); import fastmail_mcp"

# Test with coverage
python3 -m pytest tests/ --cov=fastmail_mcp --cov-report=term-missing --cov-fail-under=80 -v

# Code quality
ruff check src tests
black --check src tests

# Integration test
PYTHONPATH=src python3 src/fastmail_mcp/server.py --help
```

## Maintenance

### Updating Dependencies
- Update `requirements.txt` or `requirements.in`
- Test locally before committing
- CI will validate new dependencies

### Adjusting Coverage Threshold
Modify the `COVERAGE_THRESHOLD` environment variable in `.github/workflows/ci.yml`:
```yaml
env:
  COVERAGE_THRESHOLD: 80  # Adjust as needed
```

### Runner Maintenance
- Keep macOS updated
- Maintain Python version compatibility
- Monitor disk space for artifacts
- Restart runner service if needed