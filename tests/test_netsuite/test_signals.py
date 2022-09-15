from fyle_accounting_mappings.models import DestinationAttribute
from .fixtures import data

from apps.netsuite.models import CustomSegment


def test_sync_custom_segments(mocker, db):
    mocker.patch(
        'netsuitesdk.api.custom_segments.CustomSegments.get',
        return_value=data['get_custom_segment']
    )

    mocker.patch(
        'netsuitesdk.api.custom_record_types.CustomRecordTypes.get_all_by_id',
        return_value=data['get_custom_records_all']
    )

    mocker.patch(
        'netsuitesdk.api.custom_lists.CustomLists.get',
        return_value=data['get_custom_list']
    )
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
    
    custom_list = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_SINGER').count()
    assert custom_list == 0

    CustomSegment.objects.create(
        name='FAVOURITE_SINGER',
        segment_type='CUSTOM_LIST',
        script_id='custcol780',
        internal_id='491',
        workspace_id=2
    )

    custom_list = DestinationAttribute.objects.filter(attribute_type='FAVOURITE_SINGER').count()
    assert custom_list == 6

    custom_segment = DestinationAttribute.objects.filter(attribute_type='SAMPLE_SEGMENT').count()
    assert custom_segment == 0

    CustomSegment.objects.create(
        name='PRODUCTION_LINE',
        segment_type='CUSTOM_SEGMENT',
        script_id='custcolauto87',
        internal_id='1002s',
        workspace_id=49
    )

    custom_segment = DestinationAttribute.objects.filter(attribute_type='PRODUCTION_LINE').count()

    assert custom_segment == 5
    