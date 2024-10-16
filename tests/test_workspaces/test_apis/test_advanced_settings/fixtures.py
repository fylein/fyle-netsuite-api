data = {
    "advanced_settings": {
        "configuration": {
            "change_accounting_period": True,
            "sync_fyle_to_netsuite_payments": True,
            "sync_netsuite_to_fyle_payments": False,
            "auto_create_destination_entity": False,
            "auto_create_merchants": True,
            "memo_structure": ["merchant", "purpose"],
            "je_single_credit_line": False,
        },
        "general_mappings": {
            "vendor_payment_account": {
                "name": "Payment Account",
                "id": 12
            },
            "netsuite_location": {
                "name": "Bir Billing",
                "id": "13"
            },
            "netsuite_department": {
                "name": "Bir Billing",
                "id": "13"
            },
            "netsuite_class": {
                "name": "Bir Billing",
                "id": "13"
            },
            "netsuite_location_level": "TRANSACTION_BODY",
            "netsuite_department_level": "TRANSACTION_BODY",
            "netsuite_class_level": "TRANSACTION_BODY",
            "use_employee_location": False,
            "use_employee_department": False,
            "use_employee_class": False
        },
        "workspace_schedules": {
            "enabled": True,
            "interval_hours": 24,
            "emails_selected": ["fyle@fyle.in"],
            "additional_email_options": {},
        },
    },
    "response": {
        "configuration": {
            "change_accounting_period": True,
            "sync_fyle_to_netsuite_payments": True,
            "sync_netsuite_to_fyle_payments": False,
            "auto_create_destination_entity": False,
            "auto_create_merchants": True,
            "memo_structure": ["merchant", "purpose"],
            "je_single_credit_line": False,
        },
        "general_mappings": {
            "vendor_payment_account": {
                "name": "Payment Account",
                "id": 12
            },
            "netsuite_location": {
                "name": "Bir Billing",
                "id": "13"
            },
            "netsuite_department": {
                "name": "Bir Billing",
                "id": "13"
            },
            "netsuite_class": {
                "name": "Bir Billing",
                "id": "13"
            },
            "netsuite_location_level": "TRANSACTION_BODY",
            "netsuite_department_level": "TRANSACTION_BODY",
            "netsuite_class_level": "TRANSACTION_BODY",
            "use_employee_location": False,
            "use_employee_department": False,
            "use_employee_class": False
        },
        "workspace_schedules": {
            "enabled": True,
            "start_datetime": "now()",
            "interval_hours": 24,
            "emails_selected": [],
            "additional_email_options": [],
        },
        "workspace_id": 9,
    },
    "validate": {
        "workspace_general_settings": {},
        "general_mappings": {},
        "workspace_schedules": {},
    },
}
