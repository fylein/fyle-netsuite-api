import re

from apps.netsuite.models import CustomSegment
from apps.workspaces.models import Configuration
from .errors_reference import error_reference, errors_with_two_fields, errors_with_single_fields
from fyle_accounting_mappings.models import DestinationAttribute


def get_custom_attribute(custom_attribute):

    """
    Get the custom attribute from custom_segment model.

    Args:
        custom_attribute (str): The attribute_type.

    Returns:
        str or None: return the custom_attribute if this attribute is custom field else return none.
    """

    custom_segment = CustomSegment.objects.filter(script_id=custom_attribute).first()
    if custom_segment:
        custom_attribute = custom_segment.name
        return custom_attribute
    else:
        return None


def error_matcher(message, export_type, configuration: Configuration):
    """
    Match the type of error and according to that get the attribute_type and destination_id.

    Args:
        message (str): message of the exception.
        export type (int): The type of export.
        configuration: Configuration setting for the organization.

    Returns:
        list(dict): List of dictionatory containing destination_ids and respective attribute_types.
    """

    # We have two types of errors in Netsuite, one type contains only one destination id.
    # Here we are checking if the message is of this type, if yes will proceed to get the attribute_type and destination_id
    for pattern in errors_with_single_fields:
        if re.match(pattern['regex'], message):
            match = re.match(pattern['regex'], message)
            value = match.group(1)
            field = match.group(2)

            if value == 'entity':
                value = configuration.employee_field_mapping

            # Some times the error has attribute first then id and vice versa. In this case 
            # I have added a inverse attribute in the error_reference to check if the values need to inversed.
            if pattern['inverse']:
                #here we are checking if the attribute is custom field by querying custom_segment model.
                custom_attribute = get_custom_attribute(value)
                if custom_attribute:
                    return [{'attribute_type': custom_attribute,
                            'destination_id': field}]
                return [{'attribute_type': value,
                        'destination_id': field}]
            else:
                custom_attribute = get_custom_attribute(field)
                if custom_attribute:
                    return [{'attribute_type': custom_attribute,
                            'destination_id': value}]
                return [{'attribute_type': field,
                        'destination_id': value}]
        
    # The second type of errors contain two destination_ids.
    # Here we are checking if that error message matches these regex and proceed to get the respective attribute_types and destination_ids.
    for pattern in errors_with_two_fields:
        if re.match(pattern, message):
            for _, error_data in error_reference[export_type].items():
                if re.match(error_data['regex'], message):
                    match = re.search(pattern, message)
                    attribute_1, id_1, attribute_2, id_2 = match.group(1), match.group(2), match.group(3), match.group(4)
                    custom_attribute = get_custom_attribute(attribute_1)
                    if custom_attribute:
                        return [{'attribute_type': custom_attribute, 'destination_id': id_1}, {'attribute_type': attribute_2, 'destination_id': id_2}]
                    
                    print([{'attribute_type': key, 'destination_id':number} for key, number in zip(error_data['keys'], [id_1, id_2])])
                    return [{'attribute_type': key, 'destination_id':number} for key, number in zip(error_data['keys'], [id_1, id_2])]

    return []


def get_entity_values(error_dict, workspace_id):

    """
    Get the entities from DB using destination_id and attribute_type.

    Args:
        error_dict list(dict): This contains the attribute_type and destination_id to filter the DB.
        workspace_id (int): Workspace id of the organization used to filter the DB.

    Returns:
        list(dict): List of dictionatory containing destination_ids and respective attribute_types.
    """

    destination_attributes = []
    for errors in error_dict:
        destination_attributes.append(
            DestinationAttribute.objects.filter(
            destination_id=errors['destination_id'],
            attribute_type=errors['attribute_type'].upper(),
            workspace_id=workspace_id
        ).first())

    # all the items in list should exist in our DB else we will show unparsed error.
    if all(destination_attributes):
        return destination_attributes

    return []

def replace_destination_id_with_values(message, replacement):

    """
    Replace the original error message with parsed information making it more clear to the user.

    Args:
        message (string): message of the exception.
        replacement (list(dict)): This contains the attribute_type and destination_id to replace in the original error.

    Returns:
        list(dict): List of dictionatory containing destination_ids and respective attribute_types.
    """

    replacement_map = {}

    for value in replacement:
        destination_id = value.destination_id
        value = value.value

        arrowed_string = f"{destination_id} => {value}"
        replacement_map[destination_id] = arrowed_string

    #this will get the id's from the message and replace those values with our replacement dict which contains dictionary like this {1:1 => USD, 5: 5 => HoneComb Aus.}
    numeric_pattern = r'\b\d+\b'
    updated_message = re.sub(numeric_pattern, lambda x: replacement_map.get(x.group(), x.group()), message)
    
    return updated_message
