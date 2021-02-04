-- Script to remove redundant entries in task table
rollback;
begin;

delete from task_logs where type='FETCHING_EXPENSES' and status='COMPLETE' or status='FATAL';