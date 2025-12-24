from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from email.header import decode_header
import csv
import re
import ipaddress

BASE_PATH = Path(__file__).parent
ALL_SUBFOLDERS = [f for f in BASE_PATH.rglob("*") if f.is_dir() and f.name not in {"__pycache__"}]

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
            out.append(text.decode(charset or "utf-8", errors="replace"))
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
    received_list = msg.get_all("Received", [])  # 複数行を取得
    if not received_list:
        return ""

    bottom = received_list[-1]  # ★いちばん下
    ips = IPV4_RE.findall(bottom)

    if not ips:
        return ""

    public_ips = [ip for ip in ips if is_public_ipv4(ip)]
    if public_ips:
        return public_ips[0]  # まずは先頭でOK

    return ips[0]  # パブリックが無ければ先頭（内部IPの可能性）

def get_target_date():
    for folder in ALL_SUBFOLDERS:
        for target_eml_file in folder.glob("*.eml"):
            with target_eml_file.open("rb") as eml_file:
                msg = BytesParser(policy=policy.default).parse(eml_file)

            filename = target_eml_file.name
            date = msg.get("Date", "(no date)")

            raw_subject = msg.get("Subject", "")
            subject = decode_mime_header(raw_subject) or "(no subject)"

            raw_from = msg.get("From", "")
            from_name, address = parseaddr(raw_from)
            from_name = decode_mime_header(from_name)

            raw_reply = msg.get("Reply-To", "")
            reply_name, reply_addr = parseaddr(raw_reply)
            reply_name = decode_mime_header(reply_name)

            _, return_addr = parseaddr(msg.get("Return-Path", ""))

            # ★追加：Received最下段のIP
            source_ip = extract_source_ip_from_bottom_received(msg)

            from_domain = get_domain(address)
            reply_domain = get_domain(reply_addr)
            return_domain = get_domain(return_addr)

            if reply_domain and from_domain != reply_domain:
                verdict = "NG"   # 返信すると危険（From と Reply-To が不一致）
            elif return_domain and from_domain != return_domain:
                verdict = "WARN" # 注意（From と Reply-To は一致、From と Return-Path が不一致）
            else:
                verdict = "OK"   # 正常

            yield (
                filename, date, subject,
                from_name, address,
                reply_name, reply_addr,
                return_addr, source_ip, verdict
            )

def to_csv(output_csv: Path, rows):
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "filename", "date", "subject",
            "name", "address",
            "reply_name", "reply_addr",
            "return_addr", "source_ip", "verdict"
        ])

        count = 0
        for row in rows:
            writer.writerow(row)
            count += 1

    print(f"Output {count} rows to {output_csv}")

if __name__ == "__main__":
    output_csv = Path("result.csv")
    rows = get_target_date()
    to_csv(output_csv, rows)
