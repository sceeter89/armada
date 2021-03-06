from __future__ import print_function
import base64
import json
import traceback
import os
import sys
import web
import api_base
from armada_command.consul.consul import consul_query
from armada_command.dockyard.alias import INSECURE_REGISTRY_ERROR_MSG
import docker_client


sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

LENGTH_OF_SHORT_CONTAINER_ID = 12


def print_err(*objs):
    print(*objs, file=sys.stderr)


class Run(api_base.ApiCommand):
    def run_container(self, image_path, dockyard_user, dockyard_password, dict_ports, dict_environment, dict_volumes,
                      run_command):
        exception_msg = ""
        try:
            restart_parameters = {'image_path': image_path,
                                  'dockyard_user': dockyard_user,
                                  'dockyard_password': dockyard_password,
                                  'ports': dict_ports,
                                  'environment': dict_environment,
                                  'volumes': dict_volumes,
                                  'run_command': run_command,
                                  'microservice_name': dict_environment.get('MICROSERVICE_NAME')
                                  }
            dict_environment['RESTART_CONTAINER_PARAMETERS'] = base64.b64encode(json.dumps(restart_parameters))
            dict_environment['ARMADA_RUN_COMMAND'] = base64.b64encode(run_command)
            microservice_name = dict_environment.get('MICROSERVICE_NAME')

            ports = None
            port_bindings = None
            if dict_ports:
                ports = map(int, dict_ports.values())
                port_bindings = dict((int(port_container), int(port_host))
                                     for port_host, port_container in dict_ports.iteritems())

            environment = None
            if dict_environment:
                environment = dict_environment

            volumes = None
            volume_bindings = None
            if dict_volumes:
                volumes = dict_volumes.values()
                volume_bindings = dict((path_host, {'bind': path_container, 'ro': False}) for path_host, path_container in dict_volumes.iteritems())

            docker_api = docker_client.api()

            dockyard_address, image_name, image_tag = self.__split_image_path(image_path)

            if dockyard_user and dockyard_password:
                logged_in = False
                # Workaround for abrupt changes in docker-py library.
                login_exceptions = []
                registry_endpoints = ['https://{0}/v1/'.format(dockyard_address),
                                        'https://{0}'.format(dockyard_address),
                                        dockyard_address]
                for registry_endpoint in registry_endpoints:
                    try:
                        docker_api.login(dockyard_user, dockyard_password, registry=registry_endpoint)
                        logged_in = True
                        break
                    except Exception as e:
                        login_exceptions.append(e)
                if not logged_in:
                    for e in login_exceptions:
                        print_err(e)
                    raise login_exceptions[0]

            if dockyard_address:
                try:
                    docker_client.docker_pull(docker_api, dockyard_address, image_name, image_tag)
                    docker_api.tag(dockyard_address + '/' + image_name, microservice_name, tag=image_tag, force=True)
                except Exception as e:
                    if "ping attempt failed" in str(e):
                        exception_msg += INSECURE_REGISTRY_ERROR_MSG.format(header="ERROR!", address=dockyard_address)
                    raise
            else:
                docker_api.tag(image_name, microservice_name, tag=image_tag, force=True)

            container_info = docker_api.create_container(microservice_name,
                                                         ports=ports,
                                                         environment=environment,
                                                         volumes=volumes)
            long_container_id = container_info['Id']
            docker_api.start(long_container_id,
                             port_bindings=port_bindings,
                             publish_all_ports=True,
                             privileged=True,
                             binds=volume_bindings)

            service_endpoints = {}
            agent_self_dict = consul_query('agent/self')
            service_ip = agent_self_dict['Config']['AdvertiseAddr']

            docker_inspect = docker_api.inspect_container(long_container_id)

            for docker_port, host_address in docker_inspect['NetworkSettings']['Ports'].items():
                service_endpoints['{0}:{1}'.format(service_ip, host_address[0]['HostPort'])] = docker_port

        except Exception as e:
            traceback.print_exc()
            exception_msg = exception_msg + "Cannot create requested container. {exception_class} - {exception}".format(
                exception_class=type(e).__name__, exception=str(e))
            return self.status_error(exception_msg)

        short_container_id = long_container_id[:LENGTH_OF_SHORT_CONTAINER_ID]
        return self.status_ok({'container_id': short_container_id, 'endpoints': service_endpoints})

    def __split_image_path(self, image_path):
        dockyard_address = None
        image_name = image_path
        image_tag = None

        if '/' in image_name:
            dockyard_address, image_name = image_name.split('/', 1)
        if ':' in image_name:
            image_name, image_tag = image_name.split(':', 1)

        return dockyard_address, image_name, image_tag

    def __prepare_dict_ports(self, post_data):
        ports = {}
        if post_data.get('ports'):
            ports.update(post_data.get('ports'))
        return ports

    def __prepare_dict_environment(self, post_data):
        environment = {}
        if post_data.get('environment'):
            environment.update(post_data.get('environment'))

        if post_data.get('microservice_name'):
            microservice_name = post_data.get('microservice_name')
        else:
            microservice_name = self.__split_image_path(post_data['image_path'])[1]

        environment['MICROSERVICE_NAME'] = microservice_name
        return environment

    def __prepare_dict_volumes(self, post_data):
        volumes = {}
        if post_data.get('volumes'):
            volumes.update(post_data.get('volumes'))

        volumes[docker_client.DOCKER_SOCKET_PATH] = docker_client.DOCKER_SOCKET_PATH
        return volumes

    def __prepare_run_command(self, post_data):
        run_command = post_data.get('run_command')
        return run_command

    def POST(self):
        image_path, error = self.get_post_parameter('image_path')
        if error:
            return self.status_error(error)

        post_data = json.loads(web.data())
        try:
            dockyard_user = post_data.get('dockyard_user')
            dockyard_password = post_data.get('dockyard_password')
            dict_ports = self.__prepare_dict_ports(post_data)
            dict_environment = self.__prepare_dict_environment(post_data)
            dict_volumes = self.__prepare_dict_volumes(post_data)
            run_command = self.__prepare_run_command(post_data)
        except:
            traceback.print_exc()
            return self.status_error('API Run: Invalid input data.')

        return self.run_container(image_path, dockyard_user, dockyard_password, dict_ports, dict_environment,
                                  dict_volumes, run_command)
