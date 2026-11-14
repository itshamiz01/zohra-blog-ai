"""
Zohra — Agent registry.

Future agents register themselves here so the orchestrator
can discover and invoke them by name.
"""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__, component="agent_registry")

_registry: dict[str, type[BaseAgent]] = {}


def register_agent(agent_class: type[BaseAgent]) -> type[BaseAgent]:
    """Register an agent class. Can be used as a decorator."""
    name = agent_class.name
    if name in _registry:
        logger.warning("Agent '%s' is being re-registered — overwriting", name)
    _registry[name] = agent_class
    logger.info("Registered agent: %s v%s", name, agent_class.version)
    return agent_class


def get_agent(name: str) -> BaseAgent:
    """Instantiate a registered agent by name."""
    if name not in _registry:
        raise KeyError(f"No agent registered with name '{name}'")
    return _registry[name]()


def list_agents() -> list[dict[str, str]]:
    """List all registered agents."""
    return [{"name": cls.name, "version": cls.version} for cls in _registry.values()]
