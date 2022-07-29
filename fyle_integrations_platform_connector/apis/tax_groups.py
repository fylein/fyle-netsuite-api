from .base import Base

class TaxGroups(Base):
    """
    Class for Tax Groups API
    """

    def __init__(self):
        Base.__init__(self, attribute_type='TAX_GROUP', query_params={'order': 'id.asc'})

    def sync(self):
        """
        Syncs the latest API data to DB.
        """
        generator = self.get_all_generator()
        for items in generator:
            tax_attributes = []
            for tax_group in items['data']:
                    tax_attributes.append({
                        'attribute_type': 'TAX_GROUP',
                        'display_name': 'Tax Group',
                        'value': tax_group['name'],
                        'source_id': tax_group['id'],
                        'detail': {
                            'tax_rate': tax_group['percentage']
                        }
                    })

            self.bulk_create_or_update_expense_attributes(tax_attributes, True)
