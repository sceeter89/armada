from __future__ import print_function
import json
import sys

import requests


SHIP_IP = '172.17.42.1'


def print_err(*objs):
    print(*objs, file=sys.stderr)


def _query(query):
    hostname = SHIP_IP
    url = 'http://{hostname}:8500/v1/{query}'.format(**locals())
    return json.loads(requests.get(url, timeout=5).text)


def _create_dict_from_tags(tags):
    if not tags:
        return {}
    return dict((tag.split(':', 1) + [None])[:2] for tag in tags)


def get_service_to_addresses():
    service_to_addresses = {}
    service_names = list(_query('catalog/services').keys())
    for service_name in service_names:
        try:
            query = 'health/service/{service_name}'.format(**locals())
            instances = _query(query)
        except Exception as exception:
            exception_class = type(exception).__name__
            print_err(
                "query: health/service/{service_name} failed: {exception_class} - {exception}".format(**locals()))
            continue
        for instance in instances:
            service_checks_statuses = (check['Status'] for check in instance['Checks'])
            if any(status == 'critical' for status in service_checks_statuses):
                continue

            service_tags = instance['Service']['Tags']
            service_tags_dict = _create_dict_from_tags(service_tags)

            service_ip = instance['Node']['Address']
            service_port = instance['Service']['Port']
            service_address = '{service_ip}:{service_port}'.format(**locals())

            service_env = service_tags_dict.get('env') or None
            service_app_id = service_tags_dict.get('app_id') or None
            service_index = (service_name, service_env, service_app_id)
            if service_index not in service_to_addresses:
                service_to_addresses[service_index] = []
            service_to_addresses[service_index].append(service_address)
    return service_to_addresses
