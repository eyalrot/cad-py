"""
Command pattern implementation for CAD operations with undo/redo support.

This module provides a comprehensive command pattern infrastructure that integrates
with the gRPC API client to provide undo/redo functionality for all CAD operations.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from PySide6.QtCore import QObject, Signal

from .api_client import APIClientManager


class CommandState(Enum):
    """Command execution state."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    UNDOING = "undoing"
    UNDONE = "undone"


class CommandType(Enum):
    """Types of commands for categorization."""

    DRAWING = "drawing"
    EDITING = "editing"
    LAYER = "layer"
    DOCUMENT = "document"
    SELECTION = "selection"
    VIEW = "view"


class Command(ABC):
    """
    Abstract base class for all commands.

    Commands encapsulate operations that can be executed and undone,
    providing the foundation for the undo/redo system.
    """

    def __init__(
        self, description: str, command_type: CommandType = CommandType.DRAWING
    ):
        """
        Initialize command.

        Args:
            description: Human-readable description of the command
            command_type: Type/category of the command
        """
        self.description = description
        self.command_type = command_type
        self.state = CommandState.PENDING
        self.timestamp = time.time()
        self.execution_time: Optional[float] = None
        self.error_message: Optional[str] = None

        # Command data storage
        self.execution_data: Dict[str, Any] = {}
        self.undo_data: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self) -> bool:
        """
        Execute the command.

        Returns:
            True if execution was successful, False otherwise
        """
        pass

    @abstractmethod
    async def undo(self) -> bool:
        """
        Undo the command.

        Returns:
            True if undo was successful, False otherwise
        """
        pass

    @abstractmethod
    def can_undo(self) -> bool:
        """
        Check if the command can be undone.

        Returns:
            True if the command can be undone
        """
        pass

    def get_description(self) -> str:
        """Get human-readable description of the command."""
        return self.description

    def get_detailed_info(self) -> Dict[str, Any]:
        """Get detailed information about the command."""
        return {
            "description": self.description,
            "type": self.command_type.value,
            "state": self.state.value,
            "timestamp": self.timestamp,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "can_undo": self.can_undo(),
        }

    async def _execute_with_state_management(self) -> bool:
        """Execute command with proper state management."""
        self.state = CommandState.EXECUTING
        start_time = time.time()

        try:
            result = await self.execute()
            self.execution_time = time.time() - start_time

            if result:
                self.state = CommandState.COMPLETED
            else:
                self.state = CommandState.FAILED

            return result

        except Exception as e:
            self.execution_time = time.time() - start_time
            self.state = CommandState.FAILED
            self.error_message = str(e)
            logging.error(f"Command execution failed: {e}")
            return False

    async def _undo_with_state_management(self) -> bool:
        """Undo command with proper state management."""
        if not self.can_undo():
            return False

        self.state = CommandState.UNDOING

        try:
            result = await self.undo()

            if result:
                self.state = CommandState.UNDONE
            else:
                self.state = CommandState.FAILED

            return result

        except Exception as e:
            self.state = CommandState.FAILED
            self.error_message = str(e)
            logging.error(f"Command undo failed: {e}")
            return False


class CompositeCommand(Command):
    """
    Command that contains multiple sub-commands.

    Useful for operations that involve multiple steps that should be
    treated as a single undoable unit.
    """

    def __init__(
        self,
        description: str,
        commands: List[Command],
        command_type: CommandType = CommandType.EDITING,
    ):
        """
        Initialize composite command.

        Args:
            description: Description of the composite operation
            commands: List of sub-commands to execute
            command_type: Type of the composite command
        """
        super().__init__(description, command_type)
        self.commands = commands
        self.executed_commands: List[Command] = []

    async def execute(self) -> bool:
        """Execute all sub-commands in order."""
        self.executed_commands.clear()

        for command in self.commands:
            if await command._execute_with_state_management():
                self.executed_commands.append(command)
            else:
                # If any command fails, undo all previously executed commands
                await self._undo_executed_commands()
                return False

        return True

    async def undo(self) -> bool:
        """Undo all executed sub-commands in reverse order."""
        return await self._undo_executed_commands()

    async def _undo_executed_commands(self) -> bool:
        """Undo all executed commands in reverse order."""
        success = True

        # Undo in reverse order
        for command in reversed(self.executed_commands):
            if not await command._undo_with_state_management():
                success = False
                # Continue undoing other commands even if one fails

        if success:
            self.executed_commands.clear()

        return success

    def can_undo(self) -> bool:
        """Check if all executed commands can be undone."""
        return self.state == CommandState.COMPLETED and all(
            cmd.can_undo() for cmd in self.executed_commands
        )


class CommandManager(QObject):
    """
    Manages command execution, history, and undo/redo operations.

    This class provides the central interface for executing commands
    and managing the undo/redo stack with memory management.
    """

    # Signals for UI updates
    command_executed = Signal(dict)  # command info
    command_undone = Signal(dict)  # command info
    command_redone = Signal(dict)  # command info
    history_changed = Signal()  # history stack changed

    def __init__(
        self,
        api_client: APIClientManager,
        max_history: int = 100,
        max_memory_mb: float = 50.0,
        parent=None,
    ):
        """
        Initialize command manager.

        Args:
            api_client: API client for backend communication
            max_history: Maximum number of commands to keep in history
            max_memory_mb: Maximum memory usage for command history (MB)
            parent: Qt parent object
        """
        super().__init__(parent)

        self.api_client = api_client
        self.max_history = max_history
        self.max_memory_bytes = max_memory_mb * 1024 * 1024

        # Command stacks
        self.undo_stack: deque[Command] = deque(maxlen=max_history)
        self.redo_stack: List[Command] = []

        # State tracking
        self.is_executing = False
        self.current_command: Optional[Command] = None

        # Memory management
        self.estimated_memory_usage = 0

        self.logger = logging.getLogger(__name__)

    async def execute_command(self, command: Command) -> bool:
        """
        Execute a command and add it to the undo stack.

        Args:
            command: Command to execute

        Returns:
            True if execution was successful
        """
        if self.is_executing:
            self.logger.warning("Cannot execute command while another is executing")
            return False

        self.is_executing = True
        self.current_command = command

        try:
            # Execute the command
            success = await command._execute_with_state_management()

            if success:
                # Add to undo stack and clear redo stack
                self.undo_stack.append(command)
                self.redo_stack.clear()

                # Manage memory usage
                self._manage_memory()

                # Emit signals
                self.command_executed.emit(command.get_detailed_info())
                self.history_changed.emit()

                self.logger.info(f"Command executed: {command.get_description()}")
            else:
                self.logger.warning(
                    f"Command execution failed: {command.get_description()}"
                )

            return success

        finally:
            self.is_executing = False
            self.current_command = None

    async def undo(self) -> bool:
        """
        Undo the last command.

        Returns:
            True if undo was successful
        """
        if self.is_executing or not self.undo_stack:
            return False

        command = self.undo_stack.pop()

        if not command.can_undo():
            # Put it back if it can't be undone
            self.undo_stack.append(command)
            return False

        self.is_executing = True

        try:
            success = await command._undo_with_state_management()

            if success:
                # Move to redo stack
                self.redo_stack.append(command)

                # Emit signals
                self.command_undone.emit(command.get_detailed_info())
                self.history_changed.emit()

                self.logger.info(f"Command undone: {command.get_description()}")
            else:
                # Put it back in undo stack if undo failed
                self.undo_stack.append(command)
                self.logger.warning(f"Command undo failed: {command.get_description()}")

            return success

        finally:
            self.is_executing = False

    async def redo(self) -> bool:
        """
        Redo the last undone command.

        Returns:
            True if redo was successful
        """
        if self.is_executing or not self.redo_stack:
            return False

        command = self.redo_stack.pop()

        self.is_executing = True

        try:
            success = await command._execute_with_state_management()

            if success:
                # Move back to undo stack
                self.undo_stack.append(command)

                # Emit signals
                self.command_redone.emit(command.get_detailed_info())
                self.history_changed.emit()

                self.logger.info(f"Command redone: {command.get_description()}")
            else:
                # Put it back in redo stack if redo failed
                self.redo_stack.append(command)
                self.logger.warning(f"Command redo failed: {command.get_description()}")

            return success

        finally:
            self.is_executing = False

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return bool(self.undo_stack and not self.is_executing)

    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return bool(self.redo_stack and not self.is_executing)

    def get_undo_description(self) -> Optional[str]:
        """Get description of the command that would be undone."""
        if self.undo_stack:
            return self.undo_stack[-1].get_description()
        return None

    def get_redo_description(self) -> Optional[str]:
        """Get description of the command that would be redone."""
        if self.redo_stack:
            return self.redo_stack[-1].get_description()
        return None

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get command history information.

        Returns:
            List of command information dictionaries
        """
        history = []

        # Add undo stack (most recent first)
        for command in reversed(self.undo_stack):
            info = command.get_detailed_info()
            info["stack"] = "undo"
            history.append(info)

        # Add redo stack
        for command in reversed(self.redo_stack):
            info = command.get_detailed_info()
            info["stack"] = "redo"
            history.append(info)

        return history

    def clear_history(self):
        """Clear all command history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.estimated_memory_usage = 0
        self.history_changed.emit()
        self.logger.info("Command history cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about command usage.

        Returns:
            Dictionary containing usage statistics
        """
        total_commands = len(self.undo_stack) + len(self.redo_stack)

        # Count by type
        type_counts = {}
        for command in list(self.undo_stack) + self.redo_stack:
            cmd_type = command.command_type.value
            type_counts[cmd_type] = type_counts.get(cmd_type, 0) + 1

        return {
            "total_commands": total_commands,
            "undo_stack_size": len(self.undo_stack),
            "redo_stack_size": len(self.redo_stack),
            "estimated_memory_mb": self.estimated_memory_usage / (1024 * 1024),
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            "max_history": self.max_history,
            "by_type": type_counts,
            "is_executing": self.is_executing,
        }

    def _manage_memory(self):
        """Manage memory usage by removing old commands if necessary."""
        # Simple estimation based on number of commands
        # In a real implementation, you'd want more sophisticated memory tracking
        self.estimated_memory_usage = (
            len(self.undo_stack) + len(self.redo_stack)
        ) * 1024

        # Remove oldest commands if over memory limit
        while (
            self.estimated_memory_usage > self.max_memory_bytes
            and len(self.undo_stack) > 1
        ):
            # Remove from the beginning of undo stack (oldest)
            removed_command = self.undo_stack.popleft()
            self.estimated_memory_usage -= 1024  # Rough estimation

            self.logger.debug(
                f"Removed old command from history: {removed_command.get_description()}"
            )

    def _estimate_command_memory(self, command: Command) -> int:
        """
        Estimate memory usage of a command.

        Args:
            command: Command to estimate

        Returns:
            Estimated memory usage in bytes
        """
        # Simple estimation - in reality you'd want more sophisticated tracking
        base_size = 1024  # Base overhead

        # Add estimated size for data
        data_size = 0
        for data_dict in [command.execution_data, command.undo_data]:
            data_size += len(str(data_dict))

        return base_size + data_size
