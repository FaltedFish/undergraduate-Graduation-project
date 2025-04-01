import subprocess
import pty
import os
import time

def interact_with_container(container_id):
    # 创建一个伪终端
    master, slave = pty.openpty()

    # 使用 subprocess 启动 docker attach 命令
    command = ['make', 'onos-cli']
    process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, preexec_fn=os.setsid)

    try:
        time.sleep(3)
        os.write(master, b'srv6-insert device:leaf1 3:201:2:: 3:102:2:: 2001:2:4::4\r\n')  #
        time.sleep(5)
    except KeyboardInterrupt:
            print("Exiting...")
    finally:
        process.terminate()




# 获取 Mininet 容器的 ID
container_id = subprocess.check_output(['docker-compose', 'ps', '-q', 'mininet'], text=True).strip()

# 进行交互式操作
interact_with_container(container_id)
