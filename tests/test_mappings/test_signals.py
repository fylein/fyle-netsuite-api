import pytest
from django_q.models import Schedule
from apps.workspaces.models import Configuration, Workspace
from apps.mappings.models import GeneralMapping
from apps.tasks.models import Error
from fyle_accounting_mappings.models import MappingSetting, ExpenseAttribute, EmployeeMapping


@pytest.mark.django_db()
def test_resolve_post_employees_mapping_errors(access_token):
    source_employee = ExpenseAttribute.objects.filter(
        value='approver1@fyleforgotham.in',
        workspace_id=1,
        attribute_type='EMPLOYEE'
    ).first()

    Error.objects.update_or_create(
        workspace_id=1,
        expense_attribute=source_employee,
        defaults={
            'type': 'EMPLOYEE_MAPPING',
            'error_title': source_employee.value,
            'error_detail': 'Employee mapping is missing',
            'is_resolved': False
        }
    )
    employee_mapping, _ = EmployeeMapping.objects.update_or_create(
       source_employee_id=1,
       destination_employee_id=719,
       workspace_id=1
    )

    error = Error.objects.filter(expense_attribute_id=employee_mapping.source_employee_id).first()

    assert error.is_resolved == True

@pytest.mark.django_db()
def test_run_post_mapping_settings_triggers(access_token):
    mapping_setting = MappingSetting(
        source_field='PROJECT',
        destination_field='PROJECT',
        workspace_id=2,
        import_to_fyle=True,
        is_custom=False
    )

    mapping_setting.save()

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_import_and_map_fyle_fields',
        args='{}'.format(2),
    ).first()

    assert schedule.func == 'apps.mappings.tasks.auto_import_and_map_fyle_fields'
    assert schedule.args == '2'

    mapping_setting = MappingSetting(
        source_field='COST_CENTER',
        destination_field='CLASS',
        workspace_id=1,
        import_to_fyle=True,
        is_custom=False
    )

    mapping_setting.save()

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.auto_create_cost_center_mappings',
        args='{}'.format(1),
    ).first()

    assert schedule.func == 'apps.mappings.tasks.auto_create_cost_center_mappings'
    assert schedule.args == '1'


def test_run_post_general_mapping_triggers(db, access_token):

    workspace = Workspace.objects.filter(id=1).first()

    configuration = Configuration.objects.get(workspace_id=1)
    configuration.auto_map_employees = 'NAME'
    configuration.save()

    general_mapping = GeneralMapping.objects.get(workspace_id=1)
    general_mapping.default_ccc_account_name = 'Accounts Payable'
    general_mapping.save()

    schedule = Schedule.objects.filter(
        func='apps.mappings.tasks.async_auto_map_ccc_account',
        args='{}'.format(1),
    ).first()
    
    assert schedule.func == 'apps.mappings.tasks.async_auto_map_ccc_account'
    assert schedule.args == '1'
