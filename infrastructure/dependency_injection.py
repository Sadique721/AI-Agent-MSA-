import inspect
import logging
from typing import Dict, Any, Type, Callable, Optional

logger = logging.getLogger("msa.infrastructure.di")

class Container:
    """Thread-safe Dependency Injection container."""
    _instance: Optional['Container'] = None

    def __new__(cls) -> 'Container':
        if cls._instance is None:
            cls._instance = super(Container, cls).__new__(cls)
            cls._instance._bindings = {}
            cls._instance._instances = {}
        return cls._instance

    def register_singleton(self, interface: Type, implementation: Type) -> None:
        """Registers a singleton service binding."""
        logger.debug("DI Binding singleton: %s -> %s", interface.__name__, implementation.__name__)
        self._bindings[interface] = ("singleton", implementation)

    def register_instance(self, interface: Type, instance: Any) -> None:
        """Registers a pre-instantiated singleton instance."""
        logger.debug("DI Binding instance: %s", interface.__name__)
        self._bindings[interface] = ("singleton", instance.__class__)
        self._instances[interface] = instance

    def register_transient(self, interface: Type, implementation: Type) -> None:
        """Registers a transient service binding (instantiated per request)."""
        logger.debug("DI Binding transient: %s -> %s", interface.__name__, implementation.__name__)
        self._bindings[interface] = ("transient", implementation)

    def resolve(self, interface: Type) -> Any:
        """Resolves dependencies and constructs instance recursively."""
        if interface in self._instances:
            return self._instances[interface]

        if interface not in self._bindings:
            # Fallback to direct instantiation if it is a concrete class
            return self._construct(interface)

        lifecycle, impl_class = self._bindings[interface]

        if lifecycle == "singleton":
            instance = self._construct(impl_class)
            self._instances[interface] = instance
            return instance
        else:
            return self._construct(impl_class)

    def _construct(self, impl_class: Type) -> Any:
        """Extracts parameters from constructor and resolves them recursively."""
        if impl_class.__init__ is object.__init__:
            return impl_class()

        try:
            signature = inspect.signature(impl_class.__init__)
        except (ValueError, TypeError):
            # No __init__ defined or built-in class
            return impl_class()

        args = {}
        for name, param in signature.parameters.items():
            if name == "self":
                continue
            if param.annotation != inspect.Parameter.empty:
                # Recursively resolve annotation type
                args[name] = self.resolve(param.annotation)
            else:
                # No type annotation, skip or use default if available
                if param.default != inspect.Parameter.empty:
                    args[name] = param.default
                else:
                    raise ValueError(f"Cannot resolve parameter '{name}' of {impl_class.__name__}: missing type hint")

        return impl_class(**args)

    def clear(self) -> None:
        """Clears all bindings and instances."""
        self._bindings.clear()
        self._instances.clear()
