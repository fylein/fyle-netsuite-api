import pytest
from apps.mappings.models import GeneralMapping
from apps.mappings.serializers import GeneralMappingSerializer
from .fixtures import data


def test_create_general_mapping(db):

    general_mapping_object = GeneralMappingSerializer.create(validated_data=data['general_mapping_payload'])
    print(general_mapping_object)

    assert 1==2