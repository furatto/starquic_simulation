import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta

# CSVファイルのパス
csv_path = "csv_logs/a0bb2.client.csv"
output_image_path = "log_img/rtt_graph_jst.png"

# CSV読み込み
df = pd.read_csv(csv_path)

# time列を日本時間のdatetimeに変換
# time が秒単位である場合
df['time_sec'] = df['time'] / 1_000_000
# RTT列（例: rtt-sample）を使用

# グラフ作成
plt.figure(figsize=(12, 5))
plt.plot(df['time_sec'], df[' one-way-delay'], label='one-way-delay', alpha=0.4)
plt.plot(df['time_sec'], df[' RTT min'], marker='.', linestyle='-', label="minRTT",alpha=0.6)
plt.plot(df['time_sec'], df[' SRTT'], label='SRTT', alpha=0.8)
plt.plot(df['time_sec'], df[' bw_max'], label='bw_max', alpha=1.0)

# 軸ラベルとタイトル
plt.xlabel("Time")
plt.ylabel("RTT (μs)")  # 単位がマイクロ秒の場合
plt.grid(True)
plt.legend()
plt.tight_layout()

try:
    plt.savefig(output_image_path)
    print(f"グラフを {output_image_path} として保存しました。")
except Exception as e:
    print(f"グラフの保存中にエラーが発生しました: {e}")