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

    assert schedule.func == 'apps.mappings.tasks.auto_create_tax_group_mappings'
    assert schedule.args == '2'

    mapping_setting = MappingSetting(
        source_field='COST_CENTER',
        destination_field='CLASS',
        workspace_id=1,
        import_to_fyle=True,
        is_custom=False
    )

    mapping_setting.save()

    schedule = Schedule.objects.first()
    assert schedule.func == 'apps.mappings.tasks.auto_create_tax_group_mappings'
    assert schedule.args == '2'


def test_run_post_general_mapping_triggers(test_connection):

    workspace = Workspace.objects.filter(id=1).first()

    general_mapping = GeneralMapping.objects.get(id=1)
    general_mapping.default_ccc_account_name = 'Accounts Payable'
    general_mapping.save()
    schedule = Schedule.objects.first()
    
    assert schedule.func == 'apps.mappings.tasks.auto_create_tax_group_mappings'
    assert schedule.args == '2'
