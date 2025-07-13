"""
Example usage of the CAD API client.

This file demonstrates how to use the APIClientManager in a Qt application.
"""

import sys
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel
from PySide6.QtCore import Qt

from api_client import APIClientManager


class CADClientDemo(QMainWindow):
    """Demo application showing API client usage."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD API Client Demo")
        self.setGeometry(100, 100, 800, 600)
        
        # Setup UI
        self.setup_ui()
        
        # Create API client manager
        self.api_client = APIClientManager("localhost:50051", self)
        
        # Connect signals
        self.connect_signals()
        
        # Current document ID for demo
        self.current_document_id = None
    
    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Status label
        self.status_label = QLabel("Disconnected")
        layout.addWidget(self.status_label)
        
        # Buttons
        self.connect_btn = QPushButton("Connect to Server")
        self.connect_btn.clicked.connect(self.test_connection)
        layout.addWidget(self.connect_btn)
        
        self.create_doc_btn = QPushButton("Create Document")
        self.create_doc_btn.clicked.connect(self.create_document)
        layout.addWidget(self.create_doc_btn)
        
        self.list_docs_btn = QPushButton("List Documents")
        self.list_docs_btn.clicked.connect(self.list_documents)
        layout.addWidget(self.list_docs_btn)
        
        self.draw_line_btn = QPushButton("Draw Line")
        self.draw_line_btn.clicked.connect(self.draw_line)
        layout.addWidget(self.draw_line_btn)
        
        self.draw_circle_btn = QPushButton("Draw Circle")
        self.draw_circle_btn.clicked.connect(self.draw_circle)
        layout.addWidget(self.draw_circle_btn)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)
    
    def connect_signals(self):
        """Connect API client signals to UI handlers."""
        # Connection signals
        self.api_client.connection_state_changed.connect(self.on_connection_state_changed)
        self.api_client.connection_error.connect(self.on_connection_error)
        
        # Document signals
        self.api_client.document_created.connect(self.on_document_created)
        self.api_client.documents_listed.connect(self.on_documents_listed)
        
        # Drawing signals
        self.api_client.line_drawn.connect(self.on_line_drawn)
        self.api_client.circle_drawn.connect(self.on_circle_drawn)
    
    def log_message(self, message: str):
        """Add a message to the log output."""
        self.log_output.append(f"[{self.api_client.client.connection_state.value}] {message}")
    
    # Signal handlers
    def on_connection_state_changed(self, state: str):
        """Handle connection state changes."""
        self.status_label.setText(f"Status: {state.title()}")
        self.log_message(f"Connection state changed to: {state}")
    
    def on_connection_error(self, error: str):
        """Handle connection errors."""
        self.log_message(f"Connection error: {error}")
    
    def on_document_created(self, doc_data: dict):
        """Handle document creation."""
        self.current_document_id = doc_data['id']
        self.log_message(f"Document created: {doc_data['name']} (ID: {doc_data['id']})")
    
    def on_documents_listed(self, documents: list):
        """Handle documents listing."""
        self.log_message(f"Found {len(documents)} documents:")
        for doc in documents:
            self.log_message(f"  - {doc['name']} (ID: {doc['id']})")
    
    def on_line_drawn(self, entity_data: dict):
        """Handle line drawing."""
        self.log_message(f"Line drawn: {entity_data['id']}")
    
    def on_circle_drawn(self, entity_data: dict):
        """Handle circle drawing."""
        self.log_message(f"Circle drawn: {entity_data['id']}")
    
    # Button handlers
    def test_connection(self):
        """Test connection to server."""
        self.log_message("Testing connection...")
        self.api_client.list_documents()
    
    def create_document(self):
        """Create a new document."""
        self.log_message("Creating new document...")
        self.api_client.create_document("Demo Document")
    
    def list_documents(self):
        """List all documents."""
        self.log_message("Listing documents...")
        self.api_client.list_documents()
    
    def draw_line(self):
        """Draw a test line."""
        if not self.current_document_id:
            self.log_message("No document selected. Create a document first.")
            return
        
        self.log_message("Drawing line...")
        start = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        end = {'x': 100.0, 'y': 100.0, 'z': 0.0}
        self.api_client.draw_line(self.current_document_id, start, end)
    
    def draw_circle(self):
        """Draw a test circle."""
        if not self.current_document_id:
            self.log_message("No document selected. Create a document first.")
            return
        
        self.log_message("Drawing circle...")
        center = {'x': 50.0, 'y': 50.0, 'z': 0.0}
        radius = 25.0
        self.api_client.draw_circle(self.current_document_id, center, radius)
    
    def closeEvent(self, event):
        """Handle application close."""
        self.log_message("Shutting down API client...")
        self.api_client.shutdown()
        event.accept()


def main():
    """Run the demo application."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create and show demo window
    demo = CADClientDemo()
    demo.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()