# Development Workflow

## Code Standards
- **Python Version**: 3.12+
- **Code Formatting**: Black (line-length 88)
- **Import Sorting**: isort with Black profile
- **Type Checking**: mypy with strict settings
- **Testing**: pytest with coverage reporting

## Testing Strategy
- Unit tests in `backend/tests/`
- Test paths: `backend/tests`, `qt_client/tests`
- Coverage reporting: HTML and terminal
- Test files: `test_*.py`, `*_test.py`

## Git Workflow
- Main branch: `master`
- Pre-commit hooks enabled
- GitHub Actions CI/CD pipeline

## Development Environment
- Docker Compose for local development
- Services: backend (port 8000), postgres (5432), redis (6379), nginx (80/443)
- Backend auto-reloads with volume mounting

## Task Management
- TaskMaster AI integration for project planning
- Tasks stored in `.taskmaster/tasks/tasks.json`
- PRD-driven development approach

## IDE Configuration
- Cursor IDE with custom rules
- MCP (Model Context Protocol) integration
- Serena AI assistant integration