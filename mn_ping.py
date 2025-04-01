import pickle
import re
import subprocess
import pty
import os
import time

def interact_with_container(container_id,server_host,client_host):
    # 创建一个伪终端
    master, slave = pty.openpty()

    # 使用 subprocess 启动 docker attach 命令
    command = ['make', 'mn-cli']
    process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, preexec_fn=os.setsid)

    try:
        time.sleep(3)
        os.write(master, f"{server_host} iperf -s -V &\r\n".encode())  #
        time.sleep(1)
        os.write(master, f'{client_host}  iperf -c {server_host} -V -t 3 \r\n'.encode())  #
        #time.sleep(5)

        # 读取子进程的输出
        full_output = ""
        bandwidth_match = None

        while True:
            try:
                data = os.read(master, 1024).decode()
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

        # 如果匹配到了带宽信息，打印结果
        if bandwidth_match:
            bandwidth_value = float(bandwidth_match.group(1))
            bandwidth_unit = bandwidth_match.group(2)
            print(f"\n解析出的带宽: {bandwidth_value} {bandwidth_unit}bits/sec")
            return bandwidth_value, bandwidth_unit
        else:
            return full_output
    except KeyboardInterrupt:
            print("Exiting...")

    finally:
        process.terminate()

# 获取 Mininet 容器的 ID
container_id = subprocess.check_output(['docker-compose', 'ps', '-q', 'mininet'], text=True).strip()
# 进行交互式操作
interact_with_container(container_id,"leaf1","leaf2")
