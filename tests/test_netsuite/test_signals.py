from attr import attributes
import pytest
from fyle_accounting_mappings.models import DestinationAttribute

from apps.netsuite.models import CustomSegment


def test_sync_custom_segments(db, add_netsuite_credentials):

    custom_records = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_BANDS').count()
    assert custom_records == 0

    CustomSegment.objects.create(
        name='FAVOURITE_BANDS',
        segment_type='CUSTOM_RECORD',
        script_id='custcol780',
        internal_id='476',
        workspace_id=1
    )

    custom_records = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_BANDS').count()
    assert custom_records == 5
    
    custom_list = DestinationAttribute.objects.filter(attribute_type='SRAVAN_DEMO').count()
    assert custom_list == 0

    CustomSegment.objects.create(
        name='SRAVAN_DEMO',
        segment_type='CUSTOM_LIST',
        script_id='custcol780',
        internal_id='491',
        workspace_id=2
    )

    custom_list = DestinationAttribute.objects.filter(attribute_type='SRAVAN_DEMO').count()
    assert custom_list == 2

    custom_segment = DestinationAttribute.objects.filter(attribute_type='SAMPLE_SEGMENT').count()
    assert custom_segment == 0

    CustomSegment.objects.create(
        name='PRODUCTION_LINE',
        segment_type='CUSTOM_SEGMENT',
        script_id='custcolauto',
        internal_id='1',
        workspace_id=49
    )

    custom_segment = DestinationAttribute.objects.filter(attribute_type='PRODUCTION_LINE').count()

    assert custom_segment == 2
    