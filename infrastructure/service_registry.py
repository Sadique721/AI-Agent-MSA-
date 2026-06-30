import logging
from typing import Dict, Type, Any, Optional

logger = logging.getLogger("msa.infrastructure.registry")

class BaseService:
    """Base class for all system-level services of MSA Operating System."""
    def __init__(self):
        self.is_running = False

    def start(self) -> None:
        """Starts the service."""
        if not self.is_running:
            logger.info("Starting service: %s", self.__class__.__name__)
            self.is_running = True

    def stop(self) -> None:
        """Stops the service."""
        if self.is_running:
            logger.info("Stopping service: %s", self.__class__.__name__)
            self.is_running = False

    def get_health(self) -> Dict[str, Any]:
        """Returns health status metrics."""
        return {
            "name": self.__class__.__name__,
            "status": "healthy" if self.is_running else "stopped",
            "is_running": self.is_running
        }

class ServiceRegistry:
    """System-wide thread-safe service registry."""
    _instance: Optional['ServiceRegistry'] = None

    def __new__(cls) -> 'ServiceRegistry':
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
            cls._instance._services = {}
        return cls._instance

    def register(self, name: str, service: BaseService) -> None:
        """Registers a service instance."""
        logger.info("Registering service: %s", name)
        self._services[name] = service

    def get(self, name: str) -> Optional[BaseService]:
        """Retrieves a registered service instance."""
        return self._services.get(name)

    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """Lists status details of all registered services."""
        return {
            name: service.get_health() for name, service in self._services.items()
        }

    def shutdown_all(self) -> None:
        """Safely shuts down all registered services."""
        logger.info("Shutting down all registry services...")
        for name, service in list(self._services.items()):
            try:
                service.stop()
            except Exception as e:
                logger.error("Failed to stop service %s: %s", name, e)
        self._services.clear()
