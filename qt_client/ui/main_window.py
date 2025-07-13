"""Main application window implementation."""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QStatusBar, QLabel, QMenuBar, QToolBar,
    QMessageBox, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from qt_client.core.application import CADApplication
from qt_client.ui.ribbon.ribbon_widget import RibbonWidget
from qt_client.ui.canvas.cad_view import CADView
from qt_client.ui.panels.properties_panel import PropertiesPanel
from qt_client.ui.panels.layers_panel import LayersPanel


logger = logging.getLogger(__name__)


class CADMainWindow(QMainWindow):
    """Main CAD application window."""
    
    # Signals
    window_closing = pyqtSignal()
    
    def __init__(self, cad_app: CADApplication, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.cad_app = cad_app
        
        # Window properties
        self.setWindowTitle("PyCAD 2D Professional")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(800, 600)
        
        # Central widget and layout
        self._central_widget: Optional[QWidget] = None
        self._main_splitter: Optional[QSplitter] = None
        self._drawing_area: Optional[CADView] = None
        self._properties_panel: Optional[PropertiesPanel] = None
        self._layers_panel: Optional[LayersPanel] = None
        
        # UI components
        self._ribbon: Optional[RibbonWidget] = None
        self._coord_label: Optional[QLabel] = None
        self._zoom_label: Optional[QLabel] = None
        self._mode_label: Optional[QLabel] = None
        
        # State
        self._use_ribbon = True  # Use ribbon interface vs traditional menu/toolbar
        
        # Setup UI
        self._setup_ui()
        self._setup_connections()
        self._restore_window_state()
        
        logger.info("Main window initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Setup menu/toolbar or ribbon
        if self._use_ribbon:
            self._setup_ribbon()
        else:
            self._setup_traditional_menu()
        
        # Setup main layout
        self._setup_main_layout()
        
        # Setup status bar
        self._setup_status_bar()
        
        # Setup shortcuts
        self._setup_shortcuts()
    
    def _setup_ribbon(self):
        """Setup ribbon interface."""
        self._ribbon = RibbonWidget(self)
        self.setMenuWidget(self._ribbon)
        
        # Connect ribbon signals
        self._ribbon.action_triggered.connect(self._handle_action)
    
    def _setup_traditional_menu(self):
        """Setup traditional menu and toolbar."""
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # New action
        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.setStatusTip("Create a new document")
        new_action.triggered.connect(self._new_document)
        file_menu.addAction(new_action)
        
        # Open action
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.setStatusTip("Open an existing document")
        open_action.triggered.connect(self._open_document)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Save action
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setStatusTip("Save the current document")
        save_action.triggered.connect(self._save_document)
        file_menu.addAction(save_action)
        
        # Save As action
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.setStatusTip("Save the document with a new name")
        save_as_action.triggered.connect(self._save_document_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        # Undo action
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setStatusTip("Undo the last action")
        undo_action.setEnabled(False)  # TODO: Connect to undo system
        edit_menu.addAction(undo_action)
        
        # Redo action
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setStatusTip("Redo the last undone action")
        redo_action.setEnabled(False)  # TODO: Connect to undo system
        edit_menu.addAction(redo_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Zoom actions
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.setStatusTip("Zoom in")
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.setStatusTip("Zoom out")
        view_menu.addAction(zoom_out_action)
        
        zoom_fit_action = QAction("Zoom &Fit", self)
        zoom_fit_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_fit_action.setStatusTip("Zoom to fit all objects")
        view_menu.addAction(zoom_fit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        # Line tool
        line_action = QAction("&Line", self)
        line_action.setShortcut(QKeySequence("L"))
        line_action.setStatusTip("Draw a line")
        tools_menu.addAction(line_action)
        
        # Circle tool
        circle_action = QAction("&Circle", self)
        circle_action.setShortcut(QKeySequence("C"))
        circle_action.setStatusTip("Draw a circle")
        tools_menu.addAction(circle_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        # About action
        about_action = QAction("&About", self)
        about_action.setStatusTip("Show application information")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        # Create toolbar
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(toolbar)
        
        # Add actions to toolbar
        toolbar.addAction(new_action)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addSeparator()
        toolbar.addAction(undo_action)
        toolbar.addAction(redo_action)
        toolbar.addSeparator()
        toolbar.addAction(zoom_in_action)
        toolbar.addAction(zoom_out_action)
        toolbar.addAction(zoom_fit_action)
    
    def _setup_main_layout(self):
        """Setup the main window layout."""
        # Create central widget
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        # Create main splitter (horizontal)
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create drawing area
        self._drawing_area = CADView(self)
        
        # Create right panel splitter (vertical)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create panels
        self._properties_panel = PropertiesPanel(self)
        self._layers_panel = LayersPanel(self)
        
        # Add panels to right splitter
        right_splitter.addWidget(self._properties_panel)
        right_splitter.addWidget(self._layers_panel)
        right_splitter.setSizes([300, 300])  # Equal height for panels
        
        # Add to main splitter
        self._main_splitter.addWidget(self._drawing_area)
        self._main_splitter.addWidget(right_splitter)
        
        # Set splitter proportions (80% drawing area, 20% panels)
        self._main_splitter.setSizes([1120, 280])
        self._main_splitter.setCollapsible(0, False)  # Don't allow collapsing drawing area
        
        # Create main layout
        layout = QHBoxLayout(self._central_widget)
        layout.addWidget(self._main_splitter)
        layout.setContentsMargins(4, 4, 4, 4)
    
    def _setup_status_bar(self):
        """Setup status bar with coordinate display."""
        status_bar = self.statusBar()
        
        # Coordinate display
        self._coord_label = QLabel("X: 0.0000  Y: 0.0000")
        self._coord_label.setMinimumWidth(150)
        self._coord_label.setStyleSheet("QLabel { padding: 2px; }")
        
        # Zoom display
        self._zoom_label = QLabel("Zoom: 100%")
        self._zoom_label.setMinimumWidth(80)
        self._zoom_label.setStyleSheet("QLabel { padding: 2px; }")
        
        # Mode display
        self._mode_label = QLabel("Select")
        self._mode_label.setMinimumWidth(80)
        self._mode_label.setStyleSheet("QLabel { padding: 2px; }")
        
        # Add permanent widgets to status bar
        status_bar.addPermanentWidget(self._mode_label)
        status_bar.addPermanentWidget(self._zoom_label)
        status_bar.addPermanentWidget(self._coord_label)
        
        # Set initial message
        status_bar.showMessage("Ready", 2000)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # File shortcuts
        self._create_shortcut("Ctrl+N", self._new_document)
        self._create_shortcut("Ctrl+O", self._open_document)
        self._create_shortcut("Ctrl+S", self._save_document)
        self._create_shortcut("Ctrl+Shift+S", self._save_document_as)
        self._create_shortcut("Ctrl+Q", self.close)
        
        # Edit shortcuts
        self._create_shortcut("Ctrl+Z", self._undo)
        self._create_shortcut("Ctrl+Y", self._redo)
        self._create_shortcut("Ctrl+Shift+Z", self._redo)
        
        # View shortcuts
        self._create_shortcut("Ctrl+=", self._zoom_in)
        self._create_shortcut("Ctrl+-", self._zoom_out)
        self._create_shortcut("Ctrl+0", self._zoom_fit)
        
        # Tool shortcuts
        self._create_shortcut("Escape", self._select_tool)
        self._create_shortcut("L", self._line_tool)
        self._create_shortcut("C", self._circle_tool)
        self._create_shortcut("R", self._rectangle_tool)
    
    def _create_shortcut(self, key_sequence: str, slot):
        """Create and connect a keyboard shortcut."""
        action = QAction(self)
        action.setShortcut(QKeySequence(key_sequence))
        action.triggered.connect(slot)
        self.addAction(action)
    
    def _setup_connections(self):
        """Setup signal connections."""
        # Connect CAD application signals
        self.cad_app.document_opened.connect(self._on_document_opened)
        self.cad_app.document_closed.connect(self._on_document_closed)
        self.cad_app.current_document_changed.connect(self._on_current_document_changed)
        
        # Connect drawing area signals
        if self._drawing_area:
            self._drawing_area.mouse_moved.connect(self._update_coordinates)
            self._drawing_area.zoom_changed.connect(self._update_zoom)
    
    def _restore_window_state(self):
        """Restore window state from settings."""
        try:
            # Restore window geometry
            geometry = self.cad_app.get_setting("window_geometry")
            if geometry:
                self.restoreGeometry(geometry)
            
            # Restore window state
            state = self.cad_app.get_setting("window_state")
            if state:
                self.restoreState(state)
            
            # Restore splitter state
            splitter_state = self.cad_app.get_setting("splitter_state")
            if splitter_state and self._main_splitter:
                self._main_splitter.restoreState(splitter_state)
                
        except Exception as e:
            logger.warning(f"Failed to restore window state: {e}")
    
    def _save_window_state(self):
        """Save window state to settings."""
        try:
            self.cad_app.set_setting("window_geometry", self.saveGeometry())
            self.cad_app.set_setting("window_state", self.saveState())
            
            if self._main_splitter:
                self.cad_app.set_setting("splitter_state", self._main_splitter.saveState())
                
        except Exception as e:
            logger.warning(f"Failed to save window state: {e}")
    
    def center_on_screen(self):
        """Center the window on the screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            window_geometry = self.geometry()
            
            x = (screen_geometry.width() - window_geometry.width()) // 2
            y = (screen_geometry.height() - window_geometry.height()) // 2
            
            self.move(x, y)
    
    # Event handlers
    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Ask to save unsaved changes
            if self.cad_app.current_document_id:
                reply = QMessageBox.question(
                    self,
                    "Confirm Exit",
                    "Do you want to save changes before exiting?",
                    QMessageBox.StandardButton.Save | 
                    QMessageBox.StandardButton.Discard | 
                    QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Save
                )
                
                if reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
                elif reply == QMessageBox.StandardButton.Save:
                    if not self._save_document():
                        event.ignore()
                        return
            
            # Exit application
            if self.cad_app.exit_application():
                self._save_window_state()
                self.window_closing.emit()
                event.accept()
            else:
                event.ignore()
                
        except Exception as e:
            logger.error(f"Error during window close: {e}")
            event.accept()  # Force close
    
    # Action handlers
    def _handle_action(self, action_name: str):
        """Handle ribbon action."""
        logger.debug(f"Ribbon action triggered: {action_name}")
        
        # Map ribbon actions to methods
        action_map = {
            "new": self._new_document,
            "open": self._open_document,
            "save": self._save_document,
            "save_as": self._save_document_as,
            "undo": self._undo,
            "redo": self._redo,
            "line": self._line_tool,
            "circle": self._circle_tool,
            "rectangle": self._rectangle_tool,
            "zoom_in": self._zoom_in,
            "zoom_out": self._zoom_out,
            "zoom_fit": self._zoom_fit,
        }
        
        handler = action_map.get(action_name)
        if handler:
            handler()
        else:
            logger.warning(f"No handler for action: {action_name}")
    
    def _new_document(self):
        """Create a new document."""
        self.cad_app.new_document()
    
    def _open_document(self):
        """Open an existing document."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open CAD Document",
            "",
            "CAD Files (*.cad);;All Files (*)"
        )
        
        if file_path:
            self.cad_app.open_document(file_path)
    
    def _save_document(self) -> bool:
        """Save current document."""
        return self.cad_app.save_document()
    
    def _save_document_as(self) -> bool:
        """Save current document with new name."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CAD Document",
            "",
            "CAD Files (*.cad);;All Files (*)"
        )
        
        if file_path:
            return self.cad_app.save_document(file_path)
        return False
    
    def _undo(self):
        """Undo last action."""
        logger.debug("Undo action triggered")
        # TODO: Implement undo functionality
    
    def _redo(self):
        """Redo last undone action."""
        logger.debug("Redo action triggered")
        # TODO: Implement redo functionality
    
    def _select_tool(self):
        """Activate select tool."""
        logger.debug("Select tool activated")
        if self._mode_label:
            self._mode_label.setText("Select")
    
    def _line_tool(self):
        """Activate line tool."""
        logger.debug("Line tool activated")
        if self._mode_label:
            self._mode_label.setText("Line")
    
    def _circle_tool(self):
        """Activate circle tool."""
        logger.debug("Circle tool activated")
        if self._mode_label:
            self._mode_label.setText("Circle")
    
    def _rectangle_tool(self):
        """Activate rectangle tool."""
        logger.debug("Rectangle tool activated")
        if self._mode_label:
            self._mode_label.setText("Rectangle")
    
    def _zoom_in(self):
        """Zoom in."""
        if self._drawing_area:
            self._drawing_area.zoom_in()
    
    def _zoom_out(self):
        """Zoom out."""
        if self._drawing_area:
            self._drawing_area.zoom_out()
    
    def _zoom_fit(self):
        """Zoom to fit all objects."""
        if self._drawing_area:
            self._drawing_area.zoom_fit()
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About PyCAD",
            "<h3>PyCAD 2D Professional</h3>"
            "<p>Version 1.0.0</p>"
            "<p>A modern 2D CAD application built with PyQt6.</p>"
            "<p>Copyright © 2023 CAD-PY Development Team</p>"
        )
    
    # Signal handlers
    def _on_document_opened(self, document_id: str):
        """Handle document opened."""
        self.setWindowTitle(f"PyCAD 2D Professional - {document_id}")
        self.statusBar().showMessage(f"Opened document: {document_id}", 3000)
    
    def _on_document_closed(self, document_id: str):
        """Handle document closed."""
        self.setWindowTitle("PyCAD 2D Professional")
        self.statusBar().showMessage(f"Closed document: {document_id}", 3000)
    
    def _on_current_document_changed(self, document_id: str):
        """Handle current document changed."""
        if document_id:
            self.setWindowTitle(f"PyCAD 2D Professional - {document_id}")
        else:
            self.setWindowTitle("PyCAD 2D Professional")
    
    def _update_coordinates(self, world_pos: QPoint):
        """Update coordinate display."""
        if self._coord_label:
            self._coord_label.setText(f"X: {world_pos.x():.4f}  Y: {world_pos.y():.4f}")
    
    def _update_zoom(self, zoom_factor: float):
        """Update zoom display."""
        if self._zoom_label:
            self._zoom_label.setText(f"Zoom: {zoom_factor * 100:.0f}%")