rollback;
begin;

update expenses e
set paid_on_fyle = 't'
from reimbursements r
where e.settlement_id = r.settlement_id 
  and e.paid_on_netsuite = 't' 
  and r.state = 'COMPLETE';
