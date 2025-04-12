import json
import os
import pty
import re
import subprocess
import sys
import time

import pexpect


class Service:

    def get_hosts(self):
        with open("mininet/topo.json") as f:
            topo_config = json.load(f)
        hosts=[]
        for host in topo_config['hosts']:
            hosts.append(host["name"])
        return hosts

    def get_switches(self):
        with open("mininet/topo.json") as f:
            topo_config = json.load(f)
        hosts = []
        for host in topo_config['switches']:
            hosts.append(host["name"])
        return hosts

    def ping(self,client_host,server_host):
        try:
            time.sleep(3)
            os.write(self.mn_master, f"{client_host} ping6 -w 3 {server_host}\r\n".encode())  #
            time.sleep(3)

            # 读取子进程的输出
            full_output = ""
            rtt_match = None

            for i in range(3):
                try:
                    data = os.read(self.mn_master, 1024).decode()
                    if not data:
                        break
                    full_output += data
                    print(data, end="")  # 实时打印输出

                    # 解析 RTT（延迟）信息
                    rtt_match = re.search(r'rtt min/avg/max/mdev = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms',
                                          full_output)
                    if rtt_match:
                        avg_rtt = float(rtt_match.group(2))  # 提取平均 RTT（avg）
                        print(f"\n解析出的平均 RTT: {avg_rtt} ms")
                        break  # 匹配到 RTT 后跳出循环
                    elif '100% packet loss' in full_output:
                        return full_output

                except OSError:
                    break
                time.sleep(2)
                os.write(self.mn_master, f"{client_host} ping6 -w 3 {server_host}\r\n".encode())

            # 如果匹配到了带宽信息，打印结果
            if rtt_match:
                # 如果匹配到 RTT 信息，返回 RTT
                avg_rtt = float(rtt_match.group(2))
                return json.dumps({"avg_rtt": avg_rtt})

            else:
                return full_output
        except KeyboardInterrupt:
            print("Exiting...")

    def iperf(self, client_host, server_host):
        try:
            time.sleep(3)
            os.write(self.mn_master, f"{server_host} iperf -s -V &\r\n".encode())  #
            time.sleep(1)
            os.write(self.mn_master, f'{client_host}  iperf -c {server_host} -V -t 3 \r\n'.encode())  #
            # time.sleep(5)

            # 读取子进程的输出
            full_output = ""
            bandwidth_match = None

            for i in range(3):
                try:
                    data = os.read(self.mn_master, 1024).decode()
                    if not data:
                        break
                    full_output += data
                    print(data, end="")  # 实时打印输出

                    # 解析带宽信息
                    bandwidth_match = re.search(r'(\d+(?:\.\d+)?)\s+([MG])bits/sec', full_output)
                    if bandwidth_match:
                        break  # 匹配到带宽后立即跳出循环

                except OSError:
                    break
                time.sleep(2)
                os.write(self.mn_master, f'{client_host}  iperf -c {server_host} -V -t 3 \r\n'.encode())

                # 如果匹配到了带宽信息，打印结果
            if bandwidth_match:
                bandwidth_value = float(bandwidth_match.group(1))
                bandwidth_unit = bandwidth_match.group(2)
                print(f"\n解析出的带宽: {bandwidth_value} {bandwidth_unit}bits/sec")
                return json.dumps({"bandwidth_value": bandwidth_value, "bandwidth_unit": bandwidth_unit})
            else:
                return full_output
        except KeyboardInterrupt:
            print("Exiting...")

    def create(self,log,data):
        restart_result = subprocess.run(
            ['make', 'restart'],
            capture_output=True,
            text=True,
            check=True
        )
        log.info(restart_result)
        time.sleep(45)

        # 执行 make app-reload 命令
        reload_result = subprocess.run(
            ['make', 'app-reload'],
            capture_output=True,
            text=True,
            check=True
        )
        log.info(reload_result)
        time.sleep(3)

        netcfg_result = subprocess.run(
            ['make', 'netcfg'],
            capture_output=True,
            text=True,
            check=True
        )
        log.info(netcfg_result)
        time.sleep(3)

        self.mn_master, self.mn_slave = pty.openpty()
        self.onos_master, self.onos_slave = pty.openpty()
        command = ['make', 'mn-cli']
        self.mn_cli = subprocess.Popen(command, stdin=self.mn_slave, stdout=self.mn_slave, stderr=self.mn_slave, preexec_fn=os.setsid)
        time.sleep(3)
        for host in self.get_hosts():
            self.ping(host, "h1a")
        ssh_cmd = f'ssh -o "UserKnownHostsFile=/dev/null" -o "StrictHostKeyChecking=no" -o "HostKeyAlgorithms=+ssh-rsa" -o LogLevel=ERROR -p 8101 onos@localhost'
        child = pexpect.spawn(ssh_cmd, timeout=5, encoding='utf-8')

        # 启用实时日志（调试时使用）
        child.logfile = sys.stdout

        # 等待动态密码提示（兼容前缀和大小写）
        password_prompt = r'Password:'
        child.expect(password_prompt, timeout=5)

        # 输入密码
        child.sendline("rocks")

        # 等待ONOS CLI提示符（如 'onos> '）
        child.expect(r'onos@root >', timeout=5)
        self.onos_cli=child
        self.host_ip_map = {host["name"]: host["ipv6"].split("/")[0]for host in data["hosts"]}
        with open("./mininet/netcfg.json") as f:
            topo_config = json.load(f)
            self.device_sid_map = {
                # 分割键名，取"device:"后的部分作为新键（如"leaf1"）
                device.split(":")[1]: details["fabricDeviceConfig"]["mySid"]
                for device, details in topo_config["devices"].items()
            }

    def onos_insert(self,device,relay,destination,log):
        # 发送命令并等待输出
        self.onos_cli.sendline(f'srv6-insert device:{device} {self.device_sid_map[device]} {self.device_sid_map[relay]} {self.host_ip_map[destination]}\r\n')
        self.onos_cli.expect(r'onos@root >')  # 再次匹配提示符
        if self.device_srv6_map.get(device) is None:
            self.device_srv6_map[device] = {}
        self.device_srv6_map[device][destination] = relay


    def onos_query(self,device):
        return self.device_srv6_map[device]
    def onos_delete(self,device):
        os.write(self.onos_master,
                 f'srv6-clear device:{device}\r\n'.encode())
        self.device_srv6_map[device]={}
    def __init__(self):
        self.mn_master = None
        self.mn_cli = None
        self.onos_cli = None
        self.mn_master = None
        self.mn_slave = None
        self.onos_master = None
        self.onos_slave = None
        self.host_ip_map = None
        self.device_sid_map = None
        self.device_srv6_map = {}
