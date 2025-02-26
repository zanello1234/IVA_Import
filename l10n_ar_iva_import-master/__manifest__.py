{
    "name": "l10n_ar_iva_import",
    "summary": """
        Importacion de IVA 
        """,
    "description": """
    """,
    "category": "Accounting",
    "version": "1.0",
    # any module necessary for this one to work correctly
    "depends": ["base","account"],
    # always loaded
    "data": [
        "account_view.xml",
        "security/ir.model.access.csv"
    ],
    'license': 'LGPL-3',
}
