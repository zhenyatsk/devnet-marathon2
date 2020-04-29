import ipaddress
import re

from typing import List


def get_ip_address_list(arg: str) -> List[str]:
    address_list = list(ipaddress.IPv4Network(arg).hosts())
    return map(str, address_list)


short_to_full_map = {
    'Fa': 'FastEthernet',
    'Gi': 'GigabitEthernet',
    'Po': 'Port-channel',
    'Te': 'TenGigabitEthernet'
}


def get_interface_full_name(short_name: str) -> str:
    matches = re.search(r"^(?P<Name>[A-Za-z]+)(?P<Number>[\d/]+)", short_name, re.MULTILINE)
    if matches:
        name, number = matches.group('Name'), matches.group('Number')
        return short_to_full_map.get(name) + number
    else:
        return short_name
