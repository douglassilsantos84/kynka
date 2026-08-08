"""
Contexto de execução da plataforma Kynka.
"""

from .agent_context import (
    AgentContext,
    ContextVariableNotFoundError,
)

from .context_command import (
    ContextCommandError,
    ContextCommandHandler,
    ContextCommandResult,
)

from .context_resolver import (
    ContextResolution,
    ContextResolutionError,
    ContextResolver,
)

from .variable_resolver import (
    VariableResolution,
    VariableResolutionError,
    VariableResolver,
)


__all__ = [
    "AgentContext",
    "ContextVariableNotFoundError",
    "ContextCommandError",
    "ContextCommandHandler",
    "ContextCommandResult",
    "ContextResolution",
    "ContextResolutionError",
    "ContextResolver",
    "VariableResolution",
    "VariableResolutionError",
    "VariableResolver",
]