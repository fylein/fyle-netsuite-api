from time import time
from fyle_accounting_mappings.models import Mapping, MappingSetting, ExpenseAttribute, DestinationAttribute

start = time()

# config
workspace_id = 1
destination_attribute_type = 'EMPLOYEE'
employee_mapping_preference = 'EMAIL'

employee_destination_attributes = DestinationAttribute.objects.filter(
    attribute_type=destination_attribute_type, workspace_id=workspace_id, mapping__destination_id__isnull=True).all()

attribute_values = ''
destination_id_value_map = {}
for destination_employee in employee_destination_attributes:
    value_to_be_appended = None
    if employee_mapping_preference == 'EMAIL' and destination_employee.detail and destination_employee.detail['email']:
        value_to_be_appended = destination_employee.detail['email']
    elif employee_mapping_preference in ['NAME', 'EMPLOYEE_CODE']:
        value_to_be_appended = destination_employee.value
    # EXTRA LINE
    if value_to_be_appended:
        attribute_values = '{}|{}'.format(attribute_values, value_to_be_appended.lower())
        destination_id_value_map[value_to_be_appended.lower()] = destination_employee.id

mapping_batch = []

if employee_mapping_preference == 'EMAIL':
    filter_on = 'value__iregex'
elif employee_mapping_preference == 'NAME':
    filter_on = 'detail__full_name__iregex'
elif employee_mapping_preference == 'EMPLOYEE_CODE':
    filter_on = 'detail__employee_code__iregex'

auto_map_filter = {
    # check withour r''
    filter_on: r'({})'.format(attribute_values[1:])
}

employee_source_attributes = ExpenseAttribute.objects.filter(
    attribute_type='EMPLOYEE', workspace_id=workspace_id, auto_mapped=False,
    **auto_map_filter
).all()

for source_emp in employee_source_attributes:
    destination_id = destination_id_value_map[source_emp.value.lower()]
    mapping_batch.append(
        Mapping(
            source_type='EMPLOYEE',
            destination_type=destination_attribute_type,
            source_id=source_emp.id,
            destination_id=destination_id,
            workspace_id=workspace_id
        )
    )

created_mappings = Mapping.objects.bulk_create(mapping_batch, batch_size=50)

expense_attributes_to_be_updated = []
for mapping in created_mappings:
    expense_attributes_to_be_updated.append(
        ExpenseAttribute(
            id=mapping.source.id,
            auto_mapped=True
        )
    )

ExpenseAttribute.objects.bulk_update(expense_attributes_to_be_updated, fields=['auto_mapped'], batch_size=50)

end = time()

print('Total time taken is', end - start)