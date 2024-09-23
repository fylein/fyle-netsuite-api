from django.conf import settings

errors_with_two_fields = [
            r"An error occured in a upsert request: Invalid (\w+) reference key (-?\d+) for (\w+) (-?\d+).?$",
            r"Invalid (\w+) reference key (-?\d+) for (\w+) (-?\d+).?$"
]

errors_with_single_fields = [
    {
        'regex': r"You have entered an Invalid Field Value (-?\d+) for the following field: account",
        'inverse': False,
        'article_link': '/en/articles/9784864-field-value-related-errors-netsuite#h_a4568071c3'.format(settings.HELP_ARTICLE_DOMAIN)
    },
    {
        'regex': r"You have entered an Invalid Field Value (-?\d+) for the following field: location",
        'inverse': False,
        'article_link': '/en/articles/9784864-field-value-related-errors-netsuite#h_633ea074e6'.format(settings.HELP_ARTICLE_DOMAIN)
    },
    {
        'regex': r"You have entered an Invalid Field Value (-?\d+) for the following field: class",
        'inverse': False,
        'article_link': '/en/articles/9784864-field-value-related-errors-netsuite#h_380818cefc'.format(settings.HELP_ARTICLE_DOMAIN)
    },
    {
        'regex': r"You have entered an Invalid Field Value (-?\d+) for the following field: subsidiary",
        'inverse': False,
        'article_link': '/en/articles/9784864-field-value-related-errors-netsuite#h_5aae723749'.format(settings.HELP_ARTICLE_DOMAIN)
    },
    {
        'regex': r"You have entered an Invalid Field Value (-?\d+) for the following field: (\w+).?$",
        'inverse': False,
        'article_link': ''
    },
    {
        'regex': r"An error occured in a upsert request: Invalid (\w+) reference key (-?\d+).?$",
        'inverse': True,
        'article_link': ''
    },
    {
        'regex': r"Invalid (\w+) reference key (-?\d+).?$",
        'inverse': True,
        'article_link': ''
    }
]

error_mappings = {
    'taxcode': 'TAX_ITEM'
}

error_reference = {
    "expense_report": {
        'category_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid category reference key -?\d+ for entity -?\d+.?$", 
            'keys': ['expense_category', 'employee'],
            'article_link': ''
        },
        'account_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid account reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['account', 'subsidiary'],
            'article_link': ''
        },
        'project_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid customer reference key -?\d+ for entity -?\d+.?$", 
            'keys': ['project', 'employee'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_af66f0841c'.format(settings.HELP_ARTICLE_DOMAIN)
        },
        'location_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid location reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['location', 'subsidiary'],
            'article_link': ''
        },
        'department_reference_error': {
            'regex':r"An error occured in a upsert request: Invalid department reference key -?\d+ for subsidiary -?\d+.?$" , 
            'keys': ['department', 'subsidiary'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_d075ab4119'.format(settings.HELP_ARTICLE_DOMAIN)
        },
        'currency_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['currency', 'subsidiary'],
            'article_link': ''
        },
        'class_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid class reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['class', 'subsidiary'],
            'article_link': ''
        },
        'tax_code_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid taxcode reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['TAX_ITEM', 'subsidiary'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_06dce67392'.format(settings.HELP_ARTICLE_DOMAIN)
        }
    },
    "bills": {
        'bill_account_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid account reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['account', 'subsidiary'],
            'article_link': ''
        },
        'location_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid location reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['location', 'subsidiary'],
            'article_link': ''
        },
        'department_reference_error': {
            'regex':r"An error occured in a upsert request: Invalid department reference key -?\d+ for subsidiary -?\d+.?$" , 
            'keys': ['department', 'subsidiary'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_d075ab4119'.format(settings.HELP_ARTICLE_DOMAIN)
        },
        'currency_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['currency', 'subsidiary'],
            'article_link': ''
        },
        'vendor_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid entity reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['vendor', 'subsidiary'],
            'article_link': ''
        },
        'class_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid class reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['class', 'subsidiary'],
            'article_link': ''
        },

        'tax_code_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid taxcode reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['TAX_ITEM', 'subsidiary'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_06dce67392'.format(settings.HELP_ARTICLE_DOMAIN)
        },

        'currency_entity_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for entity -?\d+.?$",
            'keys': ['currency', 'vendor'],
            'article_link': ''
        },
    },
    "journal_entry": {
        'location_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid location reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['location', 'subsidiary'],
            'article_link': ''
        },
        'department_reference_error': {
            'regex':r"An error occured in a upsert request: Invalid department reference key -?\d+ for subsidiary -?\d+.?$" , 
            'keys': ['department', 'subsidiary'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_d075ab4119'.format(settings.HELP_ARTICLE_DOMAIN)
        },
        'account_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid account reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['account', 'subsidiary'],
            'article_link': ''
        },
        'currency_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['currency', 'subsidiary'],
            'article_link': ''
        },
        'project_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid customer reference key -?\d+ for entity -?\d+.?$", 
            'keys': ['project', 'employee'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_af66f0841c'.format(settings.HELP_ARTICLE_DOMAIN)
        },
        'class_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid class reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['class', 'subsidiary'],
            'article_link': ''
        },

        'tax_code_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid taxcode reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['TAX_ITEM', 'subsidiary'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_06dce67392'.format(settings.HELP_ARTICLE_DOMAIN)
        },
        'currency_entity_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for entity -?\d+.?$",
            'keys': ['currency', 'employee'],
            'article_link': ''
        },
        'vendor_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid entity reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['vendor', 'subsidiary'],
            'article_link': ''
        }
    },
    'credit_card_charge': {
        'category_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid category reference key -?\d+ for entity -?\d+.?$", 
            'keys': ['expense_category', 'employee'],
            'article_link': ''
        },
        'account_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid account reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['account', 'subsidiary'],
            'article_link': ''
        },
        'project_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid customer reference key -?\d+ for entity -?\d+.?$", 
            'keys': ['project', 'employee'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_af66f0841c'.format(settings.HELP_ARTICLE_DOMAIN)
        },
        'location_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid location reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['location', 'subsidiary'],
            'article_link': ''
        },
        'department_reference_error': {
            'regex':r"An error occured in a upsert request: Invalid department reference key -?\d+ for subsidiary -?\d+.?$" , 
            'keys': ['department', 'subsidiary'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_d075ab4119'.format(settings.HELP_ARTICLE_DOMAIN)
        },
        'currency_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid currency reference key -?\d+ for subsidiary -?\d+.?$", 
            'keys': ['currency', 'subsidiary'],
            'article_link': ''
        },
        'class_reference_error':{
            'regex': r"An error occured in a upsert request: Invalid class reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['class', 'subsidiary'],
            'article_link': ''
        },

        'tax_code_reference_error': {
            'regex': r"An error occured in a upsert request: Invalid taxcode reference key -?\d+ for subsidiary -?\d+.?$",
            'keys': ['TAX_ITEM', 'subsidiary'],
            'article_link': '{}/en/articles/9784864-field-value-related-errors-netsuite#h_06dce67392'.format(settings.HELP_ARTICLE_DOMAIN)
        }
    }
}
