from .base import Base


class Projects(Base):
    """Class for Projects APIs."""

    def __init__(self):
        Base.__init__(self, attribute_type='PROJECT', query_params={'is_enabled': 'eq.true'})


    def sync(self):
        """
        Syncs the latest API data to DB.
        """
        generator = self.get_all_generator()
        for items in generator:
            project_attributes = []
            for project in items['data']:
                if project['sub_project']:
                    project['name'] = '{0} / {1}'.format(project['name'], project['sub_project'])

                project_attributes.append({
                    'attribute_type': self.attribute_type,
                    'display_name': self.attribute_type.replace('_', ' ').title(),
                    'value': project['name'],
                    'source_id': project['id']
                })

            self.bulk_create_or_update_expense_attributes(project_attributes)
