import pytest
from apps.fyle.models import ExpenseGroup

@pytest.mark.django_db(transaction=True)
def test_create_expense_group(create_expense_group):
    
    new_expense_group = ExpenseGroup.objects.filter(workspace_id=1)

    assert len(new_expense_group) == 3
    

    
    





    
    



