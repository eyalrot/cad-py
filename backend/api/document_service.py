"""Document service implementation."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from backend.models import CADDocument, DocumentSerializer

from .converters import ProtobufConverters

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document operations."""

    def __init__(self):
        self._documents: Dict[str, CADDocument] = {}

    def create_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document."""
        try:
            name = request.get("name", "")
            if not name:
                return ProtobufConverters.create_error_response(
                    error_message="Document name is required"
                )

            # Create document
            document = CADDocument(name)

            # Set optional fields
            if "description" in request:
                document.set_description(request["description"])

            if "metadata" in request:
                document.update_metadata(**dict(request["metadata"]))

            # Store document
            self._documents[document.id] = document

            logger.info(f"Created document: {document.id} - {document.name}")

            return ProtobufConverters.create_success_response(
                {"document": ProtobufConverters.document_to_proto(document)}
            )

        except Exception as e:
            logger.error(f"Error creating document: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to create document: {str(e)}"
            )

    def open_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Open an existing document."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            document = self._documents.get(document_id)
            if not document:
                return {
                    "found": False,
                    "error_message": f"Document {document_id} not found",
                }

            logger.info(f"Opened document: {document_id}")

            return {
                "document": ProtobufConverters.document_to_proto(document),
                "found": True,
                "error_message": "",
            }

        except Exception as e:
            logger.error(f"Error opening document: {e}")
            return {
                "found": False,
                "error_message": f"Failed to open document: {str(e)}",
            }

    def save_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Save a document to file."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            document = self._documents.get(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            # Determine file path and format
            file_path = request.get("file_path")
            if not file_path:
                file_path = f"documents/{document.name}_{document.id}.json"

            format_type = request.get("format", "json").lower()

            # Save document
            if format_type == "json":
                DocumentSerializer.save_json(document, file_path)
            elif format_type == "binary":
                DocumentSerializer.save_binary(document, file_path)
            else:
                return ProtobufConverters.create_error_response(
                    error_message=f"Unsupported format: {format_type}"
                )

            logger.info(f"Saved document {document_id} to {file_path}")

            return ProtobufConverters.create_success_response(
                {"file_path": str(file_path)}
            )

        except Exception as e:
            logger.error(f"Error saving document: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to save document: {str(e)}"
            )

    def load_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Load a document from file."""
        try:
            file_path = request.get("file_path", "")
            if not file_path:
                return ProtobufConverters.create_error_response(
                    error_message="File path is required"
                )

            if not Path(file_path).exists():
                return ProtobufConverters.create_error_response(
                    error_message=f"File not found: {file_path}"
                )

            format_type = request.get("format", "json").lower()

            # Load document
            if format_type == "json":
                document = DocumentSerializer.load_json(file_path)
            elif format_type == "binary":
                document = DocumentSerializer.load_binary(file_path)
            else:
                return ProtobufConverters.create_error_response(
                    error_message=f"Unsupported format: {format_type}"
                )

            # Store loaded document
            self._documents[document.id] = document

            logger.info(f"Loaded document {document.id} from {file_path}")

            return ProtobufConverters.create_success_response(
                {"document": ProtobufConverters.document_to_proto(document)}
            )

        except Exception as e:
            logger.error(f"Error loading document: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to load document: {str(e)}"
            )

    def update_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Update document properties."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            document = self._documents.get(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            # Update fields if provided
            if "name" in request:
                document.set_name(request["name"])

            if "description" in request:
                document.set_description(request["description"])

            if "metadata" in request:
                document.update_metadata(**dict(request["metadata"]))

            logger.info(f"Updated document: {document_id}")

            return ProtobufConverters.create_success_response(
                {"document": ProtobufConverters.document_to_proto(document)}
            )

        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to update document: {str(e)}"
            )

    def delete_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a document."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            if document_id not in self._documents:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            del self._documents[document_id]

            logger.info(f"Deleted document: {document_id}")

            return ProtobufConverters.create_success_response()

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to delete document: {str(e)}"
            )

    def get_document_statistics(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get document statistics."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            document = self._documents.get(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            return ProtobufConverters.create_success_response(
                {
                    "statistics": ProtobufConverters.document_statistics_to_proto(
                        document
                    )
                }
            )

        except Exception as e:
            logger.error(f"Error getting document statistics: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to get document statistics: {str(e)}"
            )

    def list_documents(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """List all documents."""
        try:
            limit = request.get("limit")
            offset = request.get("offset", 0)

            documents = list(self._documents.values())
            total_count = len(documents)

            # Apply pagination
            if limit:
                documents = documents[offset : offset + limit]
            elif offset:
                documents = documents[offset:]

            return ProtobufConverters.create_success_response(
                {
                    "documents": [
                        ProtobufConverters.document_to_proto(doc) for doc in documents
                    ],
                    "total_count": total_count,
                }
            )

        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to list documents: {str(e)}"
            )

    def get_document(self, document_id: str) -> Optional[CADDocument]:
        """Get document by ID (internal method)."""
        return self._documents.get(document_id)
