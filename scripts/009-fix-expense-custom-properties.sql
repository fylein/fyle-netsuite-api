rollback;
begin;

update expenses set custom_properties = '{}' where custom_properties is null;