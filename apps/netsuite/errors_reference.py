
errors_with_two_fields = [
            r"An error occured in a upsert request: Invalid category reference key -?\d+ for entity -?\d+.?$",
            r"An error occured in a upsert request: Invalid account reference key -?\d+ for subsidiary -?\d+.?$",
            r"An error occured in a upsert request: Invalid customer reference key -?\d+ for entity -?\d+.?$",
            r"An error occured in a upsert request: Invalid location reference key -?\d+ for subsidiary -?\d+.?$",
            r"An error occured in a upsert request: Invalid department reference key -?\d+ for subsidiary -?\d+.?$",
            r"An error occured in a upsert request: Invalid currency reference key -?\d+ for subsidiary -?\d+.?$",
            r"An error occured in a upsert request: Invalid currency reference key -?\d+ for entity -?\d+.?$",
            r"An error occured in a upsert request: Invalid entity reference key -?\d+ for subsidiary -?\d+.?$", 
            r"An error occured in a upsert request: Invalid class reference key -?\d+ for subsidiary -?\d+.?$",
            r"An error occured in a upsert request: Invalid taxcode reference key -?\d+ for subsidiary -?\d+.?$",
            r"An error occured in a upsert request: Invalid custcol_cseg1 reference key -?\d+ for subsidiary -?\d+.?$",
            r"An error occured in a upsert request: Invalid cseg_be_locationcen reference key -?\d+ for class -?\d+.?$",
            r"Invalid account reference key -?\d+ for subsidiary -?\d+.?$"
]

errors_with_single_fields = [
    {'regex': r"You have entered an Invalid Field Value (-?\d+) for the following field: (\w+).?$",
     'inverse': False},
    {'regex': r"An error occured in a upsert request: Invalid (\w+) reference key (-?\d+).?$",
    'inverse': True},
    {'regex': r"Invalid (\w+) reference key (-?\d+).?$",
    'inverse': True},   
]


error_reference = {
    "expense_report": {
        'category_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid category reference key -?\d+ for entity -?\d+.?$", 
            'keys': ['expense_category', 'employee']
        },
        'account_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid account reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['account', 'subsidiary']
        },
        'project_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid customer reference key -?\d+ for entity -?\d+.?$", 
            'keys': ['customer', 'employee']
        },
        'location_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid location reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['location', 'subsidiary']
        },
        'department_reference_error': {
            'regex':r"An error occured in a upsert request: Invalid department reference key -?\d+ for subsidiary -?\d+.?$" , 
            'keys': ['department', 'subsidiary']
        },
        'currency_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['currency', 'subsidiary']
        },
        'class_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid class reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['class', 'subsidiary']
        },
        'custom_reference_error_1': {
            'regex': r"An error occured in a upsert request: Invalid custcol_cseg1 reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['custom', 'subsidiary']
        },

        'custom_reference_error_2': {
            'regex': r"An error occured in a upsert request: Invalid cseg_be_locationcen reference key -?\d+ for class -?\d+.?$",
            'keys': ['custom', 'class']
        },

        'tax_code_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid taxcode reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['TAX_ITEM', 'subsidiary']
        }
    },
    "bills": {
        'bill_account_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid account reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['account', 'subsidiary']
        },
        'location_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid location reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['location', 'subsidiary']
        },
        'department_reference_error': {
            'regex':r"An error occured in a upsert request: Invalid department reference key -?\d+ for subsidiary -?\d+.?$" , 
            'keys': ['department', 'subsidiary']
        },
        'currency_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['currency', 'subsidiary']
        },
        'vendor_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid entity reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['vendor', 'subsidiary']
        },
        'class_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid class reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['class', 'subsidiary']
        },
        'custom_reference_error_1': {
            'regex': r"An error occured in a upsert request: Invalid custcol_cseg1 reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['custom', 'subsidiary']
        },

        'custom_reference_error_2': {
            'regex': r"An error occured in a upsert request: Invalid cseg_be_locationcen reference key -?\d+ for class -?\d+.?$",
            'keys': ['custom', 'class']
        },

        'tax_code_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid taxcode reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['TAX_ITEM', 'subsidiary']
        },

        'currency_entity_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for entity -?\d+.?$",
            'keys': ['currency', 'vendor']
        },
    },
    "journal_entry": {
        'location_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid location reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['location', 'subsidiary']
        },
        'department_reference_error': {
            'regex':r"An error occured in a upsert request: Invalid department reference key -?\d+ for subsidiary -?\d+.?$" , 
            'keys': ['department', 'subsidiary']
        },
        'account_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid account reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['account', 'subsidiary']
        },
        'currency_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['currency', 'subsidiary']
        },
        'project_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid customer reference key -?\d+ for entity -?\d+.?$", 
            'keys': ['customer', 'employee']
        },
        'class_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid class reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['class', 'subsidiary']
        },
        'custom_reference_error_1': {
            'regex': r"An error occured in a upsert request: Invalid custcol_cseg1 reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['custom', 'subsidiary']
        },

        'custom_reference_error_2': {
            'regex': r"An error occured in a upsert request: Invalid cseg_be_locationcen reference key -?\d+ for class -?\d+.?$",
            'keys': ['custom', 'class']
        },

        'tax_code_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid taxcode reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['TAX_ITEM', 'subsidiary']
        },
        'currency_entity_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for entity -?\d+.?$",
            'keys': ['currency', 'employee']
        },
        'vendor_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid entity reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['vendor', 'subsidiary']
        },
    }
}
