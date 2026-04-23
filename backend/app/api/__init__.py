from .data import router as data_router
from .analysis import router as analysis_router
from .monitor import router as monitor_router
from .spc import router as spc_router
from .settings import router as settings_router

__all__ = ["data_router", "analysis_router", "monitor_router", "spc_router", "settings_router"]