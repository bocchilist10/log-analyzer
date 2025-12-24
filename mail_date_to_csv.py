from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from email.header import decode_header
import csv
import re
import ipaddress

BASE_PATH = Path(__file__).parent

# IPv4抽出（簡易）
IPV4_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def decode_mime_header(value: str) -> str:
    """=?UTF-8?...?= のようなMIMEエンコードヘッダをデコードして文字化けを直す"""
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, charset in parts:
        if isinstance(text, bytes):
            # charsetが不明な場合に備えて候補を順番に試す
            candidates = []
            if charset:
                candidates.append(charset)
            candidates += ["utf-8", "iso-2022-jp", "cp932", "latin-1"]

            for enc in candidates:
                try:
                    out.append(text.decode(enc))
                    break
                except Exception:
                    continue
            else:
                out.append(text.decode("utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def get_domain(addr: str) -> str:
    return addr.split("@")[-1].lower() if "@" in addr else ""


def is_public_ipv4(ip: str) -> bool:
    """パブリックIPv4なら True（内部・予約・loopback等は False）"""
    try:
        obj = ipaddress.ip_address(ip)
        return (obj.version == 4) and obj.is_global
    except ValueError:
        return False


def extract_source_ip_from_bottom_received(msg) -> str:
    """
    Receivedヘッダーの「いちばん下」(最初に近い) から IPv4 を抽出
    - パブリックIPがあればそれを優先
    - なければ見つかった最初のIPv4
    - 何もなければ空文字
    """
    received_list = msg.get_all("Received", [])
    if not received_list:
        return ""

    bottom = received_list[-1]  # ★いちばん下
    ips = IPV4_RE.findall(bottom)
    if not ips:
        return ""

    public_ips = [ip for ip in ips if is_public_ipv4(ip)]
    return public_ips[0] if public_ips else ips[0]


def iter_eml_rows():
    """
    成功した行（result用）と、失敗した行（error用）を分けて返すジェネレータ
    yield ("ok", ok_row) / ("err", err_row)
    """
    for eml_path in BASE_PATH.rglob("*.eml"):
        try:
            with eml_path.open("rb") as eml_file:
                msg = BytesParser(policy=policy.default).parse(eml_file)

            filename = eml_path.name
            fullpath = str(eml_path)

            date = msg.get("Date", "(no date)")

            raw_subject = msg.get("Subject", "")
            subject = decode_mime_header(raw_subject) or "(no subject)"

            raw_from = msg.get("From", "")
            from_name, from_addr = parseaddr(raw_from)
            from_name = decode_mime_header(from_name)

            raw_reply = msg.get("Reply-To", "")
            reply_name, reply_addr = parseaddr(raw_reply)
            reply_name = decode_mime_header(reply_name)

            _, return_addr = parseaddr(msg.get("Return-Path", ""))

            source_ip = extract_source_ip_from_bottom_received(msg)

            # NG/WARN/OK 判定
            from_domain = get_domain(from_addr)
            reply_domain = get_domain(reply_addr)
            return_domain = get_domain(return_addr)

            if reply_domain and from_domain != reply_domain:
                verdict = "NG"
            elif return_domain and from_domain != return_domain:
                verdict = "WARN"
            else:
                verdict = "OK"

            ok_row = (
                filename, fullpath, date, subject,
                from_name, from_addr,
                reply_name, reply_addr,
                return_addr, source_ip, verdict
            )
            yield ("ok", ok_row)

        except Exception as e:
            # どのファイルで何が起きたか記録して続行する
            err_row = (
                eml_path.name,
                str(eml_path),
                type(e).__name__,
                str(e),
            )
            yield ("err", err_row)


def write_results_and_errors(result_csv: Path, error_csv: Path, chunk_size: int = 50000):
    """
    - resultは chunk_size 件ごとに分割（Excelが扱いやすい）
    - errorは 1ファイルにまとめて出力
    """
    # error CSV を先に開く
    error_csv.parent.mkdir(parents=True, exist_ok=True)
    ef = error_csv.open("w", newline="", encoding="utf-8-sig")
    ewriter = csv.writer(ef)
    ewriter.writerow(["filename", "fullpath", "error_type", "error_message"])

    # result CSV 分割用
    result_csv.parent.mkdir(parents=True, exist_ok=True)
    file_index = 1
    count_in_file = 0
    ok_count = 0
    err_count = 0

    rf = None
    rwriter = None

    def open_new_result(idx: int):
        nonlocal rf, rwriter, count_in_file
        if rf:
            rf.close()
        path = result_csv.parent / f"{result_csv.stem}_{idx}{result_csv.suffix}"
        rf = path.open("w", newline="", encoding="utf-8-sig")
        rwriter = csv.writer(rf)
        rwriter.writerow([
            "filename", "fullpath", "date", "subject",
            "from_name", "from_addr",
            "reply_name", "reply_addr",
            "return_addr", "source_ip", "verdict"
        ])
        count_in_file = 0
        return path

    last_path = open_new_result(file_index)

    for kind, row in iter_eml_rows():
        if kind == "ok":
            if count_in_file >= chunk_size:
                file_index += 1
                last_path = open_new_result(file_index)

            rwriter.writerow(row)
            count_in_file += 1
            ok_count += 1

            if ok_count % 5000 == 0:
                print(f"Processed OK: {ok_count}, ERR: {err_count} ...")

        else:
            ewriter.writerow(row)
            err_count += 1

    if rf:
        rf.close()
    ef.close()

    print(f"Done. OK={ok_count}, ERR={err_count}")
    print(f"Result files: {file_index} (last: {last_path})")
    print(f"Error file : {error_csv}")


if __name__ == "__main__":
    # 出力先（必要ならパス変更OK）
    result_csv = Path("result.csv")     # 例: result_1.csv, result_2.csv ... に分割されます
    error_csv = Path("errors.csv")      # エラーはここにまとまります

    write_results_and_errors(result_csv, error_csv, chunk_size=50000)
