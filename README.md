# CAD-PY: Professional 2D CAD System

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Qt](https://img.shields.io/badge/Qt-6.6+-green.svg)](https://qt.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/cad-py/cad-py/actions)

> **A modern, extensible 2D CAD platform built with Python and Qt6, designed for technical drawing, engineering diagrams, and architectural drafting.**

CAD-PY is a professional-grade 2D Computer-Aided Design (CAD) system that combines the power of Python's ecosystem with Qt6's modern UI framework. It follows a microservice architecture with a Python backend and Qt6 desktop client, enabling high performance while maintaining extensibility for future enhancements.

## 🏗️ Project Architecture

### High-Level System Design

```text
┌─────────────────────────────────────────────────────────────────┐
│                         Qt6 Desktop Client                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                      Main Application Window                 │ │
│ │ ┌─────────┬─────────────────────────────────┬─────────────┐ │ │
│ │ │ Ribbon  │                                 │   Properties│ │ │
│ │ │ Menu    │      Drawing Canvas             │   Panel     │ │ │
│ │ │         │      (QGraphicsView)            │             │ │ │
│ │ ├─────────┤                                 ├─────────────┤ │ │
│ │ │ Tool    │                                 │   Layers    │ │ │
│ │ │ Palette │                                 │   Panel     │ │ │
│ │ │         │                                 │             │ │ │
│ │ ├─────────┴─────────────────────────────────┴─────────────┤ │ │
│ │ │              Command Line / Status Bar                   │ │ │
│ │ └───────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                               │                                   │
│                      Client Service Layer                         │
│ ┌─────────────────────────────┴─────────────────────────────┐   │
│ │  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐  │   │
│ │  │ API Client │  │ State Manager │  │ Cache Manager   │  │   │
│ │  │ (gRPC)     │  │              │  │                 │  │   │
│ │  └────────────┘  └──────────────┘  └─────────────────┘  │   │
│ └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                        Network (gRPC/REST)
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      CAD Backend Service                         │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                         API Layer                            │ │
│ │  ┌────────────────┐           ┌────────────────────────┐   │ │
│ │  │  gRPC Server   │           │  REST API (Optional)   │   │ │
│ │  │  Port: 50051   │           │  Port: 8080            │   │ │
│ │  └────────────────┘           └────────────────────────┘   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                      Business Logic Layer                    │ │
│ │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │ │
│ │  │  Drawing    │  │  Geometry   │  │   Constraint     │   │ │
│ │  │  Service    │  │  Engine     │  │   Solver         │   │ │
│ │  └─────────────┘  └─────────────┘  └──────────────────┘   │ │
│ │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │ │
│ │  │  Document   │  │  Selection  │  │   Export         │   │ │
│ │  │  Manager    │  │  Service    │  │   Service        │   │ │
│ │  └─────────────┘  └─────────────┘  └──────────────────┘   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                        Data Layer                            │ │
│ │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │ │
│ │  │  Document   │  │  Spatial    │  │   File           │   │ │
│ │  │  Store      │  │  Index      │  │   Storage        │   │ │
│ │  └─────────────┘  └─────────────┘  └──────────────────┘   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```text
cad-py/
├── backend/                     # Python microservice backend
│   ├── api/                    # gRPC API layer
│   │   ├── proto/             # Protocol buffer definitions
│   │   │   ├── cad_service.proto
│   │   │   ├── document.proto
│   │   │   ├── entity.proto
│   │   │   ├── geometry.proto
│   │   │   ├── layer.proto
│   │   │   └── generated/     # Generated gRPC stubs
│   │   ├── server.py          # gRPC server setup
│   │   ├── cad_grpc_service.py # Main service implementation
│   │   ├── converters.py      # Data converters
│   │   └── [service_files]    # Specialized service handlers
│   ├── core/                  # Core business logic
│   │   └── geometry/         # Geometry primitives and algorithms
│   │       ├── point.py
│   │       ├── vector.py
│   │       ├── line.py
│   │       ├── circle.py
│   │       ├── arc.py
│   │       └── bbox.py
│   ├── models/               # Data models
│   │   ├── document.py
│   │   ├── entity.py
│   │   ├── layer.py
│   │   ├── block.py
│   │   ├── dimension.py
│   │   └── serialization.py
│   ├── services/             # Business services
│   │   ├── dxf_service.py
│   │   ├── export_service.py
│   │   └── geometry_operations.py
│   ├── tests/               # Backend tests
│   ├── requirements.txt
│   └── Dockerfile
├── qt_client/                 # Qt6 desktop application
│   ├── main.py               # Application entry point
│   ├── core/                 # Core client logic
│   │   ├── application.py    # Main application controller
│   │   ├── api_client.py     # gRPC client wrapper
│   │   ├── command_manager.py # Command pattern for undo/redo
│   │   ├── selection_manager.py # Selection handling
│   │   └── snap_engine.py    # Object snapping
│   ├── ui/                   # User interface components
│   │   ├── main_window.py    # Main application window
│   │   ├── canvas/           # Drawing canvas components
│   │   │   ├── cad_canvas_view.py # Main drawing view
│   │   │   ├── cad_scene.py  # Graphics scene
│   │   │   ├── grid_overlay.py # Grid display
│   │   │   └── ruler_overlay.py # Ruler display
│   │   ├── panels/           # Side panels
│   │   │   ├── properties_panel.py
│   │   │   ├── layers_panel.py
│   │   │   ├── blocks_panel.py
│   │   │   └── history_panel.py
│   │   ├── ribbon/           # Ribbon interface
│   │   │   └── ribbon_widget.py
│   │   └── dialogs/          # Modal dialogs
│   │       ├── export_dialog.py
│   │       └── grid_ruler_config.py
│   ├── graphics/             # Graphics and tools
│   │   ├── items/           # Custom graphics items
│   │   │   └── preview_item.py
│   │   └── tools/           # Drawing and modification tools
│   │       ├── base_tool.py
│   │       ├── line_tool.py
│   │       ├── circle_tool.py
│   │       ├── arc_tool.py
│   │       ├── move_tool.py
│   │       ├── copy_tool.py
│   │       ├── rotate_tool.py
│   │       ├── scale_tool.py
│   │       ├── mirror_tool.py
│   │       ├── trim_tool.py
│   │       ├── extend_tool.py
│   │       ├── offset_tool.py
│   │       ├── fillet_tool.py
│   │       ├── chamfer_tool.py
│   │       ├── dimension_tool.py
│   │       ├── block_tool.py
│   │       └── tool_manager.py
│   ├── tests/               # Frontend tests
│   └── requirements.txt
├── .taskmaster/             # TaskMaster project management
│   ├── docs/
│   │   └── prd.txt         # Product Requirements Document
│   └── tasks/
│       └── tasks.json      # Detailed task breakdown
├── docker-compose.yml       # Multi-service container setup
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## 🎯 Target Applications

### Primary Use Cases

- **Mechanical Engineering**: Technical drawings, part designs, assembly layouts
- **Architecture**: Floor plans, elevations, construction details  
- **Electrical Engineering**: Schematic diagrams, panel layouts, wiring diagrams
- **Design & Drafting**: Precise 2D illustrations, patterns, templates

### Key Features

#### 🎨 Drawing Tools

- **Basic Geometry**: Lines, circles, arcs, rectangles, polygons, ellipses
- **Advanced Geometry**: Bezier curves, B-splines, offset curves, hatching patterns
- **Precision Tools**: Object snap system, grid snap, polar tracking, constraints

#### 📐 Annotation & Documentation

- **Dimensioning**: Linear, angular, radial, diameter dimensions with auto-update
- **Text & Labels**: Single/multi-line text, leaders, tables, title blocks
- **Smart Annotations**: Automatic dimension placement and formatting

#### 🔧 Modification Tools

- **Basic Operations**: Move, copy, rotate, scale, mirror
- **Advanced Operations**: Trim, extend, offset, fillet, chamfer
- **Selection Tools**: Single pick, window, crossing, selection filters

#### 📂 Organization & Management

- **Layer System**: Unlimited layers with properties, states, and templates
- **Block Library**: Reusable components, symbol libraries, dynamic blocks
- **Document Management**: Multi-document interface with version control

#### 💾 Data Exchange

- **Import/Export**: DXF (AutoCAD R12-2018), DWG read support
- **Vector Formats**: SVG, PDF export with layers
- **Raster Output**: PNG, JPEG export for presentations

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.12 or higher
- **Qt**: 6.6+ (installed via PySide6)
- **Operating System**: Windows 10+, macOS 11+, or Linux (Ubuntu 20.04+)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Display**: 1920×1080 minimum resolution

### Backend Setup

1. **Navigate to backend directory**:

   ```bash
   cd backend/
   ```

2. **Create and activate virtual environment**:

   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Generate gRPC stubs** (if needed):

   ```bash
   cd api/proto/
   python generate_grpc.py
   ```

5. **Start the backend server**:

   ```bash
   # From backend/ directory
   python -m api.server
   
   # Or with custom settings
   python -m api.server --port 50051 --workers 10
   ```

6. **Verify backend is running**:

   ```bash
   # Test gRPC server
   grpcurl -plaintext localhost:50051 list
   ```

### Frontend Setup

1. **Navigate to client directory**:

   ```bash
   cd qt_client/
   ```

2. **Create and activate virtual environment**:

   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the application**:

   ```bash
   python main.py
   ```

### Docker Setup (Recommended for Development)

1. **Start all services**:

   ```bash
   docker-compose up -d
   ```

2. **View logs**:

   ```bash
   docker-compose logs -f backend
   ```

3. **Stop services**:

   ```bash
   docker-compose down
   ```

The Docker setup includes:

- **Backend service** (port 8000)
- **PostgreSQL database** (port 5432)
- **Redis cache** (port 6379)
- **Nginx reverse proxy** (ports 80/443)

## 🔧 Development Workflow

### Running Tests

**Backend Tests**:

```bash
cd backend/
pytest tests/ -v --cov=backend --cov-report=html
```

**Frontend Tests**:

```bash
cd qt_client/
pytest tests/ -v --cov=qt_client
```

**All Tests**:

```bash
# From project root
pytest backend/tests/ qt_client/tests/ -v
```

### Code Quality

**Format Code**:

```bash
black backend/ qt_client/
isort backend/ qt_client/
```

**Lint Code**:

```bash
flake8 backend/ qt_client/
mypy backend/ qt_client/
```

**Pre-commit Hooks**:

```bash
pre-commit install
pre-commit run --all-files
```

### Building for Production

**Create Distribution**:

```bash
python -m build
```

**Build Docker Image**:

```bash
docker build -t cad-py:latest .
```

## 🛠️ Technology Stack

### Backend

- **Language**: Python 3.12+
- **Framework**: FastAPI + gRPC
- **Database**: PostgreSQL with SQLAlchemy
- **Cache**: Redis
- **Geometry**: NumPy, SciPy, Shapely
- **Serialization**: Protocol Buffers
- **Testing**: pytest, pytest-asyncio

### Frontend

- **UI Framework**: PySide6 (Qt6)
- **Graphics**: QGraphicsView framework with OpenGL
- **Communication**: gRPC client
- **Testing**: pytest-qt
- **Architecture**: Model-View-Controller (MVC)

### Development Tools

- **Code Quality**: Black, isort, flake8, mypy
- **Testing**: pytest with coverage reporting
- **Containers**: Docker & Docker Compose
- **CI/CD**: GitHub Actions (configured)
- **Documentation**: Sphinx + MkDocs

## 📋 Current Implementation Status

Based on the TaskMaster project tracking, the current implementation includes:

### ✅ Completed Features

- [x] **Project Structure & Environment** - Complete development setup
- [x] **Core Geometry Engine** - Point, Vector, Line, Circle, Arc primitives  
- [x] **Document Model** - Entity management, layer system, serialization
- [x] **gRPC API Service** - Basic CRUD operations and drawing commands
- [x] **Qt6 Application Shell** - Main window, menu system, status bar
- [x] **API Client Integration** - Async gRPC client with error handling
- [x] **Drawing Canvas** - QGraphicsView with pan, zoom, coordinate system
- [x] **Basic Drawing Tools** - Line, circle, arc tools with preview
- [x] **Object Snap System** - Endpoint, midpoint, center, intersection snaps
- [x] **Grid System** - Configurable grid display and snap-to-grid
- [x] **Selection System** - Single pick, window, crossing selection
- [x] **Modification Tools** - Move, copy, rotate, scale, mirror operations
- [x] **Advanced Tools** - Trim, extend, offset, fillet, chamfer
- [x] **Layer Management** - Layer panel with CRUD operations
- [x] **Command System** - Undo/redo with command pattern
- [x] **Linear Dimensions** - Horizontal, vertical, aligned dimensions
- [x] **Angular Dimensions** - Angular, radius, diameter dimensions  
- [x] **DXF Import/Export** - AutoCAD R12-2018 format support
- [x] **SVG/PDF Export** - Vector format export with layers
- [x] **Block System** - Reusable components and symbol libraries

### 🚧 Pending Features

- [ ] **Text Annotation Tools** - Single/multi-line text with formatting
- [ ] **Table Creation** - BOM generation and data extraction
- [ ] **Constraint System** - Geometric constraints with solver
- [ ] **Performance Optimization** - Spatial indexing, GPU acceleration
- [ ] **UI Polish** - Dark theme, customizable toolbars, help system

## 📖 Architecture Deep Dive

### Geometry Engine

The core geometry engine (`backend/core/geometry/`) provides mathematical primitives and algorithms:

```python
# Example: Creating and manipulating geometry
from backend.core.geometry import Point2D, Line, Circle

# Create points
p1 = Point2D(0, 0)
p2 = Point2D(10, 10)

# Create line
line = Line(p1, p2)
length = line.length()  # 14.142...

# Create circle  
center = Point2D(5, 5)
circle = Circle(center, radius=3.0)

# Find intersections
intersections = circle.intersection_with_line(line)
```

### gRPC API Layer

The API layer (`backend/api/`) exposes CAD operations via gRPC:

```protobuf
// cad_service.proto
service CADService {
    rpc CreateDocument(CreateDocumentRequest) returns (Document);
    rpc DrawLine(DrawLineRequest) returns (Entity);
    rpc QueryEntities(QueryRequest) returns (stream Entity);
    rpc ExportDocument(ExportRequest) returns (ExportResponse);
}
```

### Qt6 Graphics System

The frontend uses Qt6's QGraphicsView framework for high-performance 2D graphics:

```python
# Tool system example
class LineTool(BaseTool):
    def on_mouse_press(self, event):
        if not self.start_point:
            self.start_point = self.snap_point(event.scenePos())
        else:
            end_point = self.snap_point(event.scenePos())
            asyncio.create_task(
                self.api.draw_line(self.start_point, end_point)
            )
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to your fork: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Standards

- Follow PEP 8 for Python code style
- Use type hints throughout the codebase
- Write docstrings for all public functions and classes
- Maintain test coverage above 80%
- Run pre-commit hooks before committing

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Roadmap & Vision

CAD-PY aims to become a modern, extensible CAD platform that rivals established solutions like AutoCAD LT or DraftSight in 2D capabilities, while offering superior architecture for collaboration and customization.

### Short-term Goals (3-6 months)

- Complete text annotation and table systems
- Implement geometric constraints solver
- Add performance optimizations for large drawings
- Polish UI with dark theme and customization

### Medium-term Goals (6-12 months)

- Multi-user collaboration features
- Plugin architecture for extensibility
- Advanced rendering and visualization
- Mobile viewer application

### Long-term Vision (1-2 years)

- Cloud-based document storage and sync
- Real-time collaborative editing
- AI-assisted design tools
- Cross-platform consistency (Windows, macOS, Linux)

## 🆘 Support & Community

- **Documentation**: <https://cad-py.readthedocs.io/>
- **Issues**: [GitHub Issues](https://github.com/cad-py/cad-py/issues)
- **Discussions**: [GitHub Discussions](https://github.com/cad-py/cad-py/discussions)
- **Email**: <info@cad-py.org>

## 🙏 Acknowledgments

- Qt Company for the excellent Qt6 framework
- The Python community for the rich ecosystem of libraries
- AutoCAD and other CAD systems for inspiration and standards
- Contributors and early adopters of the CAD-PY project

---

## Built with ❤️ by the CAD-PY Development Team
