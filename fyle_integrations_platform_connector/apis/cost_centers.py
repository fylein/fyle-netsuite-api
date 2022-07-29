from .base import Base


class CostCenters(Base):
    """Class for Cost Centers APIs."""

    def __init__(self):
        Base.__init__(self, attribute_type='COST_CENTER', query_params={'is_enabled': 'eq.true'})
