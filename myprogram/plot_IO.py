# 必要なライブラリをインストールします
# !pip install scapy matplotlib

import matplotlib.pyplot as plt
from scapy.all import rdpcap
from collections import defaultdict
import os
import matplotlib.dates as mdates
from datetime import datetime
from zoneinfo import ZoneInfo

def create_io_graph_with_periodic_lines_datetime(pcap_path, output_image_path, offsets=[12,27,42,57], interval=15):
    """
    pcap内のI/Oグラフを生成し、
    pcapの開始時刻に最も近い offsets の秒から周期的に赤い縦線を描画。
    x軸は HH:MM:SS 表示。

    Args:
        pcap_path (str): 入力pcapファイルのパス
        output_image_path (str): 出力画像ファイルのパス
        offsets (list[int]): 0-59秒の候補（例: [12,27,42,57]）
        interval (int): 赤線の周期（秒）
    """
    if not os.path.exists(pcap_path):
        print(f"エラー: ファイルが見つかりません - {pcap_path}")
        return

    try:
        packets = rdpcap(pcap_path)
    except Exception as e:
        print(f"pcapファイルの読み込み中にエラーが発生しました: {e}")
        return

    if not packets:
        print("pcapファイルにパケットが含まれていません。")
        return

    # pcapの開始・終了時刻（UNIXタイム）
    first_time = int(packets[0].time)
    last_time  = int(packets[-1].time)

    # 1秒ごとのパケット数
    packets_per_second = defaultdict(int)
    for pkt in packets:
        t = int(pkt.time)
        packets_per_second[t] += 1

    x_values = list(range(first_time, last_time + 1))
    y_values = [packets_per_second.get(t, 0) for t in x_values]

    # --- 最初の赤線を決定 ---
    sec_of_minute = first_time % 60
    closest_offset = min(offsets, key=lambda x: abs(x - sec_of_minute))
    first_red_line = first_time - sec_of_minute + closest_offset
    if first_red_line < first_time:
        first_red_line += 60

    # 赤線リストを生成
    red_line_times = list(range(first_red_line, last_time + 1, interval))

    # --- 日時表示用に変換 ---
    jst = ZoneInfo("Asia/Tokyo")
    x_values_dt = [datetime.fromtimestamp(ts, tz=jst) for ts in x_values]
    red_line_dt = [datetime.fromtimestamp(ts, tz=jst) for ts in red_line_times]
    plt.figure(figsize=(15, 5))
    plt.plot(x_values_dt, y_values, label="Packets/Second", linewidth=1.0)

    for dt in red_line_dt:
        plt.axvline(x=dt, color='r', linestyle='--', linewidth=1)

    # x軸を HH:MM:SS 表示
    formatter = mdates.DateFormatter('%H:%M:%S', tz=jst)
    plt.gca().xaxis.set_major_formatter(formatter)
    plt.gcf().autofmt_xdate()  # ラベルを斜めにして重なり防止

    plt.title("I/O Graph (Periodic Red Lines, HH:MM:SS)")
    plt.xlabel("Time (HH:MM:SS)")
    plt.ylabel("Packets per Second")
    plt.grid(True)
    plt.legend()

    try:
        plt.savefig(output_image_path)
        print(f"グラフを {output_image_path} として保存しました。")
    except Exception as e:
        print(f"グラフの保存中にエラーが発生しました: {e}")


# --- 設定 ---
pcap_file = 'pcap_logs/client_9.pcap'
output_image = 'log_img/io_graph_client_9_1.png'
interval = 15  # 赤線の周期（秒）

create_io_graph_with_periodic_lines_datetime(pcap_file, output_image, offsets=[12,27,42,57], interval=interval)
