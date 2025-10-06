import pandas as pd
import matplotlib.pyplot as plt

# CSVファイルを読み込みます
# ファイルのパスは適宜変更してください
df = pd.read_csv('csv_logs/a0bb2.client.csv')

# 'time'列をマイクロ秒から秒に変換し、datetimeオブジェクトに変換します
df['time'] = pd.to_datetime(df['time'], unit='us')

# 'time'列をインデックスに設定します
df.set_index('time', inplace=True)

# 1秒ごとにパケット数をカウント（リサンプリング）します
packets_per_second = df.resample('s').size()

# グラフを作成します
plt.figure(figsize=(12, 6))
packets_per_second.plot()

# グラフのタイトルとラベルを設定します
plt.title('Packets per Second over Time')
plt.xlabel('Time')
plt.ylabel('Packets per Second')
plt.grid(True)

# グラフを画像ファイルとして保存します
plt.savefig('log_img/io_graph_csv_client9.png')