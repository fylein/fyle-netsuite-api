import pytest
from django_q.models import Schedule
from apps.workspaces.models import Configuration, Workspace
from apps.mappings.models import GeneralMapping
from apps.tasks.models import Error
from fyle_accounting_mappings.models import MappingSetting, ExpenseAttribute, EmployeeMapping, CategoryMapping, Mapping

def test_pre_save_category_mappings(access_token):

    category_mapping, _ = CategoryMapping.objects.update_or_create(
       source_category_id=106,
       destination_expense_head_id=20,
       workspace_id=1
    )

    assert category_mapping.destination_expense_head_id == 20
    assert category_mapping.destination_account_id == 419

    category_mapping.destination_expense_head_id = None
    category_mapping.save()

    category_mapping, _ = CategoryMapping.objects.update_or_create(
        source_category_id=106,
        destination_account_id=419,
        workspace_id=1
    )

    assert category_mapping.destination_account_id == 419
    assert category_mapping.destination_expense_head_id == None

def test_resolve_post_mapping_errors(access_token):
    tax_group = ExpenseAttribute.objects.filter(
        value='GST: NCF-AU @0.0%',
        workspace_id=1,
        attribute_type='TAX_GROUP'
    ).first()

    Error.objects.update_or_create(
        workspace_id=1,
        expense_attribute=tax_group,
        defaults={
            'type': 'TAX_GROUP_MAPPING',
            'error_title': tax_group.value,
            'error_detail': 'Tax group mapping is missing',
            'is_resolved': False
        }
    )

    mapping = Mapping(
        source_type='TAX_GROUP',
        destination_type='TAX_DETAIL',
        # source__value=source_value,
        source_id=1642,
        destination_id=1019,
        workspace_id=1
    )
    mapping.save()
    error = Error.objects.filter(expense_attribute_id=mapping.source_id).first()

    assert error.is_resolved == True

@pytest.mark.django_db()
def test_resolve_post_category_mapping_errors(access_token):
    source_category = ExpenseAttribute.objects.filter(
        id=96,
        workspace_id=1,
        attribute_type='CATEGORY'
    ).first()

    Error.objects.update_or_create(
        workspace_id=1,
        expense_attribute=source_category,
        defaults={
            'type': 'CATEGORY_MAPPING',
            'error_title': source_category.value,
            'error_detail': 'Category mapping is missing',
            'is_resolved': False
        }
    )
    category_mapping, _ = CategoryMapping.objects.update_or_create(
       source_category_id=96,
       destination_account_id=791,
       destination_expense_head_id=791,
       workspace_id=1
    )

    error = Error.objects.filter(expense_attribute_id=category_mapping.source_category_id).first()
    assert error.is_resolved == True

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
        func='apps.mappings.queue.construct_tasks_and_chain_import_fields_to_fyle',
        args='{}'.format(2),
    ).first()

    assert schedule.func == 'apps.mappings.queue.construct_tasks_and_chain_import_fields_to_fyle'
    assert schedule.args == '2'

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


@pytest.mark.django_db()
def test_patch_integration_settings_on_card_mapping(db, mocker):
    """
    Test patch_corporate_card_integration_settings is called when corporate card mapping is created
    """
    workspace_id = 1

    # Create required ExpenseAttribute for CORPORATE_CARD mapping
    corporate_card = ExpenseAttribute.objects.create(
        workspace_id=workspace_id,
        attribute_type='CORPORATE_CARD',
        source_id='card_7775',
        value='Test Card - 1234',
        active=True
    )

    # Create required ExpenseAttribute for CATEGORY mapping
    category = ExpenseAttribute.objects.create(
        workspace_id=workspace_id,
        attribute_type='CATEGORY',
        source_id='cat_5322',
        value='Test Category',
        active=True
    )

    mock_patch = mocker.patch('apps.mappings.signals.patch_corporate_card_integration_settings')
    mapping = Mapping(source_type='CORPORATE_CARD', destination_type='CREDIT_CARD_ACCOUNT',
                     source_id=corporate_card.id, destination_id=123, workspace_id=workspace_id)
    mapping.save()
    mock_patch.assert_called_once_with(workspace_id=workspace_id)

    mock_patch.reset_mock()
    mapping = Mapping(source_type='CATEGORY', destination_type='ACCOUNT',
                     source_id=category.id, destination_id=585, workspace_id=workspace_id)
    mapping.save()
    mock_patch.assert_not_called()
