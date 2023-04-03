rollback;

begin;

-- Update the tax amounts to 0
update expenses set tax_amount = 0 where tax_amount is null and tax_group_id is not null;
