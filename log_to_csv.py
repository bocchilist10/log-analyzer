# csvモジュールのインポート
import csv

#テストで表示させる行数
start_line = 1
end_line = 4


#　ファイルの読み込み
with open("ddos_sample_log.txt", encoding="utf-8", errors="ignore") as f:
    #1行ごとの取り出し、空白と改行の削除
    lines = [line.strip() for line in f]
    # for i, line in enumerate(lines, start=1):
    #     if i >= 3:
    #         break
    #     print(line)
    #for line_test in lines[:3]:
        #print(line_test)
    #enumerate()を使用する方法
    #リストやファイルなどの要素を１つずつ処理しながら、「何番目か（インデックス）」も一緒に取り出せる関数
    #基本構文　for index, value in enumerate(コレクション, start=0):
    #index → 0から順に数える番号（行番号や順番）value → 実際の中身（リストの要素やファイルの行など）start= で開始番号を変えることも可能（1始まりなど）


with open("output.csv", "w", newline="", encoding="utf-8") as csvfile:
    #ヘッダー情報の追加
    writer = csv.writer(csvfile)
    #ヘッダーへの追加
    writer.writerow(["ip", "Date", "Method", "url", "Status", "Size"])

    # エラーを回避しての行の取り出し
    for line_nnumber, line in enumerate(lines, start=1):
        try:
            #if start_line <= line_nnumber <= end_line:
                 parts = line.strip().split()
                 #print(f"[{line_nnumber}行目] parts →", parts)
                 ip = parts[0]
                 date = parts[3][1:] + " " + parts[4][:-1]
                 method = parts[5][1:]
                 url = parts[6]
                 status = parts[-2]
                 size = parts[-1]
                 writer.writerow([ip, date, method, url, status, size,])                
        #エラーの出力
        except Exception as e:
            print(F"処理失敗: 行目,{line_nnumber}→{line[:50]}→{e}")