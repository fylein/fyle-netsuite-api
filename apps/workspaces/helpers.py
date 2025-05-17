
def get_error_model_path() -> str:
    """
    Get error model path: This is for imports submodule
    :return: str
    """
    return 'apps.tasks.models.Error'


def get_import_configuration_model_path() -> str:
    """
    Get import configuration model path: This is for imports submodule
    :return: str
    """
    return 'apps.workspaces.models.Configuration'


def get_app_name() -> str:
    """
    Get Integration Name. This is for imports submodule
    :return: str
    """
    return 'NETSUITE'
