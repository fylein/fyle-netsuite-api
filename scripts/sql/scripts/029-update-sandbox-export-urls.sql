rollback;
begin;

-- These values should be swapped after running the script
-- netsuite=> select count(export_url) from expense_groups where export_url like '%_sb%';
--  count 
-- -------
--    240
-- (1 row)

-- netsuite=> select count(export_url) from expense_groups where export_url like '%-sb%';
--  count 
-- -------
--      0
-- (1 row)

update expense_groups set export_url = replace(export_url, '_sb', '-sb');
