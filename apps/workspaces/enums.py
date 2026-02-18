from enum import Enum


class CacheKeyEnum(str, Enum):
    """
    Cache key enum
    """
    FYLE_SYNC_DIMENSIONS = "sync_dimensions_{workspace_id}"
    NETSUITE_SYNC_DIMENSIONS = "sync_netsuite_dimensions_{workspace_id}"
    FEATURE_CONFIG_SKIP_POSTING_GROSS_AMOUNT = "skip_posting_gross_amount_{workspace_id}"
