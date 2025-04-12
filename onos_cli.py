import pexpect

import sys

# 配置参数
host = 'localhost'  # 替换为实际IP
port = '8101'
username = 'karaf'  # ONOS默认用户
password = 'rocks'
command = 'apps -a -s'  # 要执行的命令
timeout = 30  # 超时时间

try:
    # 启动SSH连接（忽略主机密钥检查）
    ssh_cmd = f'ssh -o "UserKnownHostsFile=/dev/null" -o "StrictHostKeyChecking=no" -o "HostKeyAlgorithms=+ssh-rsa" -o LogLevel=ERROR -p 8101 onos@localhost'
    child = pexpect.spawn(ssh_cmd, timeout=timeout, encoding='utf-8')

    # 启用实时日志（调试时使用）
    child.logfile = sys.stdout

    # 等待动态密码提示（兼容前缀和大小写）
    password_prompt = r'Password:'
    child.expect(password_prompt, timeout=5)

    # 输入密码
    child.sendline("rocks")

    # 等待ONOS CLI提示符（如 'onos> '）
    child.expect(r'onos@root >', timeout=timeout)

    # 发送命令并等待输出
    child.sendline(command)
    child.expect(r'onos@root >')  # 再次匹配提示符

    # 获取命令输出（剔除命令回显和提示符）
    output = child.before.strip()
    print(f"\n命令输出：\n{output}")

    # 退出
    child.sendline('exit')
    child.expect(pexpect.EOF)

except pexpect.EOF:
    print("错误：连接意外终止（检查密码或网络）")
except pexpect.TIMEOUT:
    print("错误：操作超时（请增大 timeout 参数）")
except Exception as e:
    print(f"未知错误：{e}")
finally:
    if 'child' in locals():
        child.close()