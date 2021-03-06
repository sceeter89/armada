from armada_command.dockyard import alias
from armada_backend.utils import get_ship_name, get_other_ship_ips, get_current_datacenter, is_ship_commander
import consul_config

import json


def _save_runtime_settings():
    consul_settings = {}
    consul_settings['is_commander'] = is_ship_commander()
    consul_settings['name'] = get_ship_name()
    consul_settings['ships'] = get_other_ship_ips()
    consul_settings['datacenter'] = get_current_datacenter()
    consul_settings['dockyards'] = alias.get_list()

    with open(consul_config.RUNTIME_SETTINGS_PATH, 'w') as runtime_settings:
        runtime_settings.write(json.dumps(consul_settings, sort_keys=True, indent=4))


def override_runtime_settings(consul_mode = None, ship_name = None, ship_ips = None, datacenter = None):
    consul_settings = {}
    if consul_mode is not None:
        consul_settings['is_commander'] = consul_mode != consul_config.ConsulMode.CLIENT
    if ship_name is not None:
        consul_settings['name'] = ship_name
    if ship_ips is not None:
        consul_settings['ships'] = ship_ips
    if datacenter is not None:
        consul_settings['datacenter'] = datacenter

    with open(consul_config.OVERRIDE_RUNTIME_SETTINGS_PATH, 'w') as runtime_settings:
        runtime_settings.write(json.dumps(consul_settings, sort_keys=True, indent=4))


def _init_dockyards():
    try:
        with open(consul_config.ORIGINAL_RUNTIME_SETTINGS_PATH) as runtime_settings_json:
            runtime_settings = json.load(runtime_settings_json)
    except:
        runtime_settings = {}

    # Initialize dockyard list with fallback dockyard.
    if not alias.get_alias(alias.DOCKYARD_FALLBACK_ALIAS):
        alias.set_alias(alias.DOCKYARD_FALLBACK_ALIAS, alias.DOCKYARD_FALLBACK_ADDRESS)

    dockyards = runtime_settings.get('dockyards', {})
    default_alias = None
    for info in dockyards:
        dockyard_alias = info.get('name')
        if dockyard_alias and not alias.get_alias(dockyard_alias):
            alias.set_alias(dockyard_alias, info.get('address'), info.get('user'), info.get('password'), check_if_accessible=False)
            if info.get('is_default') == True:
                default_alias = dockyard_alias
    if default_alias:
        alias.set_default(default_alias)


if __name__ == '__main__':

    if not alias.get_initialized():
        _init_dockyards()
        alias.set_initialized()

    _save_runtime_settings()
