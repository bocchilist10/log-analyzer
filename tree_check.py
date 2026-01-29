import xml.etree.ElementTree as ET

NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}

"""XMLファイルを読み込んで、
プログラムで操作しやすいデータに変換する
parseでタグ、属性を指定することが可能"""
tree = ET.parse("4624.xml") 
"""親タグ(ルート要素)を取得"""
root = tree.getroot() # 一番外側

for ev in root.findall("e:Event", NS):
    ET.indent(ev, space=" ")
    # ターミナルに出力
    print(ET.tostring(ev, encoding="unicode"))
    # textに書き出し
    with open("extract_xml_data.txt", "w", encoding="utf-8", newline="") as f:
        f.write(ET.tostring(ev, encoding="unicode"))
    break