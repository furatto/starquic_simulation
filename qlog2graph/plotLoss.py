import json
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from collections import Counter
import os
import sys

def plot_loss_points_count(qlog_file):
    # JSTタイムゾーン
    JST = timezone(timedelta(hours=9))

    with open(qlog_file, "r", encoding="utf-8") as f:
        qlog = json.load(f)

    trace = qlog["traces"][0]
    events = trace["events"]
    ref_time_us = int(trace["common_fields"]["reference_time"])

    # loss events 時刻リスト
    loss_times = []

    for ev in events:
        rel_time_us, category, event_name, data = ev
        if event_name == "packet_lost":
            abs_time_us = ref_time_us + rel_time_us
            ts = datetime.fromtimestamp(abs_time_us / 1e6, tz=timezone.utc).astimezone(JST)
            loss_times.append(ts)

    if not loss_times:
        print("パケットロスイベントは見つかりませんでした。")
        return

    # 1秒単位で集計
    times_sec = [t.replace(microsecond=0) for t in loss_times]
    counts = Counter(times_sec)
    times_sorted = sorted(counts.keys())
    values = [counts[t] for t in times_sorted]

    # 赤線リスト（例: 12, 27, 42, 57秒に15秒間隔で）
    offsets = [12, 27, 42, 57]
    interval = 15
    first_time = times_sorted[0]
    last_time = times_sorted[-1]

    first_red_line = min(
        dt for dt in [first_time.replace(second=o, microsecond=0) for o in offsets]
        if dt >= first_time
    )

    red_line_dt = []
    t = first_red_line
    while t <= last_time:
        red_line_dt.append(t)
        t += timedelta(seconds=interval)

    # プロット
    plt.figure(figsize=(12,6))

    # 赤線描画
    for dt in red_line_dt:
        plt.axvline(x=dt, color='r', linestyle='--', linewidth=1)

    # 点プロット
    plt.scatter(times_sorted, values, color="blue", s=30, marker="x")  # sで点の大きさ調整
    plt.xlabel("Time (JST)")
    plt.ylabel("Loss Events per Second")
    plt.title("Packet Loss Events (1-second count)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 出力ディレクトリ
    base_name = os.path.basename(qlog_file)
    file_root, _ = os.path.splitext(base_name)
    output_file = os.path.join("log_img", file_root + "_loss.png")

    plt.savefig(output_file)
    print(f"グラフを保存しました: {output_file}")
    plt.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plotLoss.py <qlog_file>")
        sys.exit(1)

    qlog_file = sys.argv[1]
    plot_loss_points_count(qlog_file)
