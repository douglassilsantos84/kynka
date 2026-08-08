"""
API pública das Tasks da plataforma Kynka.
"""

from .task import Task
from .task_result import TaskResult

__all__ = [
    "Task",
    "TaskResult",
]