"""Blocks panel for managing block definitions and references."""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLineEdit,
    QComboBox,
    QLabel,
    QGroupBox,
    QSplitter,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
    QMenu,
    QMenuBar,
    QToolBar,
    QSizePolicy
)

logger = logging.getLogger(__name__)


class BlocksPanel(QWidget):
    """Panel for managing blocks and block libraries."""

    # Signals
    block_selected = Signal(str)  # block_id
    block_inserted = Signal(str, dict)  # block_id, insertion_data
    block_created = Signal(dict)  # block_data
    block_deleted = Signal(str)  # block_id

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.current_library_id: Optional[str] = None
        self.current_category: str = "All"
        self.blocks_data: Dict[str, Any] = {}
        self.libraries_data: Dict[str, Any] = {}

        self.setWindowTitle("Blocks")
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self._setup_ui()
        self._setup_connections()
        self._load_data()

        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._load_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds

        logger.debug("Blocks panel initialized")

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header with search and controls
        header_group = QGroupBox("Block Library")
        header_layout = QVBoxLayout(header_group)

        # Library selection
        library_layout = QHBoxLayout()
        library_layout.addWidget(QLabel("Library:"))
        
        self.library_combo = QComboBox()
        self.library_combo.currentTextChanged.connect(self._on_library_changed)
        library_layout.addWidget(self.library_combo)

        self.new_library_btn = QPushButton("New")
        self.new_library_btn.setMaximumWidth(50)
        self.new_library_btn.clicked.connect(self._create_new_library)
        library_layout.addWidget(self.new_library_btn)

        header_layout.addLayout(library_layout)

        # Category selection
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(["All", "General", "Symbols", "Mechanical", "Electrical", "Architectural"])
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        category_layout.addWidget(self.category_combo)

        header_layout.addLayout(category_layout)

        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search blocks...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit)

        self.search_clear_btn = QPushButton("Clear")
        self.search_clear_btn.setMaximumWidth(50)
        self.search_clear_btn.clicked.connect(self._clear_search)
        search_layout.addWidget(self.search_clear_btn)

        header_layout.addLayout(search_layout)

        layout.addWidget(header_group)

        # Main content area
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Blocks list
        blocks_group = QGroupBox("Available Blocks")
        blocks_layout = QVBoxLayout(blocks_group)

        # Toolbar for block operations
        blocks_toolbar = QHBoxLayout()
        
        self.create_block_btn = QPushButton("Create")
        self.create_block_btn.setToolTip("Create new block from selection")
        self.create_block_btn.clicked.connect(self._create_block)
        blocks_toolbar.addWidget(self.create_block_btn)

        self.insert_block_btn = QPushButton("Insert")
        self.insert_block_btn.setToolTip("Insert selected block")
        self.insert_block_btn.clicked.connect(self._insert_block)
        self.insert_block_btn.setEnabled(False)
        blocks_toolbar.addWidget(self.insert_block_btn)

        self.edit_block_btn = QPushButton("Edit")
        self.edit_block_btn.setToolTip("Edit selected block")
        self.edit_block_btn.clicked.connect(self._edit_block)
        self.edit_block_btn.setEnabled(False)
        blocks_toolbar.addWidget(self.edit_block_btn)

        self.delete_block_btn = QPushButton("Delete")
        self.delete_block_btn.setToolTip("Delete selected block")
        self.delete_block_btn.clicked.connect(self._delete_block)
        self.delete_block_btn.setEnabled(False)
        blocks_toolbar.addWidget(self.delete_block_btn)

        blocks_toolbar.addStretch()

        blocks_layout.addLayout(blocks_toolbar)

        # Blocks tree
        self.blocks_tree = QTreeWidget()
        self.blocks_tree.setHeaderLabels(["Name", "Type", "Entities"])
        self.blocks_tree.setRootIsDecorated(False)
        self.blocks_tree.setAlternatingRowColors(True)
        self.blocks_tree.itemSelectionChanged.connect(self._on_block_selection_changed)
        self.blocks_tree.itemDoubleClicked.connect(self._on_block_double_clicked)
        self.blocks_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.blocks_tree.customContextMenuRequested.connect(self._show_block_context_menu)
        blocks_layout.addWidget(self.blocks_tree)

        main_splitter.addWidget(blocks_group)

        # Block details
        details_group = QGroupBox("Block Details")
        details_layout = QVBoxLayout(details_group)

        # Block info
        info_layout = QVBoxLayout()
        
        self.block_name_label = QLabel("Name: -")
        self.block_name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.block_name_label)

        self.block_description_label = QLabel("Description: -")
        info_layout.addWidget(self.block_description_label)

        self.block_stats_label = QLabel("Entities: - | Attributes: -")
        info_layout.addWidget(self.block_stats_label)

        self.block_author_label = QLabel("Author: -")
        info_layout.addWidget(self.block_author_label)

        details_layout.addLayout(info_layout)

        # Block preview (placeholder)
        self.block_preview = QLabel("No preview available")
        self.block_preview.setMinimumHeight(100)
        self.block_preview.setMaximumHeight(150)
        self.block_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.block_preview.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        details_layout.addWidget(self.block_preview)

        main_splitter.addWidget(details_group)
        main_splitter.setSizes([300, 200])

        layout.addWidget(main_splitter)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.status_label)

    def _setup_connections(self):
        """Setup signal connections."""
        pass

    async def _load_data(self):
        """Load blocks and libraries data."""
        try:
            self.status_label.setText("Loading blocks...")
            
            # Load libraries first
            await self._load_libraries()
            
            # Load blocks
            await self._load_blocks()
            
            self.status_label.setText("Ready")
            
        except Exception as e:
            logger.error(f"Error loading blocks data: {e}")
            self.status_label.setText(f"Error: {str(e)}")

    async def _load_libraries(self):
        """Load block libraries."""
        # For now, just add a default library
        # In a real implementation, this would load from the API
        if not self.library_combo.count():
            self.library_combo.addItem("Default Library")
            self.current_library_id = "default"

    async def _load_blocks(self):
        """Load blocks from the API."""
        try:
            if not self.api_client:
                return

            # Prepare request
            request = {}
            if self.current_library_id:
                request["library_id"] = self.current_library_id
            if self.current_category and self.current_category != "All":
                request["category"] = self.current_category
            
            search_text = self.search_edit.text().strip()
            if search_text:
                request["search_query"] = search_text

            # Call API
            response = await self.api_client.get_blocks(request)
            if response.get("success", False):
                blocks_data = response.get("data", {}).get("blocks", [])
                self._update_blocks_display(blocks_data)
            else:
                error_msg = response.get("error_message", "Unknown error")
                logger.error(f"Failed to load blocks: {error_msg}")

        except Exception as e:
            logger.error(f"Error loading blocks: {e}")

    def _update_blocks_display(self, blocks_data: List[Dict[str, Any]]):
        """Update the blocks tree display."""
        self.blocks_tree.clear()
        self.blocks_data.clear()

        for block_data in blocks_data:
            block_id = block_data["id"]
            self.blocks_data[block_id] = block_data

            # Create tree item
            item = QTreeWidgetItem()
            item.setText(0, block_data["name"])
            item.setText(1, block_data.get("block_type", "static").title())
            item.setText(2, str(block_data.get("entity_count", 0)))
            item.setData(0, Qt.ItemDataRole.UserRole, block_id)

            # Set icon based on block type
            block_type = block_data.get("block_type", "static")
            if block_type == "dynamic":
                item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
            elif block_type == "annotative":
                item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView))
            else:
                item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))

            self.blocks_tree.addTopLevelItem(item)

        # Update status
        count = len(blocks_data)
        self.status_label.setText(f"{count} block{'s' if count != 1 else ''} found")

    def _on_library_changed(self, library_name: str):
        """Handle library selection change."""
        self.current_library_id = library_name.lower().replace(" ", "_")
        asyncio.create_task(self._load_blocks())

    def _on_category_changed(self, category: str):
        """Handle category selection change."""
        self.current_category = category
        asyncio.create_task(self._load_blocks())

    def _on_search_changed(self, text: str):
        """Handle search text change."""
        # Debounce search
        if hasattr(self, "_search_timer"):
            self._search_timer.stop()
        
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(lambda: asyncio.create_task(self._load_blocks()))
        self._search_timer.start(500)  # 500ms delay

    def _clear_search(self):
        """Clear search text."""
        self.search_edit.clear()

    def _on_block_selection_changed(self):
        """Handle block selection change."""
        selected_items = self.blocks_tree.selectedItems()
        if selected_items:
            item = selected_items[0]
            block_id = item.data(0, Qt.ItemDataRole.UserRole)
            self._update_block_details(block_id)
            
            # Enable/disable buttons
            self.insert_block_btn.setEnabled(True)
            self.edit_block_btn.setEnabled(True)
            self.delete_block_btn.setEnabled(True)
            
            # Emit signal
            self.block_selected.emit(block_id)
        else:
            self._clear_block_details()
            
            # Disable buttons
            self.insert_block_btn.setEnabled(False)
            self.edit_block_btn.setEnabled(False)
            self.delete_block_btn.setEnabled(False)

    def _on_block_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle block double-click to insert."""
        self._insert_block()

    def _update_block_details(self, block_id: str):
        """Update block details display."""
        if block_id not in self.blocks_data:
            self._clear_block_details()
            return

        block_data = self.blocks_data[block_id]
        
        self.block_name_label.setText(f"Name: {block_data['name']}")
        self.block_description_label.setText(f"Description: {block_data.get('description', 'No description')}")
        
        entity_count = block_data.get("entity_count", 0)
        attr_count = block_data.get("attribute_count", 0)
        self.block_stats_label.setText(f"Entities: {entity_count} | Attributes: {attr_count}")
        
        self.block_author_label.setText(f"Author: {block_data.get('author', 'Unknown')}")

        # TODO: Load and display block preview image
        self.block_preview.setText("Preview not available")

    def _clear_block_details(self):
        """Clear block details display."""
        self.block_name_label.setText("Name: -")
        self.block_description_label.setText("Description: -")
        self.block_stats_label.setText("Entities: - | Attributes: -")
        self.block_author_label.setText("Author: -")
        self.block_preview.setText("No preview available")

    def _show_block_context_menu(self, position):
        """Show context menu for block."""
        item = self.blocks_tree.itemAt(position)
        if not item:
            return

        block_id = item.data(0, Qt.ItemDataRole.UserRole)
        block_data = self.blocks_data.get(block_id)
        if not block_data:
            return

        menu = QMenu(self)
        
        # Insert action
        insert_action = menu.addAction("Insert Block")
        insert_action.triggered.connect(self._insert_block)
        
        menu.addSeparator()
        
        # Edit actions
        edit_action = menu.addAction("Edit Block")
        edit_action.triggered.connect(self._edit_block)
        
        rename_action = menu.addAction("Rename Block")
        rename_action.triggered.connect(self._rename_block)
        
        menu.addSeparator()
        
        # Copy/Export actions
        copy_action = menu.addAction("Copy Block")
        copy_action.triggered.connect(self._copy_block)
        
        export_action = menu.addAction("Export Block")
        export_action.triggered.connect(self._export_block)
        
        menu.addSeparator()
        
        # Delete action
        delete_action = menu.addAction("Delete Block")
        delete_action.triggered.connect(self._delete_block)
        
        menu.exec(self.blocks_tree.mapToGlobal(position))

    def _create_block(self):
        """Create a new block."""
        # This would typically open a dialog or activate the block creation tool
        self.block_created.emit({})

    def _insert_block(self):
        """Insert the selected block."""
        selected_items = self.blocks_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a block to insert.")
            return

        item = selected_items[0]
        block_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Default insertion data
        insertion_data = {
            "scale": 1.0,
            "rotation": 0.0,
            "attributes": {}
        }
        
        self.block_inserted.emit(block_id, insertion_data)

    def _edit_block(self):
        """Edit the selected block."""
        selected_items = self.blocks_tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        block_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # TODO: Open block editor dialog
        QMessageBox.information(self, "Edit Block", f"Block editor for '{block_id}' not implemented yet.")

    def _rename_block(self):
        """Rename the selected block."""
        selected_items = self.blocks_tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        block_id = item.data(0, Qt.ItemDataRole.UserRole)
        block_data = self.blocks_data.get(block_id)
        if not block_data:
            return

        current_name = block_data["name"]
        new_name, ok = QInputDialog.getText(
            self, "Rename Block", "Enter new name:", text=current_name
        )
        
        if ok and new_name.strip() and new_name.strip() != current_name:
            asyncio.create_task(self._update_block_name(block_id, new_name.strip()))

    async def _update_block_name(self, block_id: str, new_name: str):
        """Update block name via API."""
        try:
            if not self.api_client:
                return

            request = {
                "block_id": block_id,
                "updates": {"name": new_name}
            }
            
            response = await self.api_client.update_block(request)
            if response.get("success", False):
                await self._load_blocks()  # Refresh
                QMessageBox.information(self, "Success", f"Block renamed to '{new_name}'")
            else:
                error_msg = response.get("error_message", "Unknown error")
                QMessageBox.critical(self, "Error", f"Failed to rename block: {error_msg}")

        except Exception as e:
            logger.error(f"Error renaming block: {e}")
            QMessageBox.critical(self, "Error", f"Error renaming block: {str(e)}")

    def _copy_block(self):
        """Copy the selected block."""
        QMessageBox.information(self, "Copy Block", "Block copying not implemented yet.")

    def _export_block(self):
        """Export the selected block."""
        QMessageBox.information(self, "Export Block", "Block export not implemented yet.")

    def _delete_block(self):
        """Delete the selected block."""
        selected_items = self.blocks_tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        block_id = item.data(0, Qt.ItemDataRole.UserRole)
        block_data = self.blocks_data.get(block_id)
        if not block_data:
            return

        reply = QMessageBox.question(
            self,
            "Delete Block",
            f"Are you sure you want to delete block '{block_data['name']}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            asyncio.create_task(self._delete_block_api(block_id))

    async def _delete_block_api(self, block_id: str):
        """Delete block via API."""
        try:
            if not self.api_client:
                return

            request = {"block_id": block_id}
            
            response = await self.api_client.delete_block(request)
            if response.get("success", False):
                await self._load_blocks()  # Refresh
                self.block_deleted.emit(block_id)
                QMessageBox.information(self, "Success", "Block deleted successfully")
            else:
                error_msg = response.get("error_message", "Unknown error")
                QMessageBox.critical(self, "Error", f"Failed to delete block: {error_msg}")

        except Exception as e:
            logger.error(f"Error deleting block: {e}")
            QMessageBox.critical(self, "Error", f"Error deleting block: {str(e)}")

    def _create_new_library(self):
        """Create a new block library."""
        QMessageBox.information(self, "New Library", "Library creation not implemented yet.")

    def refresh(self):
        """Refresh the blocks display."""
        asyncio.create_task(self._load_blocks())

    def get_selected_block_id(self) -> Optional[str]:
        """Get the currently selected block ID."""
        selected_items = self.blocks_tree.selectedItems()
        if selected_items:
            return selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        return None