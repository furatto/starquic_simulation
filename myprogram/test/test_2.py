from scapy.all import rdpcap, UDP
import os

# --- 設定 ---
pcap_file = "../pcap_logs/client_9.pcap"

if not os.path.exists(pcap_file):
    print(f"ファイルが存在しません: {pcap_file}")
    exit(1)

packets = rdpcap(pcap_file)
if not packets:
    print("pcap にパケットがありません。")
    exit(1)

print(f"{'Time':<20} {'Src:Dst':<15} {'SpinBit':<7} {'FirstByte':<10}")
print("-"*60)

# 接続方向ごとに最後の Spin Bit を保持
conn_dir_last_spin = {}  # key=(src,dst)

for pkt in packets:
    if not pkt.haslayer(UDP):
        continue
    udp = pkt[UDP]
    payload = bytes(udp.payload)
    if len(payload) < 1:
        continue

    first_byte = payload[0]
    if first_byte & 0x80 == 0:
        continue  # Short Header スキップ

    spin_bit = (first_byte & 0x20) >> 5
    conn = (udp.sport, udp.dport)

    last_spin = conn_dir_last_spin.get(conn)
    if last_spin is None or spin_bit != last_spin:
        print(f"{pkt.time:.6f} {udp.sport}:{udp.dport} SpinBit: {spin_bit}")
    conn_dir_last_spin[conn] = spin_bit
