import json
import matplotlib.pyplot as plt
import os
from datetime import datetime, timezone, timedelta
import sys
import glob
import re
import collections
import numpy as np

def parse_qlog(qlog_file):
    """
    単一のqlogファイルをパースして、RTTとLoss Eventの時系列データを抽出する。
    """
    try:
        with open(qlog_file, "r", encoding="utf-8") as f:
            qlog = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading or parsing {qlog_file}: {e}")
        return [], [], [], []

    rtt_times = []
    rtt_values = []  # latest_rtt を使用

    LOSS_GROUPING_INTERVAL_SECONDS = 2
    loss_counts = collections.defaultdict(int)

    for trace in qlog.get("traces", []):
        ref_time = int(trace.get("common_fields", {}).get("reference_time", 0))
        for event in trace.get("events", []):
            if len(event) < 4:
                continue

            rel_time, category, event_name, data = event
            
            abs_time_us = ref_time + rel_time
            abs_time_s = abs_time_us / 1e6
            time_jst = datetime.fromtimestamp(abs_time_s, tz=timezone(timedelta(hours=9)))

            if category == "recovery" and event_name == "metrics_updated":
                if "latest_rtt" in data:
                    rtt_times.append(time_jst)
                    rtt_values.append(data["latest_rtt"] / 1000)  # µs -> ms

            if category == "recovery" and event_name == "packet_lost":
                base_timestamp_s = int(time_jst.timestamp())
                grouped_timestamp_s = (base_timestamp_s // LOSS_GROUPING_INTERVAL_SECONDS) * LOSS_GROUPING_INTERVAL_SECONDS
                grouping_time = datetime.fromtimestamp(grouped_timestamp_s, tz=timezone(timedelta(hours=9)))
                loss_counts[grouping_time] += 1

    if loss_counts:
        sorted_losses = sorted(loss_counts.items())
        loss_times, loss_events = zip(*sorted_losses)
    else:
        loss_times, loss_events = [], []

    return rtt_times, rtt_values, list(loss_times), list(loss_events)

def plot_combined_data(rtt_times, rtt_values, loss_times, loss_events, output_file):
    """
    結合されたデータから2段グラフをプロットし、画像として保存する。
    """
    if not rtt_times:
        print("No RTT data to plot.")
        return

    first_time_abs = min(rtt_times)
    last_time_abs = max(rtt_times)

    rtt_times_rel = [(t - first_time_abs).total_seconds() for t in rtt_times]
    loss_times_rel = [(t - first_time_abs).total_seconds() for t in loss_times]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

    ax1.scatter(rtt_times_rel, rtt_values, s=2, label="Victoria", color="blue", marker='.')
    ax1.set_ylabel("RTT (ms)")
    
    # --- ▼ここから変更点▼ ---
    # RTTのy軸の表示範囲を 0-500 ms に固定する
    ax1.set_ylim(bottom=0, top=500)
    # --- ▲ここまで変更点▲ ---

    ax2.scatter(loss_times_rel, loss_events, marker='x', label="Loss Event", color="saddlebrown")
    ax2.set_ylabel("Loss Events")
    ax2.set_xlabel("Time (s)")

    offsets = [12, 27, 42, 57]  
    interval = 15

    try:
        first_handover_abs = min(
            dt for dt in [first_time_abs.replace(second=o, microsecond=0) for o in offsets]
            if dt >= first_time_abs
        )
    except ValueError:
        next_minute = (first_time_abs + timedelta(minutes=1)).replace(second=0, microsecond=0)
        first_handover_abs = min(
            dt for dt in [next_minute.replace(second=o, microsecond=0) for o in offsets]
        )

    handover_times_abs = []
    t = first_handover_abs
    while t <= last_time_abs:
        handover_times_abs.append(t)
        t += timedelta(seconds=interval)
        
    handover_times_rel = [(t - first_time_abs).total_seconds() for t in handover_times_abs]
        
    for ax in [ax1, ax2]:
        for i, ho_time in enumerate(handover_times_rel):
            label = "Handover" if i == 0 else ""
            ax.axvline(x=ho_time, color='purple', linestyle='--', linewidth=1.2, label=label)

    ax1.legend(loc='upper left')
    ax2.legend(loc='upper left')
    
    ax1.set_xlim(left=0)
    ax2.set_xlim(left=0)

    ax1.grid(True, linestyle=':', alpha=0.6)
    ax2.grid(True, linestyle=':', alpha=0.6)
    fig.tight_layout()
    
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Combined plot saved to: {output_file}")


def main(qlog_dir, output_dir, file_prefix, max_files_to_process=None):
    """
    指定されたディレクトリからqlogファイルを処理し、結合されたグラフを生成する。
    
    Args:
        qlog_dir (str): qlogファイルが格納されているディレクトリ。
        output_dir (str): 生成されたグラフを保存するディレクトリ。
        file_prefix (str): 処理するqlogファイルのプレフィックス (例: "client", "server")。
        max_files_to_process (int, optional): 処理するファイルの最大数。Noneの場合は全て処理する。
    """
    file_pattern = os.path.join(qlog_dir, f"{file_prefix}*.qlog")
    qlog_files = glob.glob(file_pattern)

    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]
    qlog_files.sort(key=natural_sort_key)

    if max_files_to_process is not None:
        qlog_files_to_process = qlog_files[:max_files_to_process]
    else:
        qlog_files_to_process = qlog_files
            
    if not qlog_files_to_process:
        print(f"No files matching pattern '{file_pattern}' found to process.")
        return
        
    print(f"Found {len(qlog_files_to_process)} qlog files to process:")
    for f in qlog_files_to_process:
        print(f" - {os.path.basename(f)}")

    all_rtt_times, all_rtt_values, all_loss_times, all_loss_events = [], [], [], []

    for qlog_file in qlog_files_to_process:
        print(f"Processing '{os.path.basename(qlog_file)}'...")
        rtt_times, rtt_values, loss_times, loss_events = parse_qlog(qlog_file)
        all_rtt_times.extend(rtt_times)
        all_rtt_values.extend(rtt_values)
        all_loss_times.extend(loss_times)
        all_loss_events.extend(loss_events)

    if all_rtt_times:
        sorted_rtt = sorted(zip(all_rtt_times, all_rtt_values))
        all_rtt_times, all_rtt_values = zip(*sorted_rtt)

    if all_loss_times:
        sorted_loss = sorted(zip(all_loss_times, all_loss_events))
        all_loss_times, all_loss_events = zip(*sorted_loss)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
    dir_name = os.path.basename(os.path.normpath(qlog_dir))
    
    num_files_str = f"_{max_files_to_process}" if max_files_to_process is not None else "_all"
    output_file = os.path.join(output_dir, f"{dir_name}_combined{num_files_str}_{timestamp_str}.png")

    plot_combined_data(
        list(all_rtt_times) if all_rtt_times else [],
        list(all_rtt_values) if all_rtt_values else [],
        list(all_loss_times) if all_loss_times else [],
        list(all_loss_events) if all_loss_events else [],
        output_file
    )

if __name__ == "__main__":
    max_files = None
    if len(sys.argv) > 1:
        try:
            max_files = int(sys.argv[1])
            print(f"Processing up to {max_files} files for each prefix.")
        except ValueError:
            print(f"Invalid number '{sys.argv[1]}'. Processing all files.", file=sys.stderr)
            max_files = None
    else:
        print("No file limit specified. Processing all files.")

    client_qlog_dir = "../log/client/picoquic_leo/slogs"
    client_output_dir = "log_img/client"

    server_qlog_dir = "../log/server/slogs"
    server_output_dir = "log_img/server"

    main(client_qlog_dir, client_output_dir, "client", max_files_to_process=max_files)
    main(server_qlog_dir, server_output_dir, "server", max_files_to_process=max_files)