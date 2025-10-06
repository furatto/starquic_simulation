import pandas as pd

# CSVファイルの読み込み（tsharkで出力したもの）
# CSV形式: frame_time, packet_number, src, dst
# 例: "2025-10-06 01:00:00.123456", 1, "10.0.0.1", "10.0.0.2"
csv_file = "quic_packets.csv"
df = pd.read_csv(csv_file, names=["time", "packet_number", "src", "dst"])

# packet_numberを整数に
df["packet_number"] = df["packet_number"].astype(int)

# 並び替え（念のためフレーム時間順）
df = df.sort_values("time").reset_index(drop=True)

# パケロス検出用リスト
lost_packets = []

# 前のパケット番号
prev_packet = None

for idx, row in df.iterrows():
    if prev_packet is not None:
        gap = row["packet_number"] - prev_packet
        if gap > 1:
            # 欠番がある場合、パケロスとして記録
            for lost in range(prev_packet + 1, row["packet_number"]):
                lost_packets.append({
                    "lost_packet_number": lost,
                    "time_after": row["time"],
                    "src": row["src"],
                    "dst": row["dst"]
                })
    prev_packet = row["packet_number"]

# 結果をDataFrameにして表示
lost_df = pd.DataFrame(lost_packets)
print("=== パケロス検出結果 ===")
print(lost_df)

# CSVに出力する場合
lost_df.to_csv("quic_packet_loss.csv", index=False)
