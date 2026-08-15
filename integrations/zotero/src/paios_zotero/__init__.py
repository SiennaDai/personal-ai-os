"""Personal AI-OS Zotero Integration."""

from .config import ZoteroConfig, load_config
from .errors import IntegrationError
from .service import ZoteroService

__all__ = ["IntegrationError", "ZoteroConfig", "ZoteroService", "load_config"]
__version__ = "1.0.0"
