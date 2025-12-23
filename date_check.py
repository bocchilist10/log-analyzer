from email import policy # 文字のエンコードやヘッダー処理を自動化
from email.parser import BytesParser # バイナリデータを読み取る
from email.utils import parseaddr
from pathlib import Path

MAX_SHOW = 5

for i,eml in enumerate(Path("Inbox").glob("*.eml"), start=1):
    if i > MAX_SHOW:
        break
    with open(eml, "rb") as eml_file:
        msg = BytesParser(policy=policy.default).parse(eml_file)

        name, address = parseaddr(msg.get("From", ""))
        subject = msg.get("Subject", "(no subject)")
        date = msg.get("Date", "(no date)")
        _, return_addr = parseaddr(msg.get("Return-Path", ""))
        reply_name, reply_addr = parseaddr(msg.get("Reply-To", ""))

        print(f"Filename:{eml.name}")
        print(f"Name:{name}, Address:{address}")
        print(f"Subject:{subject}")
        print(f"Date:{date}")
        print(f"Return-Path:{return_addr}")
        print(f"Reply-Name:{reply_name}, Reply-Address:{reply_addr}")
        print("-" * 100)