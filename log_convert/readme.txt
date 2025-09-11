# Apacheアクセスログ → CSV変換スクリプト

このスクリプトは、Apacheのアクセスログを読み取り、CSV形式に変換します。  
スペース区切りのログをカンマ区切りにし、主要な項目だけを抽出して整理します。

## 使い方
1. `apache_access_log.txt` をこのスクリプト (`convert_csv.py`) と同じフォルダに置く
2. 以下のコマンドを実行する

   ```bash
   python convert_csv.py
