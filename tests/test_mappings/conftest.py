"""
Contains various tests Payloads
"""
from fyle_accounting_mappings.models import MappingSetting
import pytest

@pytest.fixture
def create_mapping_settings(db):
    mapping_setting, _ = MappingSetting.objects.update_or_create(
                    source_field='CUSTOM_FIELD',
                    workspace_id=1,
                    destination_field='CUSTOM_FIELD_NETSUITE',
                    defaults={
                        'import_to_fyle': True,
                        'is_custom': True
                    }
                )
