# Backend Structure

## Core Components
- `backend/core/` - Core business logic and geometry engine
- `backend/api/` - REST/gRPC API endpoints
- `backend/services/` - Business services layer
- `backend/models/` - Data models
- `backend/utils/` - Utility functions
- `backend/tests/` - Test suite

## Geometry System (backend/core/geometry/)
Implemented classes:
- `Point2D` - 2D point with x,y coordinates
- `Vector2D` - 2D vector operations
- `Line` - Line geometry class
- `Circle` - Circle geometry class
- `Arc` - Arc geometry class
- `BoundingBox` - Bounding box calculations

## Technology Stack
- Python 3.12 with type hints
- Docker containerization
- PostgreSQL database
- Redis caching
- Nginx proxy
- pytest for testing
- Black/isort for code formatting
- mypy for type checking

## Development Tools
- Code quality: Black (line-length 88), isort, mypy
- Testing: pytest with coverage reporting
- CI/CD: GitHub Actions (ci.yml, release.yml)
