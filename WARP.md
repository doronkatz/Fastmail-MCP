# Warp Agent Guidelines

## Linear Issue Workflow

When processing requests to review, plan, or implement Linear issues, always follow this workflow:

### 1. Mark Issue as In Progress
Use the Linear MCP integration to update the issue status to "In Progress" before beginning any work.

### 2. Create Feature Branch
Create a new feature branch following the naming convention:
```
feature/DOR-XXX-short-summary
```
Where:
- `DOR-XXX` is the Linear issue identifier (e.g., DOR-123)
- `short-summary` is a brief kebab-case description of the feature/fix

Example: `feature/DOR-456-add-search-filters`

### 3. Implement Changes
- Work on the feature/fix in the newly created branch
- Follow all existing coding standards and testing requirements
- Ensure all changes are properly tested and linted

### 4. Never Auto-Commit
**CRITICAL**: Never commit changes automatically. Always ask the human for review and approval before committing any changes. This includes:
- Individual commits during development
- Final commits before creating PRs
- Any git operations that modify the repository history

### 5. Pre-Commit Validation Pipeline
**MANDATORY**: Before requesting human approval for commits, execute the complete validation pipeline:

#### Build Verification
```bash
# Verify all imports work correctly
python3 -c "import sys; sys.path.insert(0, 'src'); import fastmail_mcp"
```

#### Test Suite Execution
```bash
# Run full test suite with coverage requirement
python3 -m pytest tests/ --cov=fastmail_mcp --cov-report=term-missing --cov-fail-under=80 -v
```

#### Code Quality Checks
```bash
# Linting and formatting validation
ruff check src tests
black --check src tests
```

#### Integration Validation
```bash
# Verify MCP server functionality
python3 -m fastmail_mcp.server --help
```

#### Coverage Requirements
- **Minimum 80% test coverage** on all new/modified code
- **100% coverage** on critical paths (authentication, data validation)
- **Unit tests required** for all new schemas, commands, and transport methods
- **Integration tests** for end-to-end workflows

### 6. Human Approval Required
Only after ALL validation steps pass:
1. Summarize the changes made and validation results
2. Show the human what will be committed with test coverage report
3. Confirm all quality gates passed (tests ✅, coverage ✅, linting ✅)
4. Wait for explicit approval to proceed
5. Only commit after receiving clear confirmation

**NEVER commit code that:**
- ❌ Has failing tests
- ❌ Falls below 80% coverage threshold
- ❌ Has linting or formatting errors
- ❌ Cannot import or run basic functionality

This workflow ensures proper Linear issue tracking, consistent branch naming, code quality, and maintains human oversight over all repository changes.
