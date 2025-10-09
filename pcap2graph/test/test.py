from scapy.all import rdpcap, UDP
import os
from decimal import Decimal

# --- 設定 ---
pcap_file = "../pcap_logs/client_9.pcap"

if not os.path.exists(pcap_file):
    print(f"ファイルが存在しません: {pcap_file}")
    exit(1)

packets = rdpcap(pcap_file)
if not packets:
    print("pcap にパケットがありません。")
    exit(1)

print(f"{'Time':<15} {'Src:Dst':<15} {'FirstByte':<10} {'SpinBit':<7}")
print("-"*50)

for pkt in packets:
    if not pkt.haslayer(UDP):
        continue
    udp = pkt[UDP]
    payload = bytes(udp.payload)
    if len(payload) < 1:
        continue

    # 先頭バイトと Spin Bit 抽出
    first_byte = payload[0]
    spin_bit = (first_byte & 0x20) >> 5  # RFC9000: Long Header の 6th ビット

    # タイムスタンプの float化
    ts = float(pkt.time)

    # 出力
    print(f"{ts:<15.6f} {udp.sport}:{udp.dport:<10} {first_byte:<10} {spin_bit:<7}")
