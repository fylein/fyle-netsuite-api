data = {
    "import_settings": {
        "configuration": {
            "import_categories": True,
            "import_items": False,
            "import_tax_items": True,
            "import_vendors_as_merchants": True,
            "auto_create_merchants": False,
            "import_netsuite_employees": False
        },
        "mapping_settings": [
            {
                "source_field": "COST_CENTER",
                "destination_field": "DEPARTMENT",
                "import_to_fyle": True,
                "is_custom": False,
                "source_placeholder": "cost center",
            },
            {
                "source_field": "PROJECT",
                "destination_field": "CLASS",
                "import_to_fyle": True,
                "is_custom": False,
                "source_placeholder": "project",
            },
            {
                "source_field": "Test Dependent",
                "destination_field": "CUSTOMER",
                "import_to_fyle": True,
                "is_custom": True,
                "source_placeholder": "class",
            },
        ],
    },
    "import_settings_without_mapping": {
        "configuration": {
            "import_categories": True,
            "import_items": True,
            "auto_create_merchants": False,
            "import_tax_items": True,
            "import_vendors_as_merchants": True,
            "import_netsuite_employees": False
        },
        "mapping_settings": [
            {
                "source_field": "Test Dependent",
                "destination_field": "CUSTOMER",
                "import_to_fyle": True,
                "is_custom": True,
                "source_placeholder": "class",
            }
        ],
    },
    "response": {
        "configuration": {
            "import_categories": True,
            "import_tax_items": True,
            "import_items": False,
            "auto_create_merchants": False,
            "import_vendors_as_merchants": True,
            "import_netsuite_employees": False
        },
        "mapping_settings": [
            {
                "source_field": "COST_CENTER",
                "destination_field": "CLASS",
                "import_to_fyle": True,
                "is_custom": False,
                "source_placeholder": "",
            },
            {
                "source_field": "PROJECT",
                "destination_field": "DEPARTMENT",
                "import_to_fyle": True,
                "is_custom": False,
                "source_placeholder": "",
            },
            {
                "source_field": "Test Dependent",
                "destination_field": "CUSTOMER",
                "import_to_fyle": True,
                "is_custom": True,
                "source_placeholder": "",
            },
        ],
        "workspace_id": 9,
    },
    "invalid_mapping_settings": {
        "configuration": {
            "import_categories": True,
            "import_tax_items": True,
            "import_items": False,
            "auto_create_merchants": False,
            "import_vendors_as_merchants": True,
            "import_netsuite_employees": False
        },
        "mapping_settings": None,
    },
}
