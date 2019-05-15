import json
import os

import redis
from flask import Response

from .host_registry import HostRegistry

__ACTIVE_NAMESPACES__ = {}


# This agent will find a list of appropriate hosts
# If there are no hosts available then it will return an exception (for now just run locally)
# It will then enqueue the commands onto broker(redis here and the user will provide location and port -
# default will be localhost default Redis port)
# Each host will be sent a run command and the scheduler will return whether the job was successfully started
# redis will handle stdout of each job

def is_redis_available(redis_server, redis_port):
    r = redis.Redis(host=redis_server, port=redis_port)
    try:
        r.get("")  # getting None returns None or throws an exception
    except (redis.exceptions.ConnectionError, redis.exceptions.BusyLoadingError):
        return False
    return True


def enqueue_commands(commands, redis_host, redis_port):
    if not is_redis_available(redis_host, redis_port):
        raise ('server at {}:{} does not exist'.format(redis_host, redis_port))
    # generate queue_id
    queue_id = 'job.{}'.format(os.getpid())
    r = redis.Redis(host=redis_host, port=redis_port)
    for command in commands:
        r.lpush(queue_id, json.dumps(command))
    return queue_id


def schedule_job(namespace, job, cpu_count, memory):  # noqa: E501
    try:
        commands = job['tasks']
    except Exception as e:
        return "Invalid input task, %s" % str(e), 400
    hosts = HostRegistry.get_available_host(core_count=cpu_count, memory=memory)
    if not hosts:
        return "No available agents to process the request.", 400
    else:
        active_host_objects = []
        active_hosts = []
        for host in hosts:
            queue_id = enqueue_commands(commands, host.redis_host, host.redis_port)
            container_names = HostRegistry.run_command(host=host, queue_id=queue_id, redis_host=host.redis_host,
                                                       redis_port=host.redis_port)
            host_object = host.to_object()
            host_object['containers'] = container_names
            active_host_objects.append(host_object)
            active_hosts.append({'containers': container_names, 'host': host})
        try:
            namespace_obj = __ACTIVE_NAMESPACES__[namespace]
        except KeyError:
            namespace_obj = []
            __ACTIVE_NAMESPACES__[namespace] = namespace_obj
        namespace_obj.extend(active_hosts)
        [host.free_resources(required_memory=memory, required_cores=cpu_count) for host in hosts]
        # for now return hosts - fr
        return active_host_objects


def status(namespace):
    try:
        namespace_obj = __ACTIVE_NAMESPACES__[namespace]
    except KeyError:
        return "Namespace does not exist", 404
    status_codes = {}
    for active_hosts in namespace_obj:
        containers = active_hosts['containers']
        host = active_hosts['host']
        for container_name in containers:
            status_code = HostRegistry.status(host, container_name=container_name)
            status_codes[container_name] = status_code
    return status_codes


def log(namespace):
    try:
        namespace_obj = __ACTIVE_NAMESPACES__[namespace]
    except KeyError:
        return "Namespace does not exist", 404
    logs = {}

    def generate_logs():
        for active_hosts in namespace_obj:
            containers = active_hosts['containers']
            host = active_hosts['host']
            for container_name in containers:
                log_obj = HostRegistry.log(host, container_name=container_name)
                yield b'Container %s: Output: %s\n' % (container_name.encode(), log_obj['out'])
                yield b'Container %s: Error: %s\n' % (container_name.encode(), log_obj['err'])
                logs[container_name] = log_obj

    return Response(generate_logs(), mimetype='text/stream')
