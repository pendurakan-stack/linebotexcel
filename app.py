from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import pandas as pd
import os
from io import BytesIO
import requests

app = Flask(__name__)

# ตั้งค่า LINE
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
EXCEL_FILE_ID = os.environ.get('EXCEL_FILE_ID')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

def download_excel_from_drive(file_id):
    """ดาวน์โหลด Excel จาก Google Drive"""
    try:
        download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
        response = requests.get(download_url)
        if response.status_code == 200:
            return pd.read_excel(BytesIO(response.content))
        return None
    except:
        return None

def search_part(query):
    """ค้นหาอะไหล่จาก LBNO หรือ OEM"""
    try:
        df = download_excel_from_drive(EXCEL_FILE_ID)
        if df is None:
            return None

        query = str(query).strip().upper()

        # Column: LBNO=A(0), THAI NAME=B(1), OEM=C(2), MODEL=D(3), PRICE_A=E(4)
        results = df[
            (df.iloc[:, 0].astype(str).str.contains(query, case=False, na=False)) |
            (df.iloc[:, 2].astype(str).str.contains(query, case=False, na=False))
        ]

        if results.empty:
            return None

        row = results.iloc[0]
        lbno = str(row.iloc[0]) if pd.notna(row.iloc[0]) else "N/A"
        thai_name = str(row.iloc[1]) if pd.notna(row.iloc[1]) else "ไม่พบชื่อ"
        oem = str(row.iloc[2]) if pd.notna(row.iloc[2]) else "N/A"
        model = str(row.iloc[3]) if pd.notna(row.iloc[3]) else "N/A"
        price_a = str(row.iloc[4]) if pd.notna(row.iloc[4]) else "ไม่พบราคา"

        return {
            'lbno': lbno,
            'name': thai_name,
            'oem': oem,
            'model': model,
            'price': price_a
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route("/callback", methods=['POST'])
def callback():
    """Webhook จาก LINE"""
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """จัดการข้อความ"""
    user_message = event.message.text.strip()

    result = search_part(user_message)

    if result:
        reply_text = f"📦 {result['name']}\n💰 ราคา A: {result['price']} บาท\n🚗 รุ่น: {result['model']}\n\nพี่สนใจไหมครับ"
    else:
        reply_text = f"ไม่พบข้อมูล '{user_message}'\n\nลองส่งรหัส LBNO หรือ OEM ใหม่ครับ"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
