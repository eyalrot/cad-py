# CAD-PY Project Overview

## Project Description
CAD-PY is a professional 2D CAD system consisting of a Python microservice backend and Qt6 desktop client. It's designed for technical drawing, engineering diagrams, and architectural drafting.

## Architecture
- **Backend**: Python microservice with PostgreSQL, Redis, and Nginx
- **Frontend**: Qt6 desktop client (PyQt6) 
- **Communication**: Client-server architecture (gRPC/REST APIs)
- **Deployment**: Docker Compose with multi-container setup

## Key Directories
- `backend/` - Python microservice backend
- `qt_client/` - Qt6 desktop application (planned)
- `.taskmaster/` - Task management and project configuration
- `.serena/` - Serena AI assistant configuration
- `.cursor/` - Cursor IDE rules and configuration

## Development Status
- Early development phase with foundational geometry classes
- Backend core geometry system implemented (Point2D, Vector2D, Line, Circle, Arc, BoundingBox)
- Test infrastructure in place
- Docker environment configured
- Task management system active