from time import time
from django.db.models import Q
from fyle_accounting_mappings.models import Mapping, MappingSetting, ExpenseAttribute, DestinationAttribute

start = time()

# config
workspace_id = 1
destination_attribute_type = 'CREDIT_CARD_ACCOUNT'
default_ccc_account_id = '25'
default_ccc_account_name = 'Accounts Payable'

employee_source_attributes = ExpenseAttribute.objects.filter(
    ~Q(mapping__destination_type=destination_attribute_type),
    attribute_type='EMPLOYEE', workspace_id=workspace_id
).all()

default_destination_attribute = DestinationAttribute.objects.filter(
    destination_id=default_ccc_account_id
).first()

mapping_batch = []
for source_emp in employee_source_attributes:
    mapping_batch.append(
        Mapping(
            source_type='EMPLOYEE',
            destination_type=destination_attribute_type,
            source_id=source_emp.id,
            destination_id=default_destination_attribute.id,
            workspace_id=workspace_id
        )
    )

created_mappings = Mapping.objects.bulk_create(mapping_batch, batch_size=50)

end = time()

print('Total time taken is', end - start)
