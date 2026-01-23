from enum import Enum


class CacheKeyEnum(str, Enum):
    """
    Cache key enum
    """
    FYLE_SYNC_DIMENSIONS = "sync_dimensions_{workspace_id}"
    NETSUITE_SYNC_DIMENSIONS = "sync_netsuite_dimensions_{workspace_id}"
