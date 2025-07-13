"""
Example demonstrating the command pattern and undo/redo system.

This example shows how to integrate the command manager with a Qt application
and perform various CAD operations with full undo/redo support.
"""

import asyncio
import logging
import sys
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from ..ui.panels.history_panel import HistoryPanel, HistoryToolbar
from .api_client import APIClientManager
from .command_manager import CommandManager
from .commands import create_draw_circle_command, create_draw_line_command


class CommandDemo(QMainWindow):
    """Demo application showing command pattern usage."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD Command Pattern Demo")
        self.setGeometry(100, 100, 1000, 700)

        # Initialize components
        self.api_client: Optional[APIClientManager] = None
        self.command_manager: Optional[CommandManager] = None
        self.current_document_id: Optional[str] = None

        # Setup UI
        self.setup_ui()

        # Initialize API client and command manager
        self.initialize_systems()

        # Setup demo timer
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self.run_demo_step)
        self.demo_step = 0

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left side - controls and info
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, 1)

        # Right side - history panel
        main_layout.addWidget(self.create_placeholder_history_panel(), 1)

    def create_placeholder_history_panel(self) -> QWidget:
        """Create a placeholder for the history panel."""
        placeholder = QWidget()
        placeholder.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        layout = QVBoxLayout(placeholder)

        from PySide6.QtWidgets import QLabel

        label = QLabel("History Panel\n(Will be initialized after command manager)")
        label.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(label)

        return placeholder

    def initialize_systems(self):
        """Initialize API client and command manager."""
        try:
            # Create API client
            self.api_client = APIClientManager("localhost:50051", self)

            # Create command manager
            self.command_manager = CommandManager(
                self.api_client, max_history=50, parent=self
            )

            # Connect command manager signals
            self.connect_command_signals()

            # Replace placeholder with real history panel
            self.setup_real_history_panel()

            # Create a test document
            QTimer.singleShot(
                2000, self.create_test_document
            )  # Wait 2 seconds for connection

        except Exception as e:
            logging.error(f"Failed to initialize systems: {e}")

    def setup_real_history_panel(self):
        """Replace placeholder with real history panel."""
        # Remove the placeholder
        central_widget = self.centralWidget()
        layout = central_widget.layout()
        placeholder = layout.itemAt(1).widget()
        layout.removeWidget(placeholder)
        placeholder.deleteLater()

        # Create real history panel
        self.history_panel = HistoryPanel(self.command_manager, self)

        # Connect history panel signals
        self.history_panel.undo_requested.connect(self.perform_undo)
        self.history_panel.redo_requested.connect(self.perform_redo)
        self.history_panel.clear_history_requested.connect(self.clear_history)

        # Add to layout
        layout.addWidget(self.history_panel, 1)

        # Create toolbar
        self.history_toolbar = HistoryToolbar(self.command_manager, self)
        self.history_toolbar.undo_requested.connect(self.perform_undo)
        self.history_toolbar.redo_requested.connect(self.perform_redo)

        # Add toolbar to main window
        self.addToolBar(self.history_toolbar)

    def connect_command_signals(self):
        """Connect command manager signals."""
        self.command_manager.command_executed.connect(self.on_command_executed)
        self.command_manager.command_undone.connect(self.on_command_undone)
        self.command_manager.command_redone.connect(self.on_command_redone)
        self.command_manager.history_changed.connect(self.on_history_changed)

    def create_test_document(self):
        """Create a test document for demo operations."""

        async def _create_doc():
            try:
                result = await self.api_client.client.create_document("Demo Document")
                if result and "id" in result:
                    self.current_document_id = result["id"]
                    logging.info(f"Created test document: {self.current_document_id}")

                    # Start demo after document creation
                    self.demo_timer.start(3000)  # Demo step every 3 seconds
                else:
                    logging.warning("Failed to create test document")
            except Exception as e:
                logging.error(f"Error creating test document: {e}")

        # Execute async function
        if self.api_client and self.api_client.thread.loop:
            asyncio.run_coroutine_threadsafe(_create_doc(), self.api_client.thread.loop)

    def run_demo_step(self):
        """Run a demo step."""
        if not self.current_document_id or not self.command_manager:
            return

        demo_steps = [
            self.demo_draw_line_1,
            self.demo_draw_line_2,
            self.demo_draw_circle_1,
            self.demo_draw_line_3,
            self.demo_draw_circle_2,
            self.demo_undo_last,
            self.demo_undo_last,
            self.demo_redo_last,
            self.demo_draw_line_4,
        ]

        if self.demo_step < len(demo_steps):
            try:
                demo_steps[self.demo_step]()
                self.demo_step += 1
            except Exception as e:
                logging.error(f"Demo step {self.demo_step} failed: {e}")
                self.demo_step += 1
        else:
            self.demo_timer.stop()
            logging.info("Demo completed!")

    def demo_draw_line_1(self):
        """Demo step: Draw first line."""
        command = create_draw_line_command(
            self.api_client,
            self.current_document_id,
            {"x": 0.0, "y": 0.0, "z": 0.0},
            {"x": 100.0, "y": 0.0, "z": 0.0},
        )
        self.execute_command_async(command)

    def demo_draw_line_2(self):
        """Demo step: Draw second line."""
        command = create_draw_line_command(
            self.api_client,
            self.current_document_id,
            {"x": 100.0, "y": 0.0, "z": 0.0},
            {"x": 100.0, "y": 100.0, "z": 0.0},
        )
        self.execute_command_async(command)

    def demo_draw_circle_1(self):
        """Demo step: Draw first circle."""
        command = create_draw_circle_command(
            self.api_client,
            self.current_document_id,
            {"x": 50.0, "y": 50.0, "z": 0.0},
            25.0,
        )
        self.execute_command_async(command)

    def demo_draw_line_3(self):
        """Demo step: Draw third line."""
        command = create_draw_line_command(
            self.api_client,
            self.current_document_id,
            {"x": 100.0, "y": 100.0, "z": 0.0},
            {"x": 0.0, "y": 100.0, "z": 0.0},
        )
        self.execute_command_async(command)

    def demo_draw_circle_2(self):
        """Demo step: Draw second circle."""
        command = create_draw_circle_command(
            self.api_client,
            self.current_document_id,
            {"x": 25.0, "y": 25.0, "z": 0.0},
            15.0,
        )
        self.execute_command_async(command)

    def demo_draw_line_4(self):
        """Demo step: Draw fourth line."""
        command = create_draw_line_command(
            self.api_client,
            self.current_document_id,
            {"x": 0.0, "y": 100.0, "z": 0.0},
            {"x": 0.0, "y": 0.0, "z": 0.0},
        )
        self.execute_command_async(command)

    def demo_undo_last(self):
        """Demo step: Undo last command."""
        self.perform_undo()

    def demo_redo_last(self):
        """Demo step: Redo last command."""
        self.perform_redo()

    def execute_command_async(self, command):
        """Execute a command asynchronously."""

        async def _execute():
            await self.command_manager.execute_command(command)

        if self.api_client and self.api_client.thread.loop:
            asyncio.run_coroutine_threadsafe(_execute(), self.api_client.thread.loop)

    def perform_undo(self):
        """Perform undo operation."""

        async def _undo():
            await self.command_manager.undo()

        if self.api_client and self.api_client.thread.loop:
            asyncio.run_coroutine_threadsafe(_undo(), self.api_client.thread.loop)

    def perform_redo(self):
        """Perform redo operation."""

        async def _redo():
            await self.command_manager.redo()

        if self.api_client and self.api_client.thread.loop:
            asyncio.run_coroutine_threadsafe(_redo(), self.api_client.thread.loop)

    def clear_history(self):
        """Clear command history."""
        if self.command_manager:
            self.command_manager.clear_history()

    # Signal handlers
    def on_command_executed(self, command_info):
        """Handle command executed."""
        logging.info(f"Command executed: {command_info['description']}")

    def on_command_undone(self, command_info):
        """Handle command undone."""
        logging.info(f"Command undone: {command_info['description']}")

    def on_command_redone(self, command_info):
        """Handle command redone."""
        logging.info(f"Command redone: {command_info['description']}")

    def on_history_changed(self):
        """Handle history changed."""
        if self.command_manager:
            stats = self.command_manager.get_statistics()
            logging.debug(f"History stats: {stats}")

    def closeEvent(self, event):
        """Handle application close."""
        if self.demo_timer.isActive():
            self.demo_timer.stop()

        if self.api_client:
            self.api_client.shutdown()

        event.accept()


def main():
    """Run the command demo application."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show demo window
    demo = CommandDemo()
    demo.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
