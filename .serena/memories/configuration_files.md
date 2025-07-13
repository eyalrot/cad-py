# Configuration Files

## Python Configuration
- `pyproject.toml` - Python project configuration with Black, isort, mypy, pytest settings
- `setup.cfg` - Additional Python setup configuration  
- `.pre-commit-config.yaml` - Pre-commit hooks configuration

## Docker Configuration
- `docker-compose.yml` - Multi-container setup (backend, postgres, redis, nginx)
- `backend/Dockerfile` - Backend service container
- `nginx.conf` - Nginx proxy configuration

## Development Tools
- `.cursor/mcp.json` - Cursor IDE MCP configuration
- `.cursor/rules/` - Cursor IDE development rules and guidelines
- `.serena/project.yml` - Serena AI assistant project configuration

## Task Management
- `.taskmaster/config.json` - Task Master configuration
- `.taskmaster/state.json` - Task Master state
- `.taskmaster/tasks/tasks.json` - Project tasks
- `.taskmaster/docs/prd.txt` - Product Requirements Document

## Environment
- `.env.example` - Environment variables template
- `.gitignore` - Git ignore patterns

## Code Quality Settings
- Black: line-length 88, Python 3.12 target
- isort: Black-compatible profile
- mypy: Strict type checking enabled
- pytest: Coverage reporting with HTML output