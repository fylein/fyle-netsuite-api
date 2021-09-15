-- Script to move employee mapping setting data to employee field mapping in workspace general settings

rollback;
begin;

update configurations
set employee_field_mapping = 'EMPLOYEE' 
where workspace_id in (
    select workspace_id from mapping_settings 
    where source_field = 'EMPLOYEE' 
    and destination_field = 'EMPLOYEE'
);

update configurations
set employee_field_mapping = 'VENDOR' 
where workspace_id in (
    select workspace_id from mapping_settings 
    where source_field = 'EMPLOYEE' 
    and destination_field = 'VENDOR'
);
