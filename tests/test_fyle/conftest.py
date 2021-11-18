import pytest

from apps.workspaces.models import Workspace, FyleCredential
from apps.fyle.tasks import create_expense_groups
from apps.tasks.models import TaskLog
from apps.fyle.models import ExpenseGroupSettings
from apps.fyle.helpers import check_interval_and_sync_dimension
from .fixtures import data