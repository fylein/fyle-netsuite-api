from typing import Dict

from fyle_netsuite_api.utils import assert_valid

from .models import EmployeeMapping, CategoryMapping, CostCenterMapping, ProjectMapping


class MappingUtils:
    def __init__(self, workspace_id):
        self.__workspace_id = workspace_id

    def create_or_update_employee_mapping(self, employee_mapping: Dict):
        """
        Create or update employee mappings
        :param employee_mapping: employee mapping payload
        :return: employee mappings objects
        """
        assert_valid('employee_email' in employee_mapping and employee_mapping['employee_email'],
                     'employee email field is blank')
        assert_valid('vendor_name' in employee_mapping and employee_mapping['vendor_name'],
                     'vendor name field is blank')
        assert_valid('vendor_id' in employee_mapping and employee_mapping['vendor_id'],
                     'vendor id field is blank')

        employee_mapping_object, _ = EmployeeMapping.objects.update_or_create(
            employee_email=employee_mapping['employee_email'].lower(),
            workspace_id=self.__workspace_id,
            defaults={
                'vendor_name': employee_mapping['vendor_name'],
                'vendor_id': employee_mapping['vendor_id']
            }
        )

        return employee_mapping_object

    def create_or_update_category_mapping(self, category_mapping: Dict):
        """
        Create or update category mappings
        :param category_mapping: category mapping payload
        :return: category mappings objects
        """
        assert_valid('category' in category_mapping and category_mapping['category'],
                     'category field is blank')
        assert_valid('sub_category' in category_mapping and category_mapping['sub_category'],
                     'sub_category field is blank')
        assert_valid('account_name' in category_mapping and category_mapping['account_name'],
                     'account name field is blank')
        assert_valid('account_id' in category_mapping and category_mapping['account_id'],
                     'account id field is blank')

        category_mapping_object, _ = CategoryMapping.objects.update_or_create(
            category=category_mapping['category'],
            sub_category=category_mapping['sub_category'],
            workspace_id=self.__workspace_id,
            defaults={
                'account_name': category_mapping['account_name'],
                'account_id': category_mapping['account_id']
            }
        )

        return category_mapping_object

    def create_or_update_cost_center_mapping(self, cost_center_mapping: Dict):
        """
        Create or update cost_center mappings
        :param cost_center_mapping: cost_center mapping payload
        :return: cost_center mappings objects
        """
        assert_valid('cost_center' in cost_center_mapping and cost_center_mapping['cost_center'],
                     'cost_center field is blank')
        assert_valid('location_name' in cost_center_mapping and cost_center_mapping['location_name'],
                     'location name field is blank')
        assert_valid('location_id' in cost_center_mapping and cost_center_mapping['location_id'],
                     'location id field is blank')

        cost_center_mapping_object, _ = CostCenterMapping.objects.update_or_create(
            cost_center=cost_center_mapping['cost_center'],
            workspace_id=self.__workspace_id,
            defaults={
                'location_name': cost_center_mapping['location_name'],
                'location_id': cost_center_mapping['location_id']
            }
        )

        return cost_center_mapping_object

    def create_or_update_project_mapping(self, project_mapping: Dict):
        """
        Create or update project mappings
        :param project_mapping: project mapping payload
        :return: project mappings objects
        """
        assert_valid('project' in project_mapping and project_mapping['project'],
                     'project field is blank')
        assert_valid('department_name' in project_mapping and project_mapping['department_name'],
                     'department name field is blank')
        assert_valid('department_id' in project_mapping and project_mapping['department_id'],
                     'department id field is blank')

        project_mapping_object, _ = ProjectMapping.objects.update_or_create(
            project=project_mapping['project'],
            workspace_id=self.__workspace_id,
            defaults={
                'department_name': project_mapping['department_name'],
                'department_id': project_mapping['department_id']
            }
        )

        return project_mapping_object
