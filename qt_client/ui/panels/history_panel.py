"""
History panel widget for displaying command history and undo/redo operations.

This panel provides a visual interface for viewing command history,
performing undo/redo operations, and managing command memory usage.
"""

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...core.command_manager import CommandManager


class HistoryPanel(QWidget):
    """
    Panel widget for displaying command history and undo/redo controls.

    This widget provides:
    - Visual command history list
    - Undo/Redo buttons with descriptions
    - Memory usage indicator
    - Command statistics
    """

    # Signals
    undo_requested = Signal()
    redo_requested = Signal()
    clear_history_requested = Signal()

    def __init__(self, command_manager: CommandManager, parent=None):
        """
        Initialize history panel.

        Args:
            command_manager: Command manager instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.command_manager = command_manager
        self.auto_refresh_enabled = True

        # Setup UI
        self.setup_ui()
        self.connect_signals()

        # Setup auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_display)
        self.refresh_timer.start(1000)  # Refresh every second

        # Initial display update
        self.refresh_display()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Title
        title_label = QLabel("Command History")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title_label)

        # Control buttons
        self.setup_control_buttons(layout)

        # Command history table
        self.setup_history_table(layout)

        # Statistics group
        self.setup_statistics_group(layout)

        # Memory usage group
        self.setup_memory_group(layout)

    def setup_control_buttons(self, layout: QVBoxLayout):
        """Setup undo/redo control buttons."""
        controls_layout = QHBoxLayout()

        # Undo button
        self.undo_button = QPushButton("Undo")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self.undo_requested.emit)
        self.undo_button.setToolTip("Undo the last command")
        controls_layout.addWidget(self.undo_button)

        # Redo button
        self.redo_button = QPushButton("Redo")
        self.redo_button.setEnabled(False)
        self.redo_button.clicked.connect(self.redo_requested.emit)
        self.redo_button.setToolTip("Redo the last undone command")
        controls_layout.addWidget(self.redo_button)

        # Clear history button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_history_requested.emit)
        self.clear_button.setToolTip("Clear all command history")
        controls_layout.addWidget(self.clear_button)

        layout.addLayout(controls_layout)

    def setup_history_table(self, layout: QVBoxLayout):
        """Setup command history table."""
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(
            ["Command", "Type", "State", "Time"]
        )

        # Configure table appearance
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.setSortingEnabled(False)

        # Configure column widths
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Command column
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # State
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Time

        # Set maximum height to prevent it from taking too much space
        self.history_table.setMaximumHeight(200)

        layout.addWidget(self.history_table)

    def setup_statistics_group(self, layout: QVBoxLayout):
        """Setup statistics display group."""
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)

        # Total commands label
        self.total_commands_label = QLabel("Total Commands: 0")
        stats_layout.addWidget(self.total_commands_label)

        # Undo stack size label
        self.undo_stack_label = QLabel("Undo Stack: 0")
        stats_layout.addWidget(self.undo_stack_label)

        # Redo stack size label
        self.redo_stack_label = QLabel("Redo Stack: 0")
        stats_layout.addWidget(self.redo_stack_label)

        layout.addWidget(stats_group)

    def setup_memory_group(self, layout: QVBoxLayout):
        """Setup memory usage display group."""
        memory_group = QGroupBox("Memory Usage")
        memory_layout = QVBoxLayout(memory_group)

        # Memory usage progress bar
        self.memory_progress = QProgressBar()
        self.memory_progress.setTextVisible(True)
        self.memory_progress.setFormat("%p% (%v MB / %m MB)")
        memory_layout.addWidget(self.memory_progress)

        # Memory details label
        self.memory_details_label = QLabel("0 MB / 50 MB")
        self.memory_details_label.setAlignment(Qt.AlignCenter)
        memory_layout.addWidget(self.memory_details_label)

        layout.addWidget(memory_group)

    def connect_signals(self):
        """Connect command manager signals."""
        self.command_manager.command_executed.connect(self.on_command_executed)
        self.command_manager.command_undone.connect(self.on_command_undone)
        self.command_manager.command_redone.connect(self.on_command_redone)
        self.command_manager.history_changed.connect(self.on_history_changed)

    def refresh_display(self):
        """Refresh the entire display."""
        if not self.auto_refresh_enabled:
            return

        self.update_buttons()
        self.update_history_table()
        self.update_statistics()
        self.update_memory_display()

    def update_buttons(self):
        """Update undo/redo button states and tooltips."""
        can_undo = self.command_manager.can_undo()
        can_redo = self.command_manager.can_redo()

        # Update button states
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)

        # Update tooltips with command descriptions
        if can_undo:
            undo_desc = self.command_manager.get_undo_description()
            self.undo_button.setToolTip(f"Undo: {undo_desc}")
        else:
            self.undo_button.setToolTip("Nothing to undo")

        if can_redo:
            redo_desc = self.command_manager.get_redo_description()
            self.redo_button.setToolTip(f"Redo: {redo_desc}")
        else:
            self.redo_button.setToolTip("Nothing to redo")

    def update_history_table(self):
        """Update the command history table."""
        history = self.command_manager.get_history()

        # Set row count
        self.history_table.setRowCount(len(history))

        # Populate table
        for row, command_info in enumerate(history):
            # Command description
            desc_item = QTableWidgetItem(command_info["description"])
            if command_info["stack"] == "redo":
                desc_item.setForeground(Qt.gray)
            self.history_table.setItem(row, 0, desc_item)

            # Command type
            type_item = QTableWidgetItem(command_info["type"].title())
            if command_info["stack"] == "redo":
                type_item.setForeground(Qt.gray)
            self.history_table.setItem(row, 1, type_item)

            # Command state
            state_item = QTableWidgetItem(command_info["state"].title())
            state_color = self.get_state_color(command_info["state"])
            state_item.setForeground(state_color)
            if command_info["stack"] == "redo":
                state_item.setForeground(Qt.gray)
            self.history_table.setItem(row, 2, state_item)

            # Execution time
            exec_time = command_info.get("execution_time")
            time_text = f"{exec_time:.3f}s" if exec_time else "N/A"
            time_item = QTableWidgetItem(time_text)
            if command_info["stack"] == "redo":
                time_item.setForeground(Qt.gray)
            self.history_table.setItem(row, 3, time_item)

        # Scroll to bottom to show most recent commands
        if history:
            self.history_table.scrollToBottom()

    def update_statistics(self):
        """Update statistics display."""
        stats = self.command_manager.get_statistics()

        self.total_commands_label.setText(f"Total Commands: {stats['total_commands']}")
        self.undo_stack_label.setText(f"Undo Stack: {stats['undo_stack_size']}")
        self.redo_stack_label.setText(f"Redo Stack: {stats['redo_stack_size']}")

    def update_memory_display(self):
        """Update memory usage display."""
        stats = self.command_manager.get_statistics()

        current_mb = stats["estimated_memory_mb"]
        max_mb = stats["max_memory_mb"]

        # Update progress bar
        self.memory_progress.setMaximum(int(max_mb))
        self.memory_progress.setValue(int(current_mb))

        # Update details label
        self.memory_details_label.setText(f"{current_mb:.1f} MB / {max_mb:.1f} MB")

        # Color code based on usage
        usage_percent = (current_mb / max_mb) * 100 if max_mb > 0 else 0

        if usage_percent > 90:
            style = "QProgressBar::chunk { background-color: #ff4444; }"
        elif usage_percent > 75:
            style = "QProgressBar::chunk { background-color: #ffaa00; }"
        else:
            style = "QProgressBar::chunk { background-color: #44ff44; }"

        self.memory_progress.setStyleSheet(style)

    def get_state_color(self, state: str):
        """Get color for command state display."""
        color_map = {
            "completed": Qt.darkGreen,
            "failed": Qt.red,
            "executing": Qt.blue,
            "undoing": Qt.magenta,
            "undone": Qt.gray,
            "pending": Qt.black,
        }
        return color_map.get(state, Qt.black)

    # Signal handlers
    def on_command_executed(self, command_info: Dict):
        """Handle command executed signal."""
        # The refresh timer will update the display
        pass

    def on_command_undone(self, command_info: Dict):
        """Handle command undone signal."""
        # The refresh timer will update the display
        pass

    def on_command_redone(self, command_info: Dict):
        """Handle command redone signal."""
        # The refresh timer will update the display
        pass

    def on_history_changed(self):
        """Handle history changed signal."""
        # Immediate update for history changes
        self.refresh_display()

    def set_auto_refresh(self, enabled: bool):
        """Enable or disable auto-refresh."""
        self.auto_refresh_enabled = enabled
        if enabled and not self.refresh_timer.isActive():
            self.refresh_timer.start(1000)
        elif not enabled:
            self.refresh_timer.stop()


class HistoryToolbar(QWidget):
    """
    Compact toolbar version of history controls for main window toolbar.
    """

    # Signals
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, command_manager: CommandManager, parent=None):
        """
        Initialize history toolbar.

        Args:
            command_manager: Command manager instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.command_manager = command_manager

        # Setup UI
        self.setup_ui()
        self.connect_signals()

        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_buttons)
        self.update_timer.start(500)  # Update every 0.5 seconds

        # Initial update
        self.update_buttons()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Undo button
        self.undo_button = QToolButton()
        self.undo_button.setText("Undo")
        self.undo_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.undo_button.clicked.connect(self.undo_requested.emit)
        layout.addWidget(self.undo_button)

        # Redo button
        self.redo_button = QToolButton()
        self.redo_button.setText("Redo")
        self.redo_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.redo_button.clicked.connect(self.redo_requested.emit)
        layout.addWidget(self.redo_button)

        # Add stretch to keep buttons compact
        layout.addStretch()

    def connect_signals(self):
        """Connect command manager signals."""
        self.command_manager.history_changed.connect(self.update_buttons)

    def update_buttons(self):
        """Update button states and tooltips."""
        can_undo = self.command_manager.can_undo()
        can_redo = self.command_manager.can_redo()

        # Update button states
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)

        # Update button text with command descriptions
        if can_undo:
            undo_desc = self.command_manager.get_undo_description()
            self.undo_button.setText(f"Undo {undo_desc}")
            self.undo_button.setToolTip(f"Undo: {undo_desc}")
        else:
            self.undo_button.setText("Undo")
            self.undo_button.setToolTip("Nothing to undo")

        if can_redo:
            redo_desc = self.command_manager.get_redo_description()
            self.redo_button.setText(f"Redo {redo_desc}")
            self.redo_button.setToolTip(f"Redo: {redo_desc}")
        else:
            self.redo_button.setText("Redo")
            self.redo_button.setToolTip("Nothing to redo")
