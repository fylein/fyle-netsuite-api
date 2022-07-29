from .base import Base


class Employees(Base):
    """Class for Employees APIs."""

    def __init__(self):
        Base.__init__(self, attribute_type='EMPLOYEE', query_params={'is_enabled': 'eq.true', 'has_accepted_invite': 'eq.true'})

    def sync(self):
        """
        Syncs the latest API data to DB.
        """
        generator = self.get_all_generator()
        for items in generator:
            employee_attributes = []
            for employee in items['data']:
                employee_attributes.append({
                    'attribute_type': self.attribute_type,
                    'display_name': self.attribute_type.replace('_', ' ').title(),
                    'value': employee['user']['email'],
                    'source_id': employee['id'],
                    'detail': {
                        'user_id': employee['user_id'],
                        'employee_code': employee['code'],
                        'full_name': employee['user']['full_name'],
                        'location': employee['location'],
                        'department': employee['department']['name'] if employee['department'] else None,
                        'department_id': employee['department_id'],
                        'department_code': employee['department']['code'] if employee['department'] else None
                    }
                })

            self.bulk_create_or_update_expense_attributes(employee_attributes, True)
