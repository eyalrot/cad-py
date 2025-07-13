"""
Concrete command implementations for CAD operations.

This module contains specific command implementations for drawing,
editing, and managing CAD entities and documents.
"""

import logging
from typing import Any, Dict, List, Optional

from .api_client import APIClientManager
from .command_manager import Command, CommandType


class DrawLineCommand(Command):
    """Command to draw a line."""

    def __init__(
        self,
        api_client: APIClientManager,
        document_id: str,
        start: Dict[str, float],
        end: Dict[str, float],
        layer_id: Optional[str] = None,
        properties: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize draw line command.

        Args:
            api_client: API client for backend communication
            document_id: ID of the document to draw in
            start: Start point coordinates {x, y, z}
            end: End point coordinates {x, y, z}
            layer_id: Optional layer ID
            properties: Optional entity properties
        """
        super().__init__(
            f"Draw Line ({start['x']:.1f},{start['y']:.1f}) to ({end['x']:.1f},{end['y']:.1f})",
            CommandType.DRAWING,
        )

        self.api_client = api_client
        self.document_id = document_id
        self.start = start.copy()
        self.end = end.copy()
        self.layer_id = layer_id
        self.properties = properties.copy() if properties else {}

        # Will be set during execution
        self.entity_id: Optional[str] = None

    async def execute(self) -> bool:
        """Execute the draw line command."""
        try:
            # Store execution parameters
            self.execution_data = {
                "document_id": self.document_id,
                "start": self.start,
                "end": self.end,
                "layer_id": self.layer_id,
                "properties": self.properties,
            }

            # Execute the drawing operation
            result = await self.api_client.client.draw_line(
                self.document_id, self.start, self.end, self.layer_id, self.properties
            )

            if result and "id" in result:
                self.entity_id = result["id"]
                self.undo_data = {"entity_id": self.entity_id}
                return True

            return False

        except Exception as e:
            logging.error(f"DrawLineCommand execution failed: {e}")
            return False

    async def undo(self) -> bool:
        """Undo the draw line command by deleting the entity."""
        if not self.entity_id:
            return False

        try:
            success = await self.api_client.client.delete_entity(self.entity_id)
            if success:
                self.entity_id = None
            return success

        except Exception as e:
            logging.error(f"DrawLineCommand undo failed: {e}")
            return False

    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        return self.state.value in ["completed"] and self.entity_id is not None


class DrawCircleCommand(Command):
    """Command to draw a circle."""

    def __init__(
        self,
        api_client: APIClientManager,
        document_id: str,
        center: Dict[str, float],
        radius: float,
        layer_id: Optional[str] = None,
        properties: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize draw circle command.

        Args:
            api_client: API client for backend communication
            document_id: ID of the document to draw in
            center: Center point coordinates {x, y, z}
            radius: Circle radius
            layer_id: Optional layer ID
            properties: Optional entity properties
        """
        super().__init__(
            f"Draw Circle at ({center['x']:.1f},{center['y']:.1f}) R={radius:.1f}",
            CommandType.DRAWING,
        )

        self.api_client = api_client
        self.document_id = document_id
        self.center = center.copy()
        self.radius = radius
        self.layer_id = layer_id
        self.properties = properties.copy() if properties else {}

        self.entity_id: Optional[str] = None

    async def execute(self) -> bool:
        """Execute the draw circle command."""
        try:
            self.execution_data = {
                "document_id": self.document_id,
                "center": self.center,
                "radius": self.radius,
                "layer_id": self.layer_id,
                "properties": self.properties,
            }

            result = await self.api_client.client.draw_circle(
                self.document_id,
                self.center,
                self.radius,
                self.layer_id,
                self.properties,
            )

            if result and "id" in result:
                self.entity_id = result["id"]
                self.undo_data = {"entity_id": self.entity_id}
                return True

            return False

        except Exception as e:
            logging.error(f"DrawCircleCommand execution failed: {e}")
            return False

    async def undo(self) -> bool:
        """Undo the draw circle command."""
        if not self.entity_id:
            return False

        try:
            success = await self.api_client.client.delete_entity(self.entity_id)
            if success:
                self.entity_id = None
            return success

        except Exception as e:
            logging.error(f"DrawCircleCommand undo failed: {e}")
            return False

    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        return self.state.value in ["completed"] and self.entity_id is not None


class DrawArcCommand(Command):
    """Command to draw an arc."""

    def __init__(
        self,
        api_client: APIClientManager,
        document_id: str,
        center: Dict[str, float],
        radius: float,
        start_angle: float,
        end_angle: float,
        layer_id: Optional[str] = None,
        properties: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize draw arc command.

        Args:
            api_client: API client for backend communication
            document_id: ID of the document to draw in
            center: Center point coordinates {x, y, z}
            radius: Arc radius
            start_angle: Start angle in radians
            end_angle: End angle in radians
            layer_id: Optional layer ID
            properties: Optional entity properties
        """
        super().__init__(
            f"Draw Arc at ({center['x']:.1f},{center['y']:.1f}) R={radius:.1f}",
            CommandType.DRAWING,
        )

        self.api_client = api_client
        self.document_id = document_id
        self.center = center.copy()
        self.radius = radius
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.layer_id = layer_id
        self.properties = properties.copy() if properties else {}

        self.entity_id: Optional[str] = None

    async def execute(self) -> bool:
        """Execute the draw arc command."""
        try:
            self.execution_data = {
                "document_id": self.document_id,
                "center": self.center,
                "radius": self.radius,
                "start_angle": self.start_angle,
                "end_angle": self.end_angle,
                "layer_id": self.layer_id,
                "properties": self.properties,
            }

            result = await self.api_client.client.draw_arc(
                self.document_id,
                self.center,
                self.radius,
                self.start_angle,
                self.end_angle,
                self.layer_id,
                self.properties,
            )

            if result and "id" in result:
                self.entity_id = result["id"]
                self.undo_data = {"entity_id": self.entity_id}
                return True

            return False

        except Exception as e:
            logging.error(f"DrawArcCommand execution failed: {e}")
            return False

    async def undo(self) -> bool:
        """Undo the draw arc command."""
        if not self.entity_id:
            return False

        try:
            success = await self.api_client.client.delete_entity(self.entity_id)
            if success:
                self.entity_id = None
            return success

        except Exception as e:
            logging.error(f"DrawArcCommand undo failed: {e}")
            return False

    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        return self.state.value in ["completed"] and self.entity_id is not None


class DeleteEntityCommand(Command):
    """Command to delete an entity."""

    def __init__(
        self, api_client: APIClientManager, entity_id: str, entity_data: Dict[str, Any]
    ):
        """
        Initialize delete entity command.

        Args:
            api_client: API client for backend communication
            entity_id: ID of the entity to delete
            entity_data: Complete entity data for restoration
        """
        super().__init__(f"Delete Entity {entity_id}", CommandType.EDITING)

        self.api_client = api_client
        self.entity_id = entity_id
        self.entity_data = entity_data.copy()
        self.was_deleted = False

    async def execute(self) -> bool:
        """Execute the delete entity command."""
        try:
            self.execution_data = {
                "entity_id": self.entity_id,
                "entity_data": self.entity_data,
            }

            success = await self.api_client.client.delete_entity(self.entity_id)

            if success:
                self.was_deleted = True
                self.undo_data = {"entity_data": self.entity_data}
                return True

            return False

        except Exception as e:
            logging.error(f"DeleteEntityCommand execution failed: {e}")
            return False

    async def undo(self) -> bool:
        """Undo the delete by recreating the entity."""
        if not self.was_deleted:
            return False

        try:
            # Recreate the entity using its stored data
            result = await self.api_client.client.create_entity(
                self.entity_data.get("document_id"),
                self.entity_data.get("type"),
                self.entity_data.get("geometry"),
                self.entity_data.get("layer_id"),
                self.entity_data.get("properties"),
            )

            if result and "id" in result:
                # Update the entity ID to the new one
                self.entity_id = result["id"]
                self.was_deleted = False
                return True

            return False

        except Exception as e:
            logging.error(f"DeleteEntityCommand undo failed: {e}")
            return False

    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        return self.state.value in ["completed"] and self.was_deleted


class MoveEntityCommand(Command):
    """Command to move an entity."""

    def __init__(
        self,
        api_client: APIClientManager,
        entity_id: str,
        old_position: Dict[str, float],
        new_position: Dict[str, float],
    ):
        """
        Initialize move entity command.

        Args:
            api_client: API client for backend communication
            entity_id: ID of the entity to move
            old_position: Original position
            new_position: New position
        """
        delta_x = new_position["x"] - old_position["x"]
        delta_y = new_position["y"] - old_position["y"]
        super().__init__(
            f"Move Entity {entity_id} by ({delta_x:.1f},{delta_y:.1f})",
            CommandType.EDITING,
        )

        self.api_client = api_client
        self.entity_id = entity_id
        self.old_position = old_position.copy()
        self.new_position = new_position.copy()
        self.move_successful = False

    async def execute(self) -> bool:
        """Execute the move entity command."""
        try:
            self.execution_data = {
                "entity_id": self.entity_id,
                "old_position": self.old_position,
                "new_position": self.new_position,
            }

            # Calculate movement vector
            delta = {
                "x": self.new_position["x"] - self.old_position["x"],
                "y": self.new_position["y"] - self.old_position["y"],
                "z": self.new_position.get("z", 0.0) - self.old_position.get("z", 0.0),
            }

            # Use the move entities API
            result = await self.api_client.client.stub.MoveEntities(
                {"entity_ids": [self.entity_id], "delta": delta}
            )

            if result and result.success:
                self.move_successful = True
                self.undo_data = {
                    "entity_id": self.entity_id,
                    "reverse_delta": {
                        "x": -delta["x"],
                        "y": -delta["y"],
                        "z": -delta["z"],
                    },
                }
                return True

            return False

        except Exception as e:
            logging.error(f"MoveEntityCommand execution failed: {e}")
            return False

    async def undo(self) -> bool:
        """Undo the move by moving back to original position."""
        if not self.move_successful:
            return False

        try:
            reverse_delta = self.undo_data["reverse_delta"]

            result = await self.api_client.client.stub.MoveEntities(
                {"entity_ids": [self.entity_id], "delta": reverse_delta}
            )

            if result and result.success:
                self.move_successful = False
                return True

            return False

        except Exception as e:
            logging.error(f"MoveEntityCommand undo failed: {e}")
            return False

    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        return self.state.value in ["completed"] and self.move_successful


class CreateLayerCommand(Command):
    """Command to create a layer."""

    def __init__(
        self,
        api_client: APIClientManager,
        document_id: str,
        name: str,
        **layer_properties,
    ):
        """
        Initialize create layer command.

        Args:
            api_client: API client for backend communication
            document_id: ID of the document
            name: Layer name
            **layer_properties: Additional layer properties
        """
        super().__init__(f"Create Layer '{name}'", CommandType.LAYER)

        self.api_client = api_client
        self.document_id = document_id
        self.layer_name = name
        self.layer_properties = layer_properties
        self.layer_id: Optional[str] = None

    async def execute(self) -> bool:
        """Execute the create layer command."""
        try:
            self.execution_data = {
                "document_id": self.document_id,
                "name": self.layer_name,
                "properties": self.layer_properties,
            }

            result = await self.api_client.client.create_layer(
                self.document_id, self.layer_name, **self.layer_properties
            )

            if result and "id" in result:
                self.layer_id = result["id"]
                self.undo_data = {"layer_id": self.layer_id}
                return True

            return False

        except Exception as e:
            logging.error(f"CreateLayerCommand execution failed: {e}")
            return False

    async def undo(self) -> bool:
        """Undo the create layer command by deleting the layer."""
        if not self.layer_id:
            return False

        try:
            success = await self.api_client.client.delete_layer(self.layer_id)
            if success:
                self.layer_id = None
            return success

        except Exception as e:
            logging.error(f"CreateLayerCommand undo failed: {e}")
            return False

    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        return self.state.value in ["completed"] and self.layer_id is not None


class CreateDocumentCommand(Command):
    """Command to create a document."""

    def __init__(
        self, api_client: APIClientManager, name: str, template_id: Optional[str] = None
    ):
        """
        Initialize create document command.

        Args:
            api_client: API client for backend communication
            name: Document name
            template_id: Optional template ID
        """
        super().__init__(f"Create Document '{name}'", CommandType.DOCUMENT)

        self.api_client = api_client
        self.document_name = name
        self.template_id = template_id
        self.document_id: Optional[str] = None

    async def execute(self) -> bool:
        """Execute the create document command."""
        try:
            self.execution_data = {
                "name": self.document_name,
                "template_id": self.template_id,
            }

            result = await self.api_client.client.create_document(
                self.document_name, self.template_id
            )

            if result and "id" in result:
                self.document_id = result["id"]
                self.undo_data = {"document_id": self.document_id}
                return True

            return False

        except Exception as e:
            logging.error(f"CreateDocumentCommand execution failed: {e}")
            return False

    async def undo(self) -> bool:
        """Undo the create document command by deleting the document."""
        if not self.document_id:
            return False

        try:
            # Note: This would need a delete_document method in the API client
            # For now, we'll assume it's not undoable
            logging.warning(
                "Document deletion not implemented - cannot undo create document"
            )
            return False

        except Exception as e:
            logging.error(f"CreateDocumentCommand undo failed: {e}")
            return False

    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        # Documents are typically not deleted automatically
        return False


# Factory functions for easier command creation


def create_draw_line_command(
    api_client: APIClientManager,
    document_id: str,
    start: Dict[str, float],
    end: Dict[str, float],
    **kwargs,
) -> DrawLineCommand:
    """Factory function to create a draw line command."""
    return DrawLineCommand(api_client, document_id, start, end, **kwargs)


def create_draw_circle_command(
    api_client: APIClientManager,
    document_id: str,
    center: Dict[str, float],
    radius: float,
    **kwargs,
) -> DrawCircleCommand:
    """Factory function to create a draw circle command."""
    return DrawCircleCommand(api_client, document_id, center, radius, **kwargs)


def create_draw_arc_command(
    api_client: APIClientManager,
    document_id: str,
    center: Dict[str, float],
    radius: float,
    start_angle: float,
    end_angle: float,
    **kwargs,
) -> DrawArcCommand:
    """Factory function to create a draw arc command."""
    return DrawArcCommand(
        api_client, document_id, center, radius, start_angle, end_angle, **kwargs
    )


def create_delete_entity_command(
    api_client: APIClientManager, entity_id: str, entity_data: Dict[str, Any]
) -> DeleteEntityCommand:
    """Factory function to create a delete entity command."""
    return DeleteEntityCommand(api_client, entity_id, entity_data)


def create_move_entity_command(
    api_client: APIClientManager,
    entity_id: str,
    old_position: Dict[str, float],
    new_position: Dict[str, float],
) -> MoveEntityCommand:
    """Factory function to create a move entity command."""
    return MoveEntityCommand(api_client, entity_id, old_position, new_position)


def create_layer_command(
    api_client: APIClientManager, document_id: str, name: str, **kwargs
) -> CreateLayerCommand:
    """Factory function to create a create layer command."""
    return CreateLayerCommand(api_client, document_id, name, **kwargs)


def create_document_command(
    api_client: APIClientManager, name: str, template_id: Optional[str] = None
) -> CreateDocumentCommand:
    """Factory function to create a create document command."""
    return CreateDocumentCommand(api_client, name, template_id)
