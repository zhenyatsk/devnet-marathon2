import argparse
from ping3 import ping
import yaml

from ttp import ttp

from nornir import InitNornir
from nornir.core.inventory import *
from nornir.core.task import Result
from nornir.plugins.tasks import networking

from utils import get_ip_address_list, get_interface_full_name


def get_config(task):
    r = task.run(
        task=networking.netmiko_send_command,
        command_string='show running-config'
    )
    task.host['config'] = r.result


def interface_parser(old_config):
    parser = ttp(data=old_config, template='ttp_templates/ios_interfaces.j2')
    parser.parse()
    interfaces = parser.result()[0][0]
    return interfaces


def parse_config(task):
    task.host['int_list'] = [
        interface
        for interface in interface_parser(task.host['config'])
        if 'mode' in interface.keys()
    ]

    task.host['access_interfaces'] = [
        interface['interface']
        for interface in task.host['int_list']
        if interface['mode'] == 'access'
        and 'access_vlan' in interface.keys()
    ]


def collect_interfaces_mac_address_table(task, macaddress):
    print(f'start collection on host {task.host.hostname}')
    task.run(
        task=get_config,
        name='Getting Interface Information'
    )

    task.run(
        task=parse_config,
        name='Parsing config files',
    )

    mac_table = task.run(
        task=networking.napalm_get,
        name="MacAddressTable",
        getters=["get_mac_address_table"]
    )

    for entry in mac_table.result.get('get_mac_address_table'):
        if entry.get('mac') == macaddress.upper():
            interface_name = get_interface_full_name(short_name=entry.get('interface'))
            if interface_name in task.host['access_interfaces']:
                print(f'mac is {macaddress} on access port {entry.get("interface")}')

    return Result(result='parsed', host=task.host)


def main():
    parser = argparse.ArgumentParser(description='DevNet Tool2')
    parser.add_argument('--user-mac', type=str, required=True, help='usermac')
    parser.add_argument('--username', type=str, required=True, help='Username')
    parser.add_argument('--password', type=str, required=True, help='Password')
    parser.add_argument('--network', type=str, required=True, help='Management Network')

    args = parser.parse_args()

    inv = Inventory(groups={}, hosts={})

    for address in get_ip_address_list(args.network):
        r = ping(address,timeout=1)
        if not r:
            print('not reachable')
            continue

        inv.add_host(
            name=address,
            hostname=address,
            platform='ios',
            port=22,
            username=args.username,
            password=args.password
        )

    with open('hosts.yaml', 'w') as f:
        f.write(yaml.dump(inv.get_hosts_dict()))
        f.close()
    with open('groups.yaml', 'w') as f:
        f.write(yaml.dump(inv.get_groups_dict()))
        f.close()

    nr = InitNornir()
    nr.run(task=collect_interfaces_mac_address_table, macaddress=args.user_mac)


if __name__ == "__main__":
    main()
