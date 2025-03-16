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

        self._create_switches(topo_config['switches'])
        self._create_links(topo_config['links'])
        self._create_hosts(topo_config['hosts'])


    def _create_switches(self, switches):
        self.switch_map = {}
        for sw in switches:
            self.switch_map[sw['name']] = self.addSwitch(
                sw['name'],
                cls=StratumBmv2Switch,
                cpuport=CPU_PORT
            )

    def _create_hosts(self, hosts):
        for host in hosts:
            h = self.addHost(
                host['name'],
                cls=IPv6Host,
                ipv6=host['ipv6'],
                ipv6_gw=host['gateway'],
                mac=host['mac']
            )
            self.addLink(h, self.switch_map[host['switch']])

    def _create_links(self, links):
        for link in links:
            sw1, sw2 = link
            self.addLink(self.switch_map[sw1], self.switch_map[sw2])



def main():
    net = Mininet(topo=TutorialTopo(), controller=None)
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
