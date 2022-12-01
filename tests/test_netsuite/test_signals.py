import logging
from unittest import mock
from .fixtures import data
from fyle_accounting_mappings.models import DestinationAttribute
from apps.netsuite.models import CustomSegment

logger = logging.getLogger(__name__)
logger.level = logging.INFO


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

    custom_segment = DestinationAttribute.objects.filter(attribute_type='LOCATION').count()
    assert custom_segment == 36

    CustomSegment.objects.create(
        name='LOCATION',
        segment_type='CUSTOM_SEGMENT',
        script_id='custcolauto87',
        internal_id='1002s',
        workspace_id=49
    )

    custom_segment = DestinationAttribute.objects.filter(attribute_type='LOCATION').count()
    assert custom_segment == 36

    try:
        with mock.patch('netsuitesdk.api.custom_segments.CustomSegments.get') as mock_call:
            mock_call.side_effect = Exception()
            CustomSegment.objects.create(
                name='LOCATION',
                segment_type='CUSTOM_SEGMENT',
                script_id='custcolauto87',
                internal_id='1002s',
                workspace_id=49
            )
    except:
        logger.info('rest_framework.exceptions.NotFound')
