import pytest
from django_q.models import Schedule
from apps.workspaces.models import Workspace
from apps.mappings.models import GeneralMapping

from fyle_accounting_mappings.models import MappingSetting

@pytest.mark.django_db()
def test_run_post_mapping_settings_triggers(test_connection):
    mapping_setting = MappingSetting(
        source_field='PROJECT',
        destination_field='PROJECT',
        workspace_id=1,
        import_to_fyle=True,
        is_custom=False
    )

    mapping_setting.save()
    schedule = Schedule.objects.first()

    assert schedule.func == 'apps.mappings.tasks.auto_create_project_mappings'
    assert schedule.args == '1'

    mapping_setting = MappingSetting(
        source_field='COST_CENTER',
        destination_field='TAX_ITEM',
        workspace_id=1,
        import_to_fyle=True,
        is_custom=False
    )

    mapping_setting.save()

    schedule = Schedule.objects.last()
    assert schedule.func == 'apps.mappings.tasks.auto_create_cost_center_mappings'
    assert schedule.args == '1'


def test_run_post_general_mapping_triggers(test_connection, create_configuration):

    workspace = Workspace.objects.filter(id=1).first()

    general_mapping = GeneralMapping(
        id=1,
        location_name='01: San Francisco',
        location_level='ALL',
        location_id=2,
        accounts_payable_name='Accounts Payable',
        accounts_payable_id=25,
        reimbursable_account_id=25,
        reimbursable_account_name='Accounts Payable',
        use_employee_department=False,
        use_employee_location=False,
        use_employee_class=False,
        default_ccc_vendor_id=3381,
        default_ccc_vendor_name='Allison Hill',
        default_ccc_account_name='Nilesh',
        workspace=workspace
    )

    general_mapping.save()

    schedule = Schedule.objects.last()
    
    assert schedule.func == 'apps.mappings.tasks.async_auto_map_ccc_account'
    assert schedule.args == '1'
