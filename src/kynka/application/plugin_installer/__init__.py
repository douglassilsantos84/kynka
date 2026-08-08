"""
API pública de instalação de Plugins da Kynka.
"""

from .plugin_installer import (
    PluginInstallationError,
    PluginInstaller,
)

__all__ = [
    "PluginInstallationError",
    "PluginInstaller",
]