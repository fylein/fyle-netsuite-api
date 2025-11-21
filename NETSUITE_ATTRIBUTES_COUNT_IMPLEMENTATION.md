# NetSuite Attributes Count - Implementation Guide

---

## Current Implementation

```python
# apps/netsuite/connector.py

# OLD - Different limits for each attribute
SYNC_UPPER_LIMIT = {
    'projects': 10000,
    'customers': 25000,
    'classes': 2000,
    'accounts': 2000,
    'locations': 2000,
    'departments': 2000,
    'vendors': 20000,
}

def is_sync_allowed(self, attribute_type: str, attribute_count: int):
    """
    Checks if the sync is allowed based on attribute type and count.
    
    Note:
        - For 'projects' and 'customers', sync is only allowed if count is within SYNC_UPPER_LIMIT
        - For other types, workspaces created after Oct 1, 2024 have stricter limits
    """
    if attribute_count <= SYNC_UPPER_LIMIT[attribute_type]:
        return True

    # Special handling for projects and customers
    if attribute_type in ['projects', 'customers']:
        return False

    # For other types, check workspace creation date
    workspace = Workspace.objects.get(id=self.workspace_id)
    cutoff_date = timezone.make_aware(datetime(2024, 10, 1), timezone.get_current_timezone())
    return workspace.created_at <= cutoff_date

def sync_accounts(self):
    attribute_count = self.connection.accounts.count()
    if not self.is_sync_allowed(attribute_type='accounts', attribute_count=attribute_count):
        logger.info('Skipping sync of accounts for workspace %s', self.workspace_id)
        return
    # ... rest of sync logic
```

---

## Implementation

### 1. Update Sync Upper Limit and is_sync_allowed Function

**File:** `apps/netsuite/connector.py`

Replace the dictionary with a single constant and simplify `is_sync_allowed()` function:

```python
# NEW - Single consistent limit for all attributes
SYNC_UPPER_LIMIT = 30000

def is_sync_allowed(self, attribute_count: int):
    """
    Checks if the sync is allowed based on workspace creation date and count limit
    
    Returns:
        bool: True if sync allowed, False otherwise
    """
    if attribute_count > SYNC_UPPER_LIMIT:
        workspace = Workspace.objects.get(id=self.workspace_id)
        if workspace.created_at > timezone.make_aware(datetime(2024, 10, 1), timezone.get_current_timezone()):
            return False  # Block sync for new workspaces
        else:
            return True   # Allow sync for old workspaces
    
    return True  # Allow sync if under limit
```

---

### 2. Database Model

**File:** `apps/netsuite/models.py`

```python
class NetSuiteAttributesCount(models.Model):
    """
    Store NetSuite attribute counts for each workspace
    """
    id = models.AutoField(primary_key=True)
    workspace = models.OneToOneField(
        Workspace, 
        on_delete=models.CASCADE,
        help_text='Reference to workspace',
        related_name='netsuite_attributes_count'
    )
    
    # Attribute counts
    accounts_count = models.IntegerField(default=0, help_text='Number of accounts in NetSuite')
    expense_categories_count = models.IntegerField(default=0, help_text='Number of expense categories in NetSuite')
    items_count = models.IntegerField(default=0, help_text='Number of items in NetSuite')
    currencies_count = models.IntegerField(default=0, help_text='Number of currencies in NetSuite')
    locations_count = models.IntegerField(default=0, help_text='Number of locations in NetSuite')
    classifications_count = models.IntegerField(default=0, help_text='Number of classifications in NetSuite')
    departments_count = models.IntegerField(default=0, help_text='Number of departments in NetSuite')
    vendors_count = models.IntegerField(default=0, help_text='Number of vendors in NetSuite')
    employees_count = models.IntegerField(default=0, help_text='Number of employees in NetSuite')
    subsidiaries_count = models.IntegerField(default=0, help_text='Number of subsidiaries in NetSuite')
    tax_items_count = models.IntegerField(default=0, help_text='Number of tax items in NetSuite')
    projects_count = models.IntegerField(default=0, help_text='Number of projects in NetSuite')
    customers_count = models.IntegerField(default=0, help_text='Number of customers in NetSuite')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, help_text='Created at datetime')
    updated_at = models.DateTimeField(auto_now=True, help_text='Updated at datetime', db_index=True)
    
    class Meta:
        db_table = 'netsuite_attributes_count'
    
    @staticmethod
    def update_attribute_count(workspace_id: int, attribute_type: str, count: int):
        """
        Update attribute count for a workspace
        
        :param workspace_id: Workspace ID
        :param attribute_type: Type of attribute (e.g., 'accounts', 'vendors')
        :param count: Count value from NetSuite
        """
        netsuite_count, _ = NetSuiteAttributesCount.objects.get_or_create(workspace_id=workspace_id)
        field_name = f'{attribute_type}_count'
        setattr(netsuite_count, field_name, count)
        netsuite_count.save(update_fields=[field_name, 'updated_at'])
```

---

### 3. Update Sync Methods

**File:** `apps/netsuite/connector.py`

Update each sync method to persist the count and use simplified `is_sync_allowed()`:

```python
def sync_accounts(self):
    """
    Sync accounts
    """
    attribute_count = self.connection.accounts.count()
    
    # Persist the count using helper method
    from apps.netsuite.models import NetSuiteAttributesCount
    NetSuiteAttributesCount.update_attribute_count(
        workspace_id=self.workspace_id,
        attribute_type='accounts',
        count=attribute_count
    )
    
    # Check if sync is allowed
    if not self.is_sync_allowed(attribute_count=attribute_count):
        logger.info('Skipping sync of accounts for workspace %s as it has %s counts which is over the limit of %s', 
                    self.workspace_id, attribute_count, SYNC_UPPER_LIMIT)
        return
    
    # ... rest of sync logic remains the same
```

---

### 4. Create Record on NetSuite Connection

**File:** `apps/workspaces/views.py`

Add NetSuiteAttributesCount creation when NetSuite credentials are created:

```python
# In the NetSuite connection view, add this line after NetSuiteCredentials creation (around line 239):
from apps.netsuite.models import NetSuiteAttributesCount

# Add after netsuite_credentials.save() or workspace.save()
NetSuiteAttributesCount.objects.get_or_create(workspace_id=workspace.id)
```

---

### 5. Serializer

**File:** `apps/netsuite/serializers.py`

```python
class NetSuiteAttributesCountSerializer(serializers.ModelSerializer):
    """
    Serializer for NetSuite Attributes Count
    """
    class Meta:
        model = NetSuiteAttributesCount
        fields = '__all__'
```

---

### 6. View

**File:** `apps/netsuite/views.py`

```python
from apps.netsuite.models import NetSuiteAttributesCount
from apps.netsuite.serializers import NetSuiteAttributesCountSerializer

class NetSuiteAttributesCountView(generics.RetrieveAPIView):
    """
    GET NetSuite Attributes Count for a workspace
    
    Endpoint: GET /api/workspaces/<workspace_id>/netsuite/attributes_count/
    """
    queryset = NetSuiteAttributesCount.objects.all()
    serializer_class = NetSuiteAttributesCountSerializer
    lookup_field = 'workspace_id'
    lookup_url_kwarg = 'workspace_id'
```

---

### 7. URL

**File:** `apps/netsuite/urls.py`

```python
from .views import (
    # ... existing imports ...
    NetSuiteAttributesCountView,
)

netsuite_app_paths = [
    # ... existing patterns ...
    path('attributes_count/', NetSuiteAttributesCountView.as_view(), name='netsuite-attributes-count'),
]
```

Full URL: `GET /api/workspaces/<workspace_id>/netsuite/attributes_count/`

---

## API Response

**Success Response (200 OK):**

```json
{
    "id": 1,
    "workspace": 123,
    "accounts_count": 1500,
    "expense_categories_count": 250,
    "items_count": 800,
    "currencies_count": 15,
    "locations_count": 150,
    "classifications_count": 80,
    "departments_count": 120,
    "vendors_count": 5000,
    "employees_count": 350,
    "subsidiaries_count": 5,
    "tax_items_count": 30,
    "projects_count": 3000,
    "customers_count": 8000,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T14:45:00Z"
}
```

**Not Found Response (404):** Django's default 404 response


