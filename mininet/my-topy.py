#!/usr/bin/python

#  Copyright 2019-present Open Networking Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import argparse
import json
import os
from collections import OrderedDict

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import Host
from mininet.topo import Topo
from stratum import StratumBmv2Switch
from mininet.link import TCLink

CPU_PORT = 255


class IPv6Host(Host):
    """Host that can be configured with an IPv6 gateway (default route).
    """

    def config(self, ipv6, ipv6_gw=None, **params):
        super(IPv6Host, self).config(**params)
        self.cmd('ip -4 addr flush dev %s' % self.defaultIntf())
        self.cmd('ip -6 addr flush dev %s' % self.defaultIntf())
        self.cmd('ip -6 addr add %s dev %s' % (ipv6, self.defaultIntf()))
        if ipv6_gw:
            self.cmd('ip -6 route add default via %s' % ipv6_gw)
        # Disable offload
        for attr in ["rx", "tx", "sg"]:
            cmd = "/sbin/ethtool --offload %s %s off" % (self.defaultIntf(), attr)
            self.cmd(cmd)

        def updateIP():
            return ipv6.split('/')[0]

        self.defaultIntf().updateIP = updateIP

    def terminate(self):
        super(IPv6Host, self).terminate()


class TutorialTopo(Topo):
    """2x2 fabric topology with IPv6 hosts"""

    def __init__(self, *args, **kwargs):
        Topo.__init__(self, *args, **kwargs)
        with open("/mininet/topo.json") as f:
            topo_config = json.load(f)

        netcfg = {
            "devices":{},
            "hosts":{},
            "ports":{}
        }
        port_counters = {}
        self._create_switches(topo_config['switches'],netcfg)
        self._create_links(topo_config['links'],port_counters)
        self._create_hosts(topo_config['hosts'],port_counters,netcfg)
        with open("/mininet/netcfg1.json", "w") as f:
            json.dump(netcfg, f, indent=4)
        print(" netcfg1.json successfully created")


    def _create_switches(self, switches,netcfg):
        self.switch_map = {}
        self.switch_isSpine_map = {}
        leaf_counter = 1
        spine_counter = 1
        management_counter = 1
        for sw in switches:
            sw_name = sw["name"]
            self.switch_isSpine_map[sw_name] = sw['isSpine']

            device_key = "device:{}".format(sw_name)
            management_address = "grpc://mininet:500{:02d}?device_id=1".format(management_counter)
            management_counter+=1
            if sw.get("isSpine", False):
                myStationMac = "00:bb:00:00:00:{:02d}".format(leaf_counter)
                mySid = "3:20{}:2::".format(leaf_counter)
                leaf_counter += 1
            else:
                myStationMac = "00:aa:00:00:00:{:02d}".format(spine_counter)
                mySid = "3:10{}:2::".format(spine_counter)
                spine_counter += 1
            netcfg["devices"][device_key] = {
                "basic": {
                    "managementAddress": management_address,
                    "driver": "stratum-bmv2",
                    "pipeconf": "org.onosproject.ngsdn-tutorial"
                },
                "fabricDeviceConfig": {
                    "myStationMac": myStationMac,
                    "mySid": mySid,
                    "isSpine": sw.get("isSpine", False)
                }
            }
            self.switch_map[sw['name']] = self.addSwitch(
                sw['name'],
                cls=StratumBmv2Switch,
                cpuport=CPU_PORT
            )

    def _create_hosts(self, hosts,port_counters,netcfg):
        for host in hosts:
            sw_name = host["switch"]
            host_name = host["name"]
            h = self.addHost(
                host_name,
                cls=IPv6Host,
                ipv6=host['ipv6'],
                ipv6_gw=host['gateway'],
                mac=host['mac']
            )
            device_port_key = "device:{sw_name}/{port_num}".format(sw_name=sw_name,port_num=port_counters[sw_name])
            interface_name = "{sw_name}-{port_num}".format(sw_name=sw_name,port_num=port_counters[sw_name])
            port_counters[sw_name]+=1
            gateway = host["gateway"]
            if "/" not in gateway:
                gateway += "/64"
            netcfg["ports"][device_port_key] = {
                "interfaces": [
                    {
                        "name": interface_name,
                        "ips": [gateway]
                    }
                ]
            }
            host_key = "{host}/None".format(host=host['mac'])
            netcfg["hosts"][host_key] = {
                "basic": {
                    "name": host["name"]
                }
            }
            print(host_name, host['switch'])
            self.addLink(h, self.switch_map[host['switch']],bw=host['bw'])

    def _create_links(self, links,port_counters):
        for link in links:
            sw1, sw2,bw = link
            port_counters[sw1] = port_counters.get(sw1,1)+1
            port_counters[sw2] = port_counters.get(sw2,1)+1
            print(sw1, sw2)
            self.addLink(self.switch_map[sw1], self.switch_map[sw2],bw=bw)



def main():
    net = Mininet(topo=TutorialTopo(), controller=None, link=TCLink)
    net.start()
    CLI(net)
    net.stop()
    print '#' * 80
    print 'ATTENTION: Mininet was stopped! Perhaps accidentally?'
    print 'No worries, it will restart automatically in a few seconds...'
    print 'To access again the Mininet CLI, use `make mn-cli`'
    print 'To detach from the CLI (without stopping), press Ctrl-D'
    print 'To permanently quit Mininet, use `make stop`'
    print '#' * 80


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Mininet topology script for 2x2 fabric with stratum_bmv2 and IPv6 hosts')
    args = parser.parse_args()
    setLogLevel('info')

    main()
