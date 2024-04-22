import re

from apps.workspaces.models import Configuration
from .errors_reference import error_reference, errors_with_two_fields, errors_with_single_fields
from fyle_accounting_mappings.models import DestinationAttribute

def error_matcher(string, workspace_id, export_type='expense_report'):

    for pattern in errors_with_single_fields:
        if re.match(pattern['regex'], string):
            match = re.match(pattern['regex'], string)
            value = match.group(1)
            field = match.group(2)

            if value == 'entity':
                configuration = Configuration.objects.get(workspace_id=workspace_id)
                value = configuration.employee_field_mapping

            if pattern['inverse']:
                return [{'attribute_type': value,
                        'destination_id': field}]
            else:
                return [{'attribute_type': field,
                        'destination_id': value}]

    for pattern in errors_with_two_fields:
        if re.match(pattern, string):
            for _, error_data in error_reference[export_type].items():
                if isinstance(error_data['regex'], list):
                    for reg in error_data['regex']:
                        if re.match(reg, string):
                            numbers = re.findall(r'-?\d+', string)
                            return [{'attribute_type': key, 'destination_id':number} for key, number in zip(error_data['keys'], numbers)]
                elif re.match(error_data['regex'], string):
                    numbers = re.findall(r'-?\d+', string)
                    return [{'attribute_type': key, 'destination_id':number} for key, number in zip(error_data['keys'], numbers)]

    return None


def get_entity_values(error_dict, workspace_id):

    destination_attributes = []

    for errors in error_dict:
        destination_attributes.append(
            DestinationAttribute.objects.filter(
            destination_id=errors['destination_id'],
            attribute_type=errors['attribute_type'].upper(),
            workspace_id=workspace_id
        ).first())

    if all(destination_attributes):
        return destination_attributes

    return None

def replace_destination_id_with_values(input_string, replacement):

    replacement_map = {}

    for value in replacement:
        destination_id = value.destination_id
        value = value.value

        arrowed_string = f"{destination_id} => {value}"
        replacement_map[destination_id] = arrowed_string

    numeric_pattern = r'\b\d+\b'
    updated_message = re.sub(numeric_pattern, lambda x: replacement_map.get(x.group(), x.group()), input_string)
    
    return updated_message
