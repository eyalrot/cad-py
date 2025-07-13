"""Modern ribbon interface widget."""

import logging
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QTabWidget, QFrame, QLabel, QSizePolicy, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont


logger = logging.getLogger(__name__)


class RibbonButton(QPushButton):
    """Custom button for ribbon interface."""
    
    def __init__(self, text: str, icon_name: Optional[str] = None, 
                 large: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setText(text)
        self.setCheckable(False)
        
        # Set button style based on size
        if large:
            self.setMinimumSize(64, 64)
            self.setMaximumSize(80, 80)
            self.setIconSize(QSize(32, 32))
            # Arrange text below icon
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        else:
            self.setMinimumSize(32, 32)
            self.setMaximumSize(48, 48)
            self.setIconSize(QSize(16, 16))
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        # Set icon if provided
        if icon_name:
            # TODO: Load actual icons
            # self.setIcon(QIcon(f":/icons/{icon_name}.png"))
            pass
        
        # Style the button
        self.setStyleSheet("""
            QPushButton {
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 2px;
                background-color: transparent;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #e1f5fe;
                border-color: #0288d1;
            }
            QPushButton:pressed {
                background-color: #b3e5fc;
                border-color: #0277bd;
            }
            QPushButton:checked {
                background-color: #81d4fa;
                border-color: #0277bd;
            }
        """)


class RibbonGroup(QFrame):
    """Group of related buttons in the ribbon."""
    
    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.title = title
        self.buttons: List[RibbonButton] = []
        
        # Setup frame
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            RibbonGroup {
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin: 2px;
            }
        """)
        
        # Create layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(2)
        
        # Create button area
        self.button_widget = QWidget()
        self.button_layout = QHBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(2, 2, 2, 2)
        self.button_layout.setSpacing(2)
        
        # Create title label
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #666666;
                padding: 2px;
                border: none;
            }
        """)
        
        # Add to main layout
        self.main_layout.addWidget(self.button_widget)
        self.main_layout.addWidget(self.title_label)
    
    def add_button(self, button: RibbonButton):
        """Add a button to the group."""
        self.buttons.append(button)
        self.button_layout.addWidget(button)
    
    def add_large_button(self, text: str, icon_name: Optional[str] = None) -> RibbonButton:
        """Add a large button to the group."""
        button = RibbonButton(text, icon_name, large=True, parent=self)
        self.add_button(button)
        return button
    
    def add_small_button(self, text: str, icon_name: Optional[str] = None) -> RibbonButton:
        """Add a small button to the group."""
        button = RibbonButton(text, icon_name, large=False, parent=self)
        self.add_button(button)
        return button
    
    def add_separator(self):
        """Add a separator to the group."""
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Sunken)
        separator.setStyleSheet("QFrame { color: #cccccc; }")
        self.button_layout.addWidget(separator)


class RibbonTab(QWidget):
    """A tab in the ribbon containing groups of buttons."""
    
    def __init__(self, name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.name = name
        self.groups: List[RibbonGroup] = []
        
        # Create layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(8)
        
        # Add stretch at the end
        self.layout.addStretch()
    
    def add_group(self, group: RibbonGroup):
        """Add a group to the tab."""
        self.groups.append(group)
        # Insert before the stretch
        self.layout.insertWidget(len(self.groups) - 1, group)
    
    def create_group(self, title: str) -> RibbonGroup:
        """Create and add a new group."""
        group = RibbonGroup(title, self)
        self.add_group(group)
        return group


class RibbonWidget(QTabWidget):
    """Main ribbon widget containing multiple tabs."""
    
    # Signals
    action_triggered = pyqtSignal(str)  # action_name
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.action_buttons: Dict[str, RibbonButton] = {}
        
        # Setup tab widget
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #f5f5f5;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-bottom: none;
                padding: 6px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #f5f5f5;
                border-bottom: 1px solid #f5f5f5;
            }
            QTabBar::tab:hover {
                background-color: #e8e8e8;
            }
        """)
        
        # Create tabs
        self._create_home_tab()
        self._create_modify_tab()
        self._create_annotate_tab()
        self._create_view_tab()
        
        logger.info("Ribbon widget initialized")
    
    def _create_home_tab(self):
        """Create the Home tab with file and drawing tools."""
        home_tab = RibbonTab("Home")
        
        # File group
        file_group = home_tab.create_group("File")
        
        new_btn = file_group.add_large_button("New", "new")
        new_btn.setObjectName("new")
        new_btn.clicked.connect(lambda: self.action_triggered.emit("new"))
        
        open_btn = file_group.add_large_button("Open", "open")
        open_btn.setObjectName("open")
        open_btn.clicked.connect(lambda: self.action_triggered.emit("open"))
        
        save_btn = file_group.add_large_button("Save", "save")
        save_btn.setObjectName("save")
        save_btn.clicked.connect(lambda: self.action_triggered.emit("save"))
        
        # Clipboard group
        clipboard_group = home_tab.create_group("Clipboard")
        
        undo_btn = clipboard_group.add_small_button("Undo", "undo")
        undo_btn.setObjectName("undo")
        undo_btn.clicked.connect(lambda: self.action_triggered.emit("undo"))
        
        redo_btn = clipboard_group.add_small_button("Redo", "redo")
        redo_btn.setObjectName("redo")
        redo_btn.clicked.connect(lambda: self.action_triggered.emit("redo"))
        
        # Drawing group
        drawing_group = home_tab.create_group("Drawing")
        
        line_btn = drawing_group.add_large_button("Line", "line")
        line_btn.setObjectName("line")
        line_btn.setCheckable(True)
        line_btn.clicked.connect(lambda: self.action_triggered.emit("line"))
        
        circle_btn = drawing_group.add_large_button("Circle", "circle")
        circle_btn.setObjectName("circle")
        circle_btn.setCheckable(True)
        circle_btn.clicked.connect(lambda: self.action_triggered.emit("circle"))
        
        rect_btn = drawing_group.add_large_button("Rectangle", "rectangle")
        rect_btn.setObjectName("rectangle")
        rect_btn.setCheckable(True)
        rect_btn.clicked.connect(lambda: self.action_triggered.emit("rectangle"))
        
        # Store action buttons
        self.action_buttons.update({
            "new": new_btn,
            "open": open_btn,
            "save": save_btn,
            "undo": undo_btn,
            "redo": redo_btn,
            "line": line_btn,
            "circle": circle_btn,
            "rectangle": rect_btn
        })
        
        self.addTab(home_tab, "Home")
    
    def _create_modify_tab(self):
        """Create the Modify tab with editing tools."""
        modify_tab = RibbonTab("Modify")
        
        # Transform group
        transform_group = modify_tab.create_group("Transform")
        
        move_btn = transform_group.add_large_button("Move", "move")
        move_btn.setObjectName("move")
        move_btn.clicked.connect(lambda: self.action_triggered.emit("move"))
        
        rotate_btn = transform_group.add_large_button("Rotate", "rotate")
        rotate_btn.setObjectName("rotate")
        rotate_btn.clicked.connect(lambda: self.action_triggered.emit("rotate"))
        
        scale_btn = transform_group.add_large_button("Scale", "scale")
        scale_btn.setObjectName("scale")
        scale_btn.clicked.connect(lambda: self.action_triggered.emit("scale"))
        
        # Modify group
        modify_group = modify_tab.create_group("Modify")
        
        trim_btn = modify_group.add_large_button("Trim", "trim")
        trim_btn.setObjectName("trim")
        trim_btn.clicked.connect(lambda: self.action_triggered.emit("trim"))
        
        extend_btn = modify_group.add_large_button("Extend", "extend")
        extend_btn.setObjectName("extend")
        extend_btn.clicked.connect(lambda: self.action_triggered.emit("extend"))
        
        fillet_btn = modify_group.add_large_button("Fillet", "fillet")
        fillet_btn.setObjectName("fillet")
        fillet_btn.clicked.connect(lambda: self.action_triggered.emit("fillet"))
        
        self.addTab(modify_tab, "Modify")
    
    def _create_annotate_tab(self):
        """Create the Annotate tab with text and dimension tools."""
        annotate_tab = RibbonTab("Annotate")
        
        # Dimensions group
        dimensions_group = annotate_tab.create_group("Dimensions")
        
        linear_dim_btn = dimensions_group.add_large_button("Linear", "dim_linear")
        linear_dim_btn.setObjectName("dim_linear")
        linear_dim_btn.clicked.connect(lambda: self.action_triggered.emit("dim_linear"))
        
        angular_dim_btn = dimensions_group.add_large_button("Angular", "dim_angular")
        angular_dim_btn.setObjectName("dim_angular")
        angular_dim_btn.clicked.connect(lambda: self.action_triggered.emit("dim_angular"))
        
        radius_dim_btn = dimensions_group.add_large_button("Radius", "dim_radius")
        radius_dim_btn.setObjectName("dim_radius")
        radius_dim_btn.clicked.connect(lambda: self.action_triggered.emit("dim_radius"))
        
        # Text group
        text_group = annotate_tab.create_group("Text")
        
        text_btn = text_group.add_large_button("Text", "text")
        text_btn.setObjectName("text")
        text_btn.clicked.connect(lambda: self.action_triggered.emit("text"))
        
        leader_btn = text_group.add_large_button("Leader", "leader")
        leader_btn.setObjectName("leader")
        leader_btn.clicked.connect(lambda: self.action_triggered.emit("leader"))
        
        self.addTab(annotate_tab, "Annotate")
    
    def _create_view_tab(self):
        """Create the View tab with display controls."""
        view_tab = RibbonTab("View")
        
        # Zoom group
        zoom_group = view_tab.create_group("Zoom")
        
        zoom_in_btn = zoom_group.add_large_button("Zoom In", "zoom_in")
        zoom_in_btn.setObjectName("zoom_in")
        zoom_in_btn.clicked.connect(lambda: self.action_triggered.emit("zoom_in"))
        
        zoom_out_btn = zoom_group.add_large_button("Zoom Out", "zoom_out")
        zoom_out_btn.setObjectName("zoom_out")
        zoom_out_btn.clicked.connect(lambda: self.action_triggered.emit("zoom_out"))
        
        zoom_fit_btn = zoom_group.add_large_button("Zoom Fit", "zoom_fit")
        zoom_fit_btn.setObjectName("zoom_fit")
        zoom_fit_btn.clicked.connect(lambda: self.action_triggered.emit("zoom_fit"))
        
        # Display group
        display_group = view_tab.create_group("Display")
        
        grid_btn = display_group.add_small_button("Grid", "grid")
        grid_btn.setObjectName("grid")
        grid_btn.setCheckable(True)
        grid_btn.setChecked(True)
        grid_btn.clicked.connect(lambda: self.action_triggered.emit("toggle_grid"))
        
        snap_btn = display_group.add_small_button("Snap", "snap")
        snap_btn.setObjectName("snap")
        snap_btn.setCheckable(True)
        snap_btn.setChecked(True)
        snap_btn.clicked.connect(lambda: self.action_triggered.emit("toggle_snap"))
        
        # Store additional action buttons
        self.action_buttons.update({
            "zoom_in": zoom_in_btn,
            "zoom_out": zoom_out_btn,
            "zoom_fit": zoom_fit_btn,
            "toggle_grid": grid_btn,
            "toggle_snap": snap_btn
        })
        
        self.addTab(view_tab, "View")
    
    def get_action_button(self, action_name: str) -> Optional[RibbonButton]:
        """Get action button by name."""
        return self.action_buttons.get(action_name)
    
    def set_action_enabled(self, action_name: str, enabled: bool):
        """Enable/disable an action button."""
        button = self.get_action_button(action_name)
        if button:
            button.setEnabled(enabled)
    
    def set_action_checked(self, action_name: str, checked: bool):
        """Set checked state of an action button."""
        button = self.get_action_button(action_name)
        if button and button.isCheckable():
            button.setChecked(checked)