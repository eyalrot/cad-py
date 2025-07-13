"""
gRPC API client for Qt6 CAD application.

This module provides an async gRPC client wrapper that integrates with Qt6's
signal-slot system for non-blocking communication with the CAD backend.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from enum import Enum

import grpc
from PySide6.QtCore import QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import QApplication

# Import generated gRPC modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend/api/proto/generated'))

from cad_service_pb2_grpc import CADServiceStub
from cad_service_pb2 import *
from document_pb2 import *
from entity_pb2 import *
from layer_pb2 import *
from geometry_pb2 import *


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class CADAPIClient(QObject):
    """
    Async gRPC client for CAD operations with Qt6 integration.
    
    This client provides non-blocking access to the CAD backend service
    using Qt signals and slots for asynchronous communication.
    """
    
    # Connection signals
    connection_state_changed = Signal(str)  # ConnectionState.value
    connection_error = Signal(str)
    
    # Document signals
    document_created = Signal(dict)
    document_loaded = Signal(dict)
    document_saved = Signal(dict)
    document_updated = Signal(dict)
    document_deleted = Signal(str)  # document_id
    documents_listed = Signal(list)
    
    # Layer signals
    layer_created = Signal(dict)
    layer_updated = Signal(dict)
    layer_deleted = Signal(str)  # layer_id
    layers_listed = Signal(list)
    current_layer_set = Signal(str)  # layer_id
    
    # Entity signals
    entity_created = Signal(dict)
    entity_updated = Signal(dict)
    entity_deleted = Signal(str)  # entity_id
    entities_queried = Signal(list)
    entities_moved = Signal(list)
    
    # Batch operation signals
    entities_batch_created = Signal(list)
    entities_batch_deleted = Signal(list)
    
    # Drawing operation signals
    line_drawn = Signal(dict)
    circle_drawn = Signal(dict)
    arc_drawn = Signal(dict)
    rectangle_drawn = Signal(dict)
    polygon_drawn = Signal(dict)
    
    # Error signals
    error_occurred = Signal(str, str)  # operation, error_message
    
    def __init__(self, server_address: str = "localhost:50051", parent=None):
        """
        Initialize the CAD API client.
        
        Args:
            server_address: gRPC server address (host:port)
            parent: Qt parent object
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.server_address = server_address
        self.connection_state = ConnectionState.DISCONNECTED
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[CADServiceStub] = None
        
        # Connection management
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0  # seconds
        
        # Request queue for offline mode
        self.request_queue: List[Dict[str, Any]] = []
        self.queue_enabled = True
        
        # Health check timer
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self._check_connection_health)
        
    async def connect(self) -> bool:
        """
        Connect to the gRPC server.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self.connection_state == ConnectionState.CONNECTED:
            return True
            
        self._set_connection_state(ConnectionState.CONNECTING)
        
        try:
            # Create insecure channel (use secure channel in production)
            self.channel = grpc.aio.insecure_channel(
                self.server_address,
                options=[
                    ('grpc.keepalive_time_ms', 30000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.keepalive_permit_without_calls', True),
                    ('grpc.http2.max_pings_without_data', 0),
                    ('grpc.http2.min_time_between_pings_ms', 10000),
                    ('grpc.http2.min_ping_interval_without_data_ms', 300000)
                ]
            )
            
            self.stub = CADServiceStub(self.channel)
            
            # Test connection with a simple call
            await self._test_connection()
            
            self._set_connection_state(ConnectionState.CONNECTED)
            self.reconnect_attempts = 0
            
            # Start health check timer
            self.health_timer.start(30000)  # Check every 30 seconds
            
            # Process queued requests
            if self.request_queue:
                await self._process_request_queue()
            
            self.logger.info(f"Connected to CAD server at {self.server_address}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to server: {e}")
            self._set_connection_state(ConnectionState.ERROR)
            self.connection_error.emit(str(e))
            return False
    
    async def disconnect(self):
        """Disconnect from the gRPC server."""
        if self.channel:
            self.health_timer.stop()
            await self.channel.close()
            self.channel = None
            self.stub = None
            
        self._set_connection_state(ConnectionState.DISCONNECTED)
        self.logger.info("Disconnected from CAD server")
    
    def _set_connection_state(self, state: ConnectionState):
        """Update connection state and emit signal."""
        if self.connection_state != state:
            self.connection_state = state
            self.connection_state_changed.emit(state.value)
    
    async def _test_connection(self):
        """Test connection with a lightweight operation."""
        if not self.stub:
            raise RuntimeError("No gRPC stub available")
        
        # Try to list documents as a connection test
        request = ListDocumentsRequest()
        await self.stub.ListDocuments(request, timeout=5.0)
    
    async def _check_connection_health(self):
        """Periodic health check for the connection."""
        if self.connection_state != ConnectionState.CONNECTED:
            return
            
        try:
            await self._test_connection()
        except Exception as e:
            self.logger.warning(f"Connection health check failed: {e}")
            await self._handle_connection_error(e)
    
    async def _handle_connection_error(self, error: Exception):
        """Handle connection errors with retry logic."""
        self.logger.error(f"Connection error: {error}")
        
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self._set_connection_state(ConnectionState.RECONNECTING)
            self.reconnect_attempts += 1
            
            # Exponential backoff
            delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
            self.logger.info(f"Reconnecting in {delay} seconds (attempt {self.reconnect_attempts})")
            
            await asyncio.sleep(delay)
            
            if await self.connect():
                return
        
        self._set_connection_state(ConnectionState.ERROR)
        self.connection_error.emit(str(error))
    
    def _queue_request(self, operation: str, **kwargs):
        """Queue a request for later execution when connection is restored."""
        if self.queue_enabled:
            self.request_queue.append({
                'operation': operation,
                'kwargs': kwargs,
                'timestamp': asyncio.get_event_loop().time()
            })
            self.logger.info(f"Queued operation: {operation}")
    
    async def _process_request_queue(self):
        """Process queued requests after reconnection."""
        self.logger.info(f"Processing {len(self.request_queue)} queued requests")
        
        for request in self.request_queue.copy():
            try:
                operation = request['operation']
                kwargs = request['kwargs']
                
                # Execute the queued operation
                method = getattr(self, operation)
                await method(**kwargs)
                
                self.request_queue.remove(request)
                
            except Exception as e:
                self.logger.error(f"Failed to process queued request {request['operation']}: {e}")
        
    async def _execute_request(self, operation_name: str, request_func, *args, **kwargs):
        """
        Execute a gRPC request with error handling and queuing.
        
        Args:
            operation_name: Name of the operation for logging/queuing
            request_func: The gRPC stub method to call
            *args, **kwargs: Arguments to pass to the request function
        """
        if self.connection_state != ConnectionState.CONNECTED:
            if self.queue_enabled:
                # Queue the request for later execution
                self._queue_request(operation_name, *args, **kwargs)
                return None
            else:
                raise RuntimeError(f"Not connected to server. Cannot execute {operation_name}")
        
        try:
            response = await request_func(*args, **kwargs)
            return response
            
        except grpc.RpcError as e:
            error_msg = f"{operation_name} failed: {e.details()}"
            self.logger.error(error_msg)
            self.error_occurred.emit(operation_name, error_msg)
            
            # Handle connection errors
            if e.code() in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED]:
                await self._handle_connection_error(e)
            
            raise
        
        except Exception as e:
            error_msg = f"{operation_name} failed: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(operation_name, error_msg)
            raise

    # Document Operations
    async def create_document(self, name: str, template_id: Optional[str] = None) -> Optional[dict]:
        """Create a new document."""
        request = CreateDocumentRequest(name=name)
        if template_id:
            request.template_id = template_id
            
        response = await self._execute_request(
            "create_document",
            self.stub.CreateDocument,
            request
        )
        
        if response:
            doc_data = {
                'id': response.document.id,
                'name': response.document.name,
                'created_at': response.document.created_at,
                'modified_at': response.document.modified_at
            }
            self.document_created.emit(doc_data)
            return doc_data
        return None

    async def load_document(self, document_id: str) -> Optional[dict]:
        """Load a document by ID."""
        request = LoadDocumentRequest(document_id=document_id)
        
        response = await self._execute_request(
            "load_document",
            self.stub.LoadDocument,
            request
        )
        
        if response:
            doc_data = {
                'id': response.document.id,
                'name': response.document.name,
                'layers': [self._layer_to_dict(layer) for layer in response.document.layers],
                'entities': [self._entity_to_dict(entity) for entity in response.document.entities]
            }
            self.document_loaded.emit(doc_data)
            return doc_data
        return None

    async def save_document(self, document_id: str, format: str = "native") -> bool:
        """Save a document."""
        request = SaveDocumentRequest(document_id=document_id, format=format)
        
        response = await self._execute_request(
            "save_document",
            self.stub.SaveDocument,
            request
        )
        
        if response and response.success:
            self.document_saved.emit({'id': document_id, 'path': response.file_path})
            return True
        return False

    async def list_documents(self) -> Optional[List[dict]]:
        """List all available documents."""
        request = ListDocumentsRequest()
        
        response = await self._execute_request(
            "list_documents",
            self.stub.ListDocuments,
            request
        )
        
        if response:
            docs = [
                {
                    'id': doc.id,
                    'name': doc.name,
                    'created_at': doc.created_at,
                    'modified_at': doc.modified_at
                }
                for doc in response.documents
            ]
            self.documents_listed.emit(docs)
            return docs
        return None

    # Layer Operations
    async def create_layer(self, document_id: str, name: str, color: str = "white", 
                          line_type: str = "solid", line_weight: float = 1.0) -> Optional[dict]:
        """Create a new layer."""
        request = CreateLayerRequest(
            document_id=document_id,
            name=name,
            color=color,
            line_type=line_type,
            line_weight=line_weight
        )
        
        response = await self._execute_request(
            "create_layer",
            self.stub.CreateLayer,
            request
        )
        
        if response:
            layer_data = self._layer_to_dict(response.layer)
            self.layer_created.emit(layer_data)
            return layer_data
        return None

    async def update_layer(self, layer_id: str, **kwargs) -> Optional[dict]:
        """Update layer properties."""
        request = UpdateLayerRequest(layer_id=layer_id)
        
        # Set optional fields
        for field, value in kwargs.items():
            if hasattr(request, field):
                setattr(request, field, value)
        
        response = await self._execute_request(
            "update_layer",
            self.stub.UpdateLayer,
            request
        )
        
        if response:
            layer_data = self._layer_to_dict(response.layer)
            self.layer_updated.emit(layer_data)
            return layer_data
        return None

    async def delete_layer(self, layer_id: str) -> bool:
        """Delete a layer."""
        request = DeleteLayerRequest(layer_id=layer_id)
        
        response = await self._execute_request(
            "delete_layer",
            self.stub.DeleteLayer,
            request
        )
        
        if response and response.success:
            self.layer_deleted.emit(layer_id)
            return True
        return False

    async def list_layers(self, document_id: str) -> Optional[List[dict]]:
        """List layers in a document."""
        request = ListLayersRequest(document_id=document_id)
        
        response = await self._execute_request(
            "list_layers",
            self.stub.ListLayers,
            request
        )
        
        if response:
            layers = [self._layer_to_dict(layer) for layer in response.layers]
            self.layers_listed.emit(layers)
            return layers
        return None

    async def set_current_layer(self, document_id: str, layer_id: str) -> bool:
        """Set the current active layer."""
        request = SetCurrentLayerRequest(document_id=document_id, layer_id=layer_id)
        
        response = await self._execute_request(
            "set_current_layer",
            self.stub.SetCurrentLayer,
            request
        )
        
        if response and response.success:
            self.current_layer_set.emit(layer_id)
            return True
        return False

    # Entity Operations
    async def create_entity(self, document_id: str, entity_type: str, 
                           geometry_data: dict, layer_id: Optional[str] = None,
                           properties: Optional[Dict[str, str]] = None) -> Optional[dict]:
        """Create a new entity."""
        request = CreateEntityRequest(
            document_id=document_id,
            type=entity_type,
            geometry=self._dict_to_geometry(geometry_data)
        )
        
        if layer_id:
            request.layer_id = layer_id
        if properties:
            request.properties.update(properties)
        
        response = await self._execute_request(
            "create_entity",
            self.stub.CreateEntity,
            request
        )
        
        if response:
            entity_data = self._entity_to_dict(response.entity)
            self.entity_created.emit(entity_data)
            return entity_data
        return None

    async def update_entity(self, entity_id: str, **kwargs) -> Optional[dict]:
        """Update entity properties."""
        request = UpdateEntityRequest(entity_id=entity_id)
        
        # Set optional fields
        for field, value in kwargs.items():
            if field == 'geometry' and isinstance(value, dict):
                request.geometry.CopyFrom(self._dict_to_geometry(value))
            elif field == 'properties' and isinstance(value, dict):
                request.properties.update(value)
            elif hasattr(request, field):
                setattr(request, field, value)
        
        response = await self._execute_request(
            "update_entity",
            self.stub.UpdateEntity,
            request
        )
        
        if response:
            entity_data = self._entity_to_dict(response.entity)
            self.entity_updated.emit(entity_data)
            return entity_data
        return None

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity."""
        request = DeleteEntityRequest(entity_id=entity_id)
        
        response = await self._execute_request(
            "delete_entity",
            self.stub.DeleteEntity,
            request
        )
        
        if response and response.success:
            self.entity_deleted.emit(entity_id)
            return True
        return False

    async def query_entities(self, document_id: str, layer_id: Optional[str] = None,
                            entity_type: Optional[str] = None,
                            bbox: Optional[dict] = None) -> Optional[List[dict]]:
        """Query entities with filters."""
        request = QueryEntitiesRequest(document_id=document_id)
        
        if layer_id:
            request.layer_id = layer_id
        if entity_type:
            request.type = entity_type
        if bbox:
            request.bounding_box.CopyFrom(self._dict_to_bbox(bbox))
        
        entities = []
        async for entity in self.stub.QueryEntities(request):
            entities.append(self._entity_to_dict(entity))
        
        self.entities_queried.emit(entities)
        return entities

    # Drawing Operations (convenience methods)
    async def draw_line(self, document_id: str, start: dict, end: dict,
                       layer_id: Optional[str] = None,
                       properties: Optional[Dict[str, str]] = None) -> Optional[dict]:
        """Draw a line."""
        request = DrawLineRequest(
            document_id=document_id,
            start=Point(x=start['x'], y=start['y'], z=start.get('z', 0.0)),
            end=Point(x=end['x'], y=end['y'], z=end.get('z', 0.0))
        )
        
        if layer_id:
            request.layer_id = layer_id
        if properties:
            request.properties.update(properties)
        
        response = await self._execute_request(
            "draw_line",
            self.stub.DrawLine,
            request
        )
        
        if response:
            entity_data = self._entity_to_dict(response.entity)
            self.line_drawn.emit(entity_data)
            return entity_data
        return None

    async def draw_circle(self, document_id: str, center: dict, radius: float,
                         layer_id: Optional[str] = None,
                         properties: Optional[Dict[str, str]] = None) -> Optional[dict]:
        """Draw a circle."""
        request = DrawCircleRequest(
            document_id=document_id,
            center=Point(x=center['x'], y=center['y'], z=center.get('z', 0.0)),
            radius=radius
        )
        
        if layer_id:
            request.layer_id = layer_id
        if properties:
            request.properties.update(properties)
        
        response = await self._execute_request(
            "draw_circle",
            self.stub.DrawCircle,
            request
        )
        
        if response:
            entity_data = self._entity_to_dict(response.entity)
            self.circle_drawn.emit(entity_data)
            return entity_data
        return None

    async def draw_arc(self, document_id: str, center: dict, radius: float,
                      start_angle: float, end_angle: float,
                      layer_id: Optional[str] = None,
                      properties: Optional[Dict[str, str]] = None) -> Optional[dict]:
        """Draw an arc."""
        request = DrawArcRequest(
            document_id=document_id,
            center=Point(x=center['x'], y=center['y'], z=center.get('z', 0.0)),
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle
        )
        
        if layer_id:
            request.layer_id = layer_id
        if properties:
            request.properties.update(properties)
        
        response = await self._execute_request(
            "draw_arc",
            self.stub.DrawArc,
            request
        )
        
        if response:
            entity_data = self._entity_to_dict(response.entity)
            self.arc_drawn.emit(entity_data)
            return entity_data
        return None

    # Helper methods for data conversion
    def _layer_to_dict(self, layer) -> dict:
        """Convert layer protobuf to dictionary."""
        return {
            'id': layer.id,
            'name': layer.name,
            'color': layer.color,
            'visible': layer.visible,
            'locked': layer.locked,
            'line_type': layer.line_type,
            'line_weight': layer.line_weight
        }

    def _entity_to_dict(self, entity) -> dict:
        """Convert entity protobuf to dictionary."""
        return {
            'id': entity.id,
            'type': entity.type,
            'layer_id': entity.layer_id,
            'properties': dict(entity.properties),
            'geometry': self._geometry_to_dict(entity.geometry)
        }

    def _geometry_to_dict(self, geometry) -> dict:
        """Convert geometry protobuf to dictionary."""
        geometry_type = geometry.WhichOneof('geometry_type')
        result = {'type': geometry_type}
        
        if geometry_type == 'point':
            result['data'] = {
                'x': geometry.point.x,
                'y': geometry.point.y,
                'z': geometry.point.z
            }
        elif geometry_type == 'line':
            result['data'] = {
                'start': {
                    'x': geometry.line.start.x,
                    'y': geometry.line.start.y,
                    'z': geometry.line.start.z
                },
                'end': {
                    'x': geometry.line.end.x,
                    'y': geometry.line.end.y,
                    'z': geometry.line.end.z
                }
            }
        elif geometry_type == 'circle':
            result['data'] = {
                'center': {
                    'x': geometry.circle.center.x,
                    'y': geometry.circle.center.y,
                    'z': geometry.circle.center.z
                },
                'radius': geometry.circle.radius
            }
        elif geometry_type == 'arc':
            result['data'] = {
                'center': {
                    'x': geometry.arc.center.x,
                    'y': geometry.arc.center.y,
                    'z': geometry.arc.center.z
                },
                'radius': geometry.arc.radius,
                'start_angle': geometry.arc.start_angle,
                'end_angle': geometry.arc.end_angle
            }
        
        return result

    def _dict_to_geometry(self, data: dict):
        """Convert dictionary to geometry protobuf."""
        from geometry_pb2 import Geometry, Point, Line, Circle, Arc
        
        geometry = Geometry()
        geometry_type = data.get('type')
        
        if geometry_type == 'point':
            point_data = data['data']
            geometry.point.CopyFrom(Point(
                x=point_data['x'],
                y=point_data['y'],
                z=point_data.get('z', 0.0)
            ))
        elif geometry_type == 'line':
            line_data = data['data']
            geometry.line.CopyFrom(Line(
                start=Point(
                    x=line_data['start']['x'],
                    y=line_data['start']['y'],
                    z=line_data['start'].get('z', 0.0)
                ),
                end=Point(
                    x=line_data['end']['x'],
                    y=line_data['end']['y'],
                    z=line_data['end'].get('z', 0.0)
                )
            ))
        elif geometry_type == 'circle':
            circle_data = data['data']
            geometry.circle.CopyFrom(Circle(
                center=Point(
                    x=circle_data['center']['x'],
                    y=circle_data['center']['y'],
                    z=circle_data['center'].get('z', 0.0)
                ),
                radius=circle_data['radius']
            ))
        elif geometry_type == 'arc':
            arc_data = data['data']
            geometry.arc.CopyFrom(Arc(
                center=Point(
                    x=arc_data['center']['x'],
                    y=arc_data['center']['y'],
                    z=arc_data['center'].get('z', 0.0)
                ),
                radius=arc_data['radius'],
                start_angle=arc_data['start_angle'],
                end_angle=arc_data['end_angle']
            ))
        
        return geometry

    def _dict_to_bbox(self, bbox: dict):
        """Convert dictionary to bounding box protobuf."""
        from geometry_pb2 import BoundingBox, Point
        
        return BoundingBox(
            min_point=Point(
                x=bbox['min']['x'],
                y=bbox['min']['y'],
                z=bbox['min'].get('z', 0.0)
            ),
            max_point=Point(
                x=bbox['max']['x'],
                y=bbox['max']['y'],
                z=bbox['max'].get('z', 0.0)
            )
        )


class APIClientThread(QThread):
    """
    Qt thread wrapper for running async gRPC operations.
    
    This thread runs an asyncio event loop to handle async gRPC calls
    without blocking the Qt main thread.
    """
    
    def __init__(self, client: CADAPIClient, parent=None):
        super().__init__(parent)
        self.client = client
        self.loop = None
        self.should_stop = False
        
    def run(self):
        """Run the asyncio event loop in this thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._run_client())
        finally:
            self.loop.close()
    
    async def _run_client(self):
        """Main client execution loop."""
        # Connect to server
        await self.client.connect()
        
        # Keep the loop running until stop is requested
        while not self.should_stop:
            await asyncio.sleep(0.1)
        
        # Cleanup
        await self.client.disconnect()
    
    def stop(self):
        """Stop the client thread."""
        self.should_stop = True
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


class APIClientManager(QObject):
    """
    Manager class to simplify API client setup and usage.
    
    This class handles the thread management and provides a simpler
    interface for Qt applications to use the gRPC client.
    """
    
    # Forward signals from the client
    connection_state_changed = Signal(str)
    connection_error = Signal(str)
    
    # Document signals
    document_created = Signal(dict)
    document_loaded = Signal(dict)
    document_saved = Signal(dict)
    documents_listed = Signal(list)
    
    # Layer signals
    layer_created = Signal(dict)
    layers_listed = Signal(list)
    
    # Entity signals
    entity_created = Signal(dict)
    entities_queried = Signal(list)
    
    # Drawing signals
    line_drawn = Signal(dict)
    circle_drawn = Signal(dict)
    arc_drawn = Signal(dict)
    
    def __init__(self, server_address: str = "localhost:50051", parent=None):
        """Initialize the API client manager."""
        super().__init__(parent)
        
        # Create client and thread
        self.client = CADAPIClient(server_address, self)
        self.thread = APIClientThread(self.client, self)
        
        # Connect signals
        self._connect_signals()
        
        # Start the thread
        self.thread.start()
    
    def _connect_signals(self):
        """Connect client signals to manager signals."""
        # Connection signals
        self.client.connection_state_changed.connect(self.connection_state_changed)
        self.client.connection_error.connect(self.connection_error)
        
        # Document signals
        self.client.document_created.connect(self.document_created)
        self.client.document_loaded.connect(self.document_loaded)
        self.client.document_saved.connect(self.document_saved)
        self.client.documents_listed.connect(self.documents_listed)
        
        # Layer signals
        self.client.layer_created.connect(self.layer_created)
        self.client.layers_listed.connect(self.layers_listed)
        
        # Entity signals
        self.client.entity_created.connect(self.entity_created)
        self.client.entities_queried.connect(self.entities_queried)
        
        # Drawing signals
        self.client.line_drawn.connect(self.line_drawn)
        self.client.circle_drawn.connect(self.circle_drawn)
        self.client.arc_drawn.connect(self.arc_drawn)
    
    def execute_async(self, coro):
        """
        Execute an async coroutine in the client thread.
        
        Args:
            coro: Coroutine to execute
        """
        if self.thread.loop:
            asyncio.run_coroutine_threadsafe(coro, self.thread.loop)
    
    # Convenience methods that delegate to the client
    def create_document(self, name: str, template_id: Optional[str] = None):
        """Create a new document (non-blocking)."""
        self.execute_async(self.client.create_document(name, template_id))
    
    def load_document(self, document_id: str):
        """Load a document (non-blocking)."""
        self.execute_async(self.client.load_document(document_id))
    
    def save_document(self, document_id: str, format: str = "native"):
        """Save a document (non-blocking)."""
        self.execute_async(self.client.save_document(document_id, format))
    
    def list_documents(self):
        """List documents (non-blocking)."""
        self.execute_async(self.client.list_documents())
    
    def create_layer(self, document_id: str, name: str, **kwargs):
        """Create a layer (non-blocking)."""
        self.execute_async(self.client.create_layer(document_id, name, **kwargs))
    
    def list_layers(self, document_id: str):
        """List layers (non-blocking)."""
        self.execute_async(self.client.list_layers(document_id))
    
    def draw_line(self, document_id: str, start: dict, end: dict, **kwargs):
        """Draw a line (non-blocking)."""
        self.execute_async(self.client.draw_line(document_id, start, end, **kwargs))
    
    def draw_circle(self, document_id: str, center: dict, radius: float, **kwargs):
        """Draw a circle (non-blocking)."""
        self.execute_async(self.client.draw_circle(document_id, center, radius, **kwargs))
    
    def draw_arc(self, document_id: str, center: dict, radius: float, 
                start_angle: float, end_angle: float, **kwargs):
        """Draw an arc (non-blocking)."""
        self.execute_async(self.client.draw_arc(
            document_id, center, radius, start_angle, end_angle, **kwargs
        ))
    
    def query_entities(self, document_id: str, **kwargs):
        """Query entities (non-blocking)."""
        self.execute_async(self.client.query_entities(document_id, **kwargs))
    
    def shutdown(self):
        """Shutdown the client and thread."""
        self.thread.stop()
        self.thread.wait()  # Wait for thread to finish