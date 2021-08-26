"""
Contains various tests Payloads
"""


def create_subsidiary_mappings_payload(workspace_id):
    return {
        "subsidiary_name": "Honeycomb Mfg.",
        "internal_id": "1",
        "workspace": workspace_id
    }


def create_general_mappings_payload(workspace_id):
    return {
        "workspace": workspace_id,
        "location_name": "01: San Francisco",
        "location_id": "2",
        "location_level": "ALL",
        "accounts_payable_name": "Accounts Payable 2",
        "accounts_payable_id": "176",
        "reimbursable_account_name": "Test Account",
        "reimbursable_account_id": "1",
        "default_ccc_account_name": "VISA",
        "default_ccc_account_id": "129",
        "vendor_payment_account_id": "Test Account",
        "use_employee_department": False,
        "department_level": "",
        "vendor_payment_account_name": "Test Account",
        "default_ccc_vendor_id": "1",
        "default_ccc_vendor_name": "Test Vendor"
    }
