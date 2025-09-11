# csvモジュールのインポート
import csv

# ファイルの読み込み
with open("apache_access_log.txt") as f:

# 1行ごとの取り出し
# stripで空白改行の除去
    lines = [line.strip() for line in f] 
    #print(lines)

# csvファイルへの出力
# newlineで余計な空行の出力を防ぐ（特にWindows環境）
with open("output1.csv", "w", newline="") as csvfile:
    # csvファイルに行単位でデータを書き込むためのオブジェクトを生成
    writer = csv.writer(csvfile)
    #　1行目に項目の追加名（ヘッダー）を出力
    writer.writerow(["ip", "Date", "Method", "URL", "Status"]) # ヘッダー

    # 各行のデータを分解・抽出して書き込み
    for line in lines:
        parts = line.split() # スペース区切りで分割
        ip = parts[0]  # IPアドレス
        date = parts[3][1:] # 日時　先頭の"["を除去
        method = parts[5][1:] # リクエストメソッドを除去
        url = parts[6] # リクエストされたURL
        status = parts[-2] # ステータスコード（末尾から2番目）
        writer.writerow([ip, date, method, url, status]) # 書き込み
