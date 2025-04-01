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
        os.write(master, f"{client_host} ping6 -w 3 {server_host}\r\n".encode())  #
        time.sleep(5)

        # 读取子进程的输出
        full_output = ""
        rtt_match = None

        while True:
            try:
                data = os.read(master, 1024).decode()
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

            except OSError:
                break

        # 如果匹配到了带宽信息，打印结果
        if rtt_match:
            # 如果匹配到 RTT 信息，返回 RTT
            avg_rtt = float(rtt_match.group(2))
            return avg_rtt
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
