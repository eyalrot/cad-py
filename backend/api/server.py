"""gRPC server setup and configuration."""

import asyncio
import logging
import signal
import sys
from concurrent import futures
from typing import Optional

import grpc
from grpc_reflection.v1alpha import reflection

from .cad_grpc_service import CADGrpcService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CADGrpcServer:
    """CAD gRPC Server implementation."""
    
    def __init__(self, port: int = 50051, max_workers: int = 10):
        """Initialize the gRPC server.
        
        Args:
            port: Port to bind the server to
            max_workers: Maximum number of worker threads
        """
        self.port = port
        self.max_workers = max_workers
        self.server: Optional[grpc.Server] = None
        self.cad_service = CADGrpcService()
        
    def create_server(self) -> grpc.Server:
        """Create and configure the gRPC server."""
        # Create server with thread pool
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=self.max_workers),
            options=[
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 5000)
            ]
        )
        
        # Add the CAD service to the server
        # Note: In real implementation, would use generated servicer:
        # cad_service_pb2_grpc.add_CADServiceServicer_to_server(self.cad_service, server)
        
        # Add reflection service for development
        service_names = [
            'cad.service.CADService',
            reflection.SERVICE_NAME,
        ]
        reflection.enable_server_reflection(service_names, server)
        
        # Bind to port
        listen_addr = f'[::]:{self.port}'
        server.add_insecure_port(listen_addr)
        
        logger.info(f"gRPC server configured on {listen_addr}")
        return server
    
    def start(self) -> None:
        """Start the gRPC server."""
        try:
            self.server = self.create_server()
            self.server.start()
            logger.info(f"CAD gRPC server started on port {self.port}")
            
            # Health check
            health_status = self.cad_service.health_check()
            logger.info(f"Service health: {health_status}")
            
            # Service info
            service_info = self.cad_service.get_service_info()
            logger.info(f"Service info: {service_info}")
            
        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}")
            raise
    
    def stop(self, grace_period: int = 30) -> None:
        """Stop the gRPC server.
        
        Args:
            grace_period: Grace period in seconds for graceful shutdown
        """
        if self.server:
            logger.info("Stopping CAD gRPC server...")
            self.server.stop(grace_period)
            logger.info("CAD gRPC server stopped")
    
    def wait_for_termination(self) -> None:
        """Wait for server termination."""
        if self.server:
            try:
                self.server.wait_for_termination()
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                self.stop()


def setup_signal_handlers(server: CADGrpcServer) -> None:
    """Setup signal handlers for graceful shutdown."""
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def run_server(port: int = 50051, max_workers: int = 10) -> None:
    """Run the CAD gRPC server.
    
    Args:
        port: Port to bind the server to
        max_workers: Maximum number of worker threads
    """
    server = CADGrpcServer(port=port, max_workers=max_workers)
    
    # Setup signal handlers
    setup_signal_handlers(server)
    
    try:
        # Start server
        server.start()
        
        # Wait for termination
        server.wait_for_termination()
        
    except Exception as e:
        logger.error(f"Server error: {e}")
        server.stop()
        raise


async def run_async_server(port: int = 50051, max_workers: int = 10) -> None:
    """Run the CAD gRPC server asynchronously.
    
    Args:
        port: Port to bind the server to
        max_workers: Maximum number of worker threads
    """
    server = CADGrpcServer(port=port, max_workers=max_workers)
    
    try:
        # Start server
        server.start()
        
        logger.info("Server running asynchronously. Press Ctrl+C to stop.")
        
        # Keep the server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
    finally:
        server.stop()


if __name__ == "__main__":
    """Main entry point for running the server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CAD gRPC Server")
    parser.add_argument(
        "--port", 
        type=int, 
        default=50051, 
        help="Port to bind the server to (default: 50051)"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=10, 
        help="Maximum number of worker threads (default: 10)"
    )
    parser.add_argument(
        "--async-mode", 
        action="store_true", 
        help="Run server asynchronously"
    )
    
    args = parser.parse_args()
    
    if getattr(args, 'async-mode', False):
        asyncio.run(run_async_server(port=args.port, max_workers=args.workers))
    else:
        run_server(port=args.port, max_workers=args.workers)