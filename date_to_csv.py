from pathlib import Path
from email import policy # 文字のエンコードやヘッダー処理を自動化
from email.parser import BytesParser # バイナリデータを読み取る
from email.utils import parseaddr
import csv


BASE_PATH = Path(__file__).parent
# rglob("*") で全階層を探索し、フォルダのみ抽出
ALL_SUBFOLDERS = [f for f in BASE_PATH.rglob("*") if f.is_dir() and f.name not in {"__pycache__"}]

def get_target_date():
    for folder in ALL_SUBFOLDERS:
        for target_eml_file in folder.glob("*.eml"):
            with target_eml_file.open("rb") as eml_file:
                msg = BytesParser(policy=policy.default).parse(eml_file)

                filename = target_eml_file.name
                date = msg.get("Date", "(no date)")                
                subject = msg.get("Subject", "(no subject)")
                name, address = parseaddr(msg.get("From", ""))
                reply_name, reply_addr = parseaddr(msg.get("Reply-To", ""))
                _, return_addr = parseaddr(msg.get("Return-Path", ""))

                def get_domain(addr: str) -> str:
                    return addr.split("@")[-1].lower() if "@" in addr else ""

                from_domain = get_domain(address)
                reply_domain = get_domain(reply_addr)
                return_domain = get_domain(return_addr)

                if reply_domain and from_domain != reply_domain:
                    verdict = "NG" # 返信すると危険 From と Reply-To が不一致
                elif return_domain and from_domain != return_domain:
                    verdict = "WARN" # 見た目と実際の送信先が違う From と Reply-To は一致しかし From と Return-Path が不一致
                else:
                    verdict = "OK" # 正常

            yield (filename, date, subject, name, address, reply_name, reply_addr, return_addr, verdict)

def to_csv(output_csv: Path, rows):
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "date", "subject", "name", "address", "reply_name", "reply_addr", "return_addr", "verdict"])
        count = 0
        for row in rows:
            writer.writerow(row)
            count += 1
        print(f"Output {count} rows to {output_csv}")


if __name__ == "__main__":
    output_csv = Path("result.csv")
    rows = get_target_date()
    to_csv(output_csv, rows)