"""
Plugins do domínio da plataforma Kynka.
"""

from kynka.domain.plugins.hello_plugin import HelloPlugin
from kynka.domain.plugins.plugin import Plugin, PluginMetadata

__all__ = [
    "HelloPlugin",
    "Plugin",
    "PluginMetadata",
]