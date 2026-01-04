# 標準ライブラリのインポート
from pathlib import Path # Pathの操作
from email import policy # 文字のエンコードやヘッダー処理を自動化
from email.parser import BytesParser # バイナリデータを読み取る 
from email.utils import parseaddr # メールアドレスの分割
from email.header import decode_header # デコード
from datetime import timezone, timedelta # 日付と時刻
import email.utils
import csv # CSVの操作
import re # 正規表現
import ipaddress # IPアドレス


# 現在のスクリプトの親フォルダを取得
BASE_PATH = Path(__file__).parent

# IPv4の正規表現(簡易)
IPV4_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")

# デコード
def decode_mime_header(value: str) -> str:
    """=?UTF-8?...?= のようなMIMEエンコードヘッダをデコードして文字化けを直す"""
    # 空文字なら空文字で返す
    if not value:
        return ""
    # MIMEヘッダーを分解（本文、文字エンコード）
    parts = decode_header(value)
    # デコード結果を順番にためる
    out = []
    # パーツ毎に処理
    for text, charset in parts:
        # byteかの判定 byteならデコードが必要
        if isinstance(text, bytes):
            # 合致したエンコードを追加
            candidates = []
            # デコード候補の作成
            if charset:
                # 元のものがあればそれを優先
                candidates.append(charset)
                # なければ日本語でありそうなものを追加 適宜追加
            candidates += ["utf-8", "iso-2022-jp", "cp932", "latin-1"] # 日本語でありそうなエンコード群
            # 候補を順番に試して、成功したらそのまま追加
            for enc in candidates:
                try:
                    out.append(text.decode(enc))
                    break
                except Exception:
                    continue
            # 合致したエンコードがなければutf-8で置換し、ひし形で置換
            else:
                out.append(text.decode("utf-8", errors="replace")) # errors="replace" ひし形に強制置換する
        # テキストならそのまま
        else:
            out.append(text)
    # 元の文字列に戻して返す
    return "".join(out)

# メールアドレスのドメインを取得
def get_domain(addr: str) -> str:
    # 最後の@以降を返すためリストの最後を取得-1で最後の値
    return addr.split("@")[-1].lower() if "@" in addr else ""

# received内のIPアドレスの判定
def is_public_ipv4(addr: str) -> bool:
    """パブリックIPアドレスかどうかを判定"""
    try:
        obj = ipaddress.ip_address(addr)
        # versionはIPv4かの判定 is_globalはグローバルアドレスかの判定
        return (obj.version == 4) and obj.is_global
    except ValueError: # 変な値ならFalse
        return False

# mail内のdateを日本時間に変更
def to_jst(date_str: str) -> str:
    if not date_str or date_str == "(no date)":
        return ""
    
    try:
        # datetimeをオブジェクトに変換
        dt = email.utils.parsedate_to_datetime(date_str)
        if dt is None:
            return ""
        # 日本時間に変換(JST)
        jst = timezone(timedelta(hours=9))
        # dtがtimezoneがなければUTCに変換
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(jst).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


# received内のIPアドレスの取得
def extract_source_ip_from_bottom_received(msg) -> str:
    """
    Receivedヘッダーの「いちばん下」(最初に近い) から IPv4 を抽出
    - パブリックIPがあればそれを優先
    - なければ見つかった最初のIPv4
    - 何もなければ空文字
    """
    # Receivedヘッダーを取得
    received_list = msg.get_all("Received", [])
    if not received_list:
        return ""
    
    # 最後のReceivedを取得 -1は最後の値
    bottom = received_list[-1]
    ips = IPV4_RE.findall(bottom) # findallはリストを返す
    if not ips:
        return ""
    # パブリックIPを優先し、なければ最初のIP(Pablic)を返す
    public_ips = [ip for ip in ips if is_public_ipv4(ip)]
    return public_ips[0] if public_ips else ips[0]


# メールヘッダーを取得
def iter_eml_rows():
    """
    成功した行（result用）と、失敗した行（error用）を分けて返すジェネレータ
    yield ("ok", ok_row) / ("err", err_row)
    """
    for eml_path in BASE_PATH.rglob("*.eml"):
        try:
            with eml_path.open("rb") as eml_file:
                msg = BytesParser(policy=policy.default).parse(eml_file)
                # filename取得
                filename = eml_path.name
                # fullpath取得
                fullpath = str(eml_path)
                # date取得
                raw_date = msg.get("Date", "(no date)")
                jst_date = to_jst(raw_date)
                # subject取得
                raw_subject = msg.get("Subject", "")
                subject = decode_mime_header(raw_subject) or "(no subject)"
                # from取得
                raw_from = msg.get("From", "")
                from_name, from_addr = parseaddr(raw_from)
                from_name = decode_mime_header(from_name)
                # reply取得
                raw_reply = msg.get("Reply-To", "")
                reply_name, reply_addr = parseaddr(raw_reply)
                reply_name = decode_mime_header(reply_name)
                # return取得
                _, return_addr = parseaddr(msg.get("Return-Path", ""))
                # source取得
                source_ip = extract_source_ip_from_bottom_received(msg)

                # NG/WARN/OK判定
                from_domain = get_domain(from_addr)
                reply_domain = get_domain(reply_addr)
                return_domain = get_domain(return_addr)

                if reply_domain and from_domain != reply_domain:
                    verdict = "NG" # 返信すると危険  From と Reply-To が不一致
                elif return_domain and from_domain != return_domain:
                    verdict = "WARN" # 見た目と実際の送信先が違う From と Reply-To は一致しかし From と Return-Path が不一致
                else:
                    verdict = "OK" # 正常
                # 渡すデータの順番
                ok_row = (
                    filename, fullpath, 
                    raw_date, jst_date, 
                    subject,
                    from_name, from_addr, from_domain,
                    reply_name, reply_addr, reply_domain,
                    return_addr, return_domain,
                    source_ip, verdict
                )

                yield ("ok", ok_row)

        except Exception as e:
                err_row = (
                    eml_path.name,
                    str(eml_path),
                    type(e).__name__,
                    str(e)
                )
                yield ("err", err_row)

# CSV出力
def write_results_and_errors(result_csv: Path, error_csv: Path, chunk_size: int = 50000):
    """
    - resultは chunk_size 件ごとに分割（Excelが扱いやすい）
    - errorは 1ファイルにまとめて出力
    """
    # error出力
    error_csv.parent.mkdir(parents=True, exist_ok=True)
    ef = error_csv.open("w", newline="", encoding="utf-8-sig") # sigはExcelでcsvを開くときに表示される文字化けを回避
    ewriter = csv.writer(ef)
    ewriter.writerow(["filename", "fullpath", "error_type", "error_message"])

    # result出力 分割出力
    result_csv.parent.mkdir(parents=True, exist_ok=True)
    # 分割CSVの番号管理
    file_index = 1
    # 今のCSVに何行書いたか
    count_in_file = 0

    #成功件数と失敗件数 
    ok_count = 0
    err_count = 0

    # ファイルとwriterの入れ物
    rf = None # 現在開いているCSVファイル
    rwriter = None # 実際にwriterow()をする人

    #書き込み 
    def open_new_result(idx: int):
        nonlocal rf, rwriter, count_in_file # nonlocalは外側の変数を参照　外のrf,rwriter,count_in_fileを操作する宣言
        # 現在開いているCSVを閉じる
        if rf:
            rf.close()
        # 新しいCSVを作成 .stemは拡張子を除いたファイル名
        path = result_csv.parent / f"{result_csv.stem}_{idx}{result_csv.suffix}"

        rf = path.open("w", newline="", encoding="utf-8-sig") # sigはExcelでcsvを開くときに表示される文字化けを回避
        rwriter = csv.writer(rf)
        rwriter.writerow([
            "filename", "fullpath", 
            "raw_date", "jst_date", 
            "subject",
            "from_name", "from_addr", "from_domain", 
            "reply_name", "reply_addr", "reply_domain",
            "return_addr", "return_domain",
            "source_ip", "verdict"
        ])
        # 行カウントのリセット
        count_in_file = 0
        # pathを返す デバックで表示させためPathを返す
        return path
    
    # メインの処理
    # 書き込み先の用意し、ファイルパスを保存
    last_path = open_new_result(file_index)
    # .emlを順番に取り出す(ok, ok_row)という値を受け取る
    for kind, row in iter_eml_rows():
        if kind == "ok":
            # ファイルの分割を判断
            if count_in_file >= chunk_size:
                # 上限を超えていれば新しいCSVを開く
                file_index += 1
                # Pathの更新
                last_path = open_new_result(file_index)
            # 書き込み
            rwriter.writerow(row)
            # 行数更新
            count_in_file += 1
            # 成功件数更新
            ok_count += 1
            # 5000件毎に表示
            if ok_count % 5000 == 0:
                print(f"Processed OK:{ok_count}, ERR:{err_count}...")
        # errorのときはエラーファイルに書き込む
        else:
            ewriter.writerow(row)
            err_count += 1
    # 最後のCSVを閉じる
    if rf:
        rf.close()
    ef.close()

    print(f"Done. OK={ok_count}, ERR={err_count}")
    print(f"Result files: {file_index} (last: {last_path})")
    print(f"Error file : {error_csv}")



if __name__ == "__main__":
    result_csv = Path("result.csv")     # 例: result_1.csv, result_2.csv ... に分割
    error_csv = Path("errors.csv")      # エラーはここにまとまる

    write_results_and_errors(result_csv, error_csv, chunk_size=50000)
