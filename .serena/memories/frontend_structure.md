# Frontend Structure (Qt6 Client)

## Overview
The Qt6 client is planned but not yet implemented. Based on the PRD, it will be a professional CAD desktop application.

## Planned Structure (from PRD)
```
qt_client/
├── main.py                      # Application entry point
├── requirements.txt             # PyQt6, grpcio dependencies
├── ui/                          # User interface components
│   ├── main_window.py          # Main application window
│   ├── ribbon/                 # Ribbon interface
│   ├── canvas/                 # Drawing canvas (QGraphicsView)
│   ├── panels/                 # Properties, layers, blocks panels
│   └── dialogs/                # Settings, dimension styles
├── graphics/                   # Graphics items and tools
│   ├── items/                  # QGraphicsItem subclasses
│   ├── handles/                # Edit grips and handles
│   └── tools/                  # Drawing tools
├── core/                       # Core client logic
│   ├── api_client.py          # gRPC client wrapper
│   ├── document_model.py      # Local document model
│   └── command_manager.py     # Undo/redo system
└── utils/                     # Utilities and helpers
```

## Key Technologies
- PyQt6 for UI framework
- QGraphicsView for 2D drawing canvas
- gRPC client for backend communication
- OpenGL for hardware acceleration

## Current Status
- Not yet implemented
- Requirements file exists at `qt_client/requirements.txt`
- Planned for future development phases