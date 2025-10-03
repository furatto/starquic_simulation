from datetime import datetime, timedelta
from multiprocessing import Process
from mininet.cli import CLI
import numpy as np
import threading
import random
import time
import math
import csv
import re

from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.link import TCLink
import mininet.node

class NetworkConfigThread(threading.Thread):
    def __init__(self, net, host_name, dev, trace_path, step, column, line_number = 0):
        super().__init__()
        self.net = net
        self.host = net.get(host_name)
        self.dev = dev
        self.step = step
        self.column = column
        self.stop_event = threading.Event()

        self.trace_path = trace_path

        self.current_line_number = line_number

    def stop(self): self.stop_event.set()

    def join(self):
        threading.Thread.join(self)
        return self.current_line_number

    def set_bandwidth(self, bw, action = "change"):
        burst = int(math.ceil(bw))
        self.host.cmd(f'tc qdisc {action} dev {self.dev} root handle 1: tbf rate {bw}mbit burst 200k latency 50ms')

    def set_delay(self, delay, action = "change"):
        self.host.cmd(f'tc qdisc {action} dev {self.dev} parent 1:1 handle 10: netem delay {delay}ms')

    def get_bandwidth(self, lines): return float(lines[self.current_line_number][self.column - 2])

    def get_delay(self, lines): return float(lines[self.current_line_number][self.column])

    def run(self):
        with open(self.trace_path, 'r') as file:
            lines = list(csv.reader(file))

        # Initial bandwidth and delay
        self.set_bandwidth(self.get_bandwidth(lines), action = "replace")
        self.set_delay(self.get_delay(lines), action = "add")
        
        while not self.stop_event.is_set():

            # Current bandwith and delay
            self.set_delay(self.get_delay(lines))
            self.set_bandwidth(self.get_bandwidth(lines))
            
            self.current_line_number += 1
            self.current_line_number %= len(lines)
            
            time.sleep(self.step)

def link_interruption(node: mininet.node.Host, link: str, loss_rate: int):
    for intf in node.intfList():
        if intf.link and str(intf) == link:
            intfs = [intf.link.intf1, intf.link.intf2]
            intfs[0].config(loss = loss_rate)
            intfs[1].config(loss = loss_rate)

def sleep_until_ts(end):
    while True:
        now = time.time()
        diff = end - now

        if diff <= 0.0: break
        else: time.sleep(diff / 2.0)

def next_handover_ts():
    now = datetime.fromtimestamp(time.time())
    current_minute = now - timedelta(seconds = now.second, microseconds = now.microsecond)
    next_minute    = now + timedelta(minutes = 1)

    handovers = list(map(lambda x: timedelta(seconds = x), [12, 27, 42, 57]))

    for minute in [current_minute, next_minute]:
        for offset in handovers:
            candidate = minute + offset
            if now < candidate:
                return candidate.timestamp() 

    raise Exception("Could not calculate next handover.")

def handover_event(node: mininet.node.Host, trace_path):
    network_thread2 = NetworkConfigThread(net, 'r2', 'r2-eth1', trace_path, 0.1, 3)
    network_thread4 = NetworkConfigThread(net, 'r4', 'r4-eth0', trace_path, 0.1, 2)
    
    # TODO: wait until start of an interval

    network_thread2.start()
    network_thread4.start()

    while True:
        sleep_until_ts(next_handover_ts())

        stop_event = threading.Event()
        network_thread2.stop()
        network_thread4.stop()
        line2 = network_thread2.join()
        line4 = network_thread4.join()

        network_thread2 = NetworkConfigThread(net, 'r2', 'r2-eth1', trace_path, 0.1, 3, line2)
        network_thread4 = NetworkConfigThread(net, 'r4', 'r4-eth0', trace_path, 0.1, 2, line4)
        network_thread2.start()
        network_thread4.start()

        print("Handover event at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # loss_rate = random.choice([2, 3])
        # iface1 = "r2-eth0"
        # link_interruption(node, iface1, loss_rate) # iface1 = "r2-eth0"

def run_test(net, server_command, client_command):
    h1 = net.get("h1")
    h2 = net.get("h2")

    #CLI(net) #デバッグ用

    h1.sendCmd(server_command)

    start = time.time()
    h2.sendCmd(client_command)
    server_out = h1.waitOutput()
    duration = time.time() - start

    client_out = h2.waitOutput()

    print(f"Duration: {duration:.2f}")

    print ("Server#############")
    print (server_out)
    print ("Client#############")
    print (client_out)
    print ("###################")

    # for line in client_out.split("\n"):
    #     if line.startswith("Connection established."): print(line)

    #     print("Server#############")
    #     print(server_out)
    #     print("Client#############")
    #     print(client_out)
    #     print("###################")
    #     h1.sendCmd(f'xterm -title "node: h1 server" -hold -e "sh" &')
    #     h2.sendCmd(f'xterm -title "node: h2 client" -hold -e "sh" &')
    #     time.sleep(10)
    #     h1.sendInt()
    #     h2.sendInt()
    #     h1.waitOutput()
    #     h2.waitOutput()
    #     time.sleep(5)

#------------------------------------------------------------------------------------
def disable_checksum_offload(net):#チェックサムオフローディングの無効化(by gemini)
    """Disable checksum offloading on all hosts and routers."""
    for node in net.hosts:
        print(f"Disabling checksum offload on {node.name}")
        # node.intfList()はノードの全インターフェースをリストアップする
        for intf in node.intfList():
            # ループバック(lo)インターフェースは対象外
            if 'lo' not in intf.name:
                node.cmd(f'ethtool -K {intf.name} tx off rx off sg off')
#------------------------------------------------------------------------------------


def create_topology():
    setLogLevel('info')
    net = Mininet(link=TCLink)

    h1 = net.addHost('h1') # Server
    h2 = net.addHost('h2') # Client

    # Starlink path
    r1 = net.addHost('r1')
    r2 = net.addHost('r2')
    r4 = net.addHost('r4')

    linkopt_server = {'bw': 1000}
    linkopt_starlink = {'loss': 2}

    net.addLink(r1, h1, cls=TCLink, **linkopt_server)
    net.addLink(r1, r4, cls=TCLink, **linkopt_server)
    net.addLink(r4, r2, cls=TCLink, **linkopt_server)
    net.addLink(r2, h2, cls=TCLink, **linkopt_starlink)
    net.build()

    r1.cmd("ifconfig r1-eth0 0")
    r1.cmd("ifconfig r1-eth1 0")

    r1.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
    r1.cmd("echo 1 > /proc/sys/net/ipv4/conf/all/proxy_arp")

    r1.cmd("ifconfig r1-eth0 10.0.1.1 netmask 255.255.255.0")
    r1.cmd("ifconfig r1-eth1 10.0.2.1 netmask 255.255.255.0")
    
    r4.cmd("ifconfig r4-eth0 0")
    r4.cmd("ifconfig r4-eth1 0")

    r4.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
    r4.cmd("echo 1 > /proc/sys/net/ipv4/conf/all/proxy_arp")

    r4.cmd("ifconfig r4-eth0 10.0.2.4 netmask 255.255.255.0")
    r4.cmd("ifconfig r4-eth1 10.0.6.4 netmask 255.255.255.0")
    
    r2.cmd("ifconfig r2-eth0 0")
    r2.cmd("ifconfig r2-eth1 0")

    r2.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
    r2.cmd("echo 1 > /proc/sys/net/ipv4/conf/all/proxy_arp")

    r2.cmd("ifconfig r2-eth0 10.0.6.2 netmask 255.255.255.0")
    r2.cmd("ifconfig r2-eth1 10.0.4.2 netmask 255.255.255.0")
    
    r2.cmd("ip route add 10.0.1.0/24 via 10.0.6.4")
    
    r1.cmd("ip route add 10.0.4.0/24 via 10.0.2.4")
    
    r4.cmd("ip route add 10.0.1.0/24 via 10.0.2.1")
    r4.cmd("ip route add 10.0.4.0/24 via 10.0.6.2")

    h1.cmd("ifconfig h1-eth0 0")

    h2.cmd("ifconfig h2-eth0 0")

    h1.cmd("ifconfig h1-eth0 10.0.1.2 netmask 255.255.255.0")

    h2.cmd("ifconfig h2-eth0 10.0.4.3 netmask 255.255.255.0")

    h1.cmd("ip route add default scope global nexthop via 10.0.1.1 dev h1-eth0")

    h2.cmd("ip rule add from 10.0.4.3 table 1")
    
    h2.cmd("ip route add 10.0.6.0/24 dev h2-eth0 table 1")
    h2.cmd("ip route add 10.0.4.0/24 dev h2-eth0 table 1")
    h2.cmd("ip route add 10.0.2.0/24 dev h2-eth0 table 1")
    h2.cmd("ip route add 10.0.1.0/24 dev h2-eth0 table 1")
    
    h2.cmd("ip route add default scope global nexthop via 10.0.4.2 dev h2-eth0")
    
    #disable_checksum_offload(net) #追加

    h1.cmd('xterm -title "node: h2 monitoring" -hold -e "sudo bwm-ng" &')

    return net

if __name__ == '__main__':

    net = create_topology()

    change_latency_process = Process(target = handover_event, args = (net.get("r2"), '../Starlink-Emulator/victoria.csv',))
    change_latency_process.start()

    trace_path = '../Starlink-Emulator/victoria.csv'
    offset = 0
    n_tests = 10

    test_algo = "bbr"
    #test_server = "./build/picoquicdemo" # Modified
    test_server = "../picoquic_leo/build/picoquicdemo" # Unmodified

    server_log_path = "/tmp/server.log"
    server_command = f"{test_server} -l {server_log_path} -c ./auth/cert.pem -k ./auth/key.pem -1 -p 4434 -G {test_algo} -q ./build/slogs -w ./build/srv"
    client_command = "../picoquic/build/picoquicdemo -n eidetic -e 3 -T /dev/null -G bbr -q ../picoquic/build/slogs -o ../picoquic/build/out 10.0.1.2 4434 'data4.bin'"

    print("Server command:", server_command)
    print("Client command:", client_command)

    def run_tests():

        for i in range(n_tests):

            h2 = net.get("h2")
            dump_file = f"./log/tcpdump/client_{i}.pcap"
            h2.cmd(f"rm -f {dump_file}")
            h2.cmd(f"tcpdump -i h2-eth0 -w {dump_file} &")
            time.sleep(1)

            network_thread2 = NetworkConfigThread(net, 'r2', 'r2-eth1', trace_path, 0.1, 3, offset)
            network_thread4 = NetworkConfigThread(net, 'r4', 'r4-eth0', trace_path, 0.1, 2, offset)
            
            print(f"Test {i}: Waiting for initial handover... ")
            sleep_until_ts(next_handover_ts())
            print("Start.")

            network_thread2.start()
            network_thread4.start()

            run_test(net, server_command, client_command)

            network_thread2.stop()
            network_thread4.stop()
            network_thread2.join()
            network_thread4.join()

            h2.cmd("pkill tcpdump")
            time.sleep(1)

  
    test_process = threading.Thread(target = run_tests)
    test_process.start()
    test_process.join()

    net.get("h1").terminate()
    net.get("h2").terminate()
    change_latency_process.join()
    net.stop()