import json
import matplotlib.pyplot as plt
import os
from datetime import datetime, timezone, timedelta
import sys

def rtt_from_qlog(qlog_file):
    with open(qlog_file, "r", encoding="utf-8") as f:
        qlog = json.load(f)

    # 各RTT項目を格納する辞書
    rtt_data = {
        "smoothed_rtt": [],
        "latest_rtt": [],
        "min_rtt": [],
    }
    time_list = []

    # traces → eventsを順に走査
    for trace in qlog.get("traces", []):
        ref_time = int(trace.get("common_fields", {}).get("reference_time", 0))  # µs
        for event in trace.get("events", []):
            if len(event) < 4:
                continue

            rel_time, category, event_name, data = event
            if category == "recovery" and event_name == "metrics_updated":
                # JST時間計算
                abs_time_us = ref_time + rel_time
                abs_time_s = abs_time_us / 1e6
                time_jst = datetime.fromtimestamp(abs_time_s, tz=timezone(timedelta(hours=9)))
                time_list.append(time_jst)

                # 各rtt値を取り出し（存在するものだけ）
                for key in rtt_data.keys():
                    if key in data:
                        rtt_data[key].append(data[key] / 1000)  # µs→ms
                    else:
                        # 値が無い場合、直前の値を引き継ぎ
                        rtt_data[key].append(rtt_data[key][-1] if rtt_data[key] else None)

    if not time_list:
        print("No RTT data found in qlog.")
        return

    offsets = [12, 27, 42, 57]  
    interval = 15
    first_time = time_list[0]
    last_time = time_list[-1]

    sec_of_minute = first_time.second + first_time.microsecond / 1e6
    closest_offset = min(offsets, key=lambda x: abs(x - sec_of_minute))

    first_red_line = min(
    dt for dt in [first_time.replace(second=o, microsecond=0) for o in offsets]
    if dt >= first_time
    )


    # 赤線リスト
    red_line_dt = []
    t = first_red_line
    while t <= last_time:
        red_line_dt.append(t)
        t += timedelta(seconds=interval)

    # === プロット ===
    plt.figure(figsize=(12, 6))
    colors = {"smoothed_rtt": "blue", "latest_rtt": "orange", "min_rtt": "green"}
    linestyles = {"smoothed_rtt": "-", "latest_rtt": "--", "min_rtt": ":"}

    # 赤線描画
    for dt in red_line_dt:
        plt.axvline(x=dt, color='r', linestyle='--', linewidth=1)

    for key in rtt_data:
        values = rtt_data[key]
        if any(v is not None for v in values):
            plt.scatter(time_list, values, s=2, label=key, alpha=0.6,
                     color=colors[key], linestyle=linestyles[key])

    plt.title("RTT over Time (JST)")
    plt.xlabel("Time (JST)")
    plt.ylabel("RTT (ms)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # 出力ディレクトリ作成
    base_name = os.path.basename(qlog_file)
    file_root, _ = os.path.splitext(base_name)
    output_file = os.path.join("log_img/", file_root + ".png")

    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ RTTプロット完了: {output_file}")

# メイン処理 （コマンドライン引数でqlogファイル指定）
if __name__ == "__main__":
    args = sys.argv
    if len(args) > 1:
        qlog_file = args[1]
        rtt_from_qlog(qlog_file)
    else:
        print("Usage: python plotRTT.py <qlog_file>")
