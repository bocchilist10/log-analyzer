#csvモジュールインポート
import csv

#テスト
start_line = 1
end_line = 4

#python標準ライブラリ
#collectionsの中にあるdefauldict        dictよりも安全に使える
from collections import defaultdict

#intでゼロを設定し初期化　キーが未登録でも0で初期化
ip_counter = defaultdict(int)

#ファイルの読み込み
with open("output.csv", newline="", encoding="utf-8", errors="ignore") as f:
    #readerは1行ずつリストのような値を返す
    reader = csv.reader(f)
    #ヘッダーをスキップ
    next(reader)


    try:
        for line_number, row in enumerate(reader, start=1):
            # if start_line <= line_number <= end_line:
            #     print(line_number,row) 
                ip = row[0]
                status = row[4]
                if status == "503":
                    ip_counter[ip] += 1
    except Exception as e:
        print(F"処理失敗: 行目,{line_number}→{row[:50]}→{e}")

# 外部ファイルへの出力
with open("503_count.csv", "w", newline="", encoding="utf-8") as out:
     writer = csv.writer(out)
     writer.writerow(["ip", "appear"])

     for ip, count in ip_counter.items():

          writer.writerow([ip, count])
