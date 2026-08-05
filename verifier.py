import re
import requests
from bs4 import BeautifulSoup

def parse_receipt_input(input_text):
    """የሪሲፕት ቁጥሩን ከሊንክ ወይም ከጽሁፍ ውስጥ ፈልጎ ያወጣል"""
    text = str(input_text or "").strip()
    match = re.search(r"receipt/([A-Z0-9]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    if re.match(r"^[A-Z0-9]{6,15}$", text, re.IGNORECASE):
        return text.upper()
    return None

def verify(receipt_input, expected_receiver_name="", expected_receiver_no=""):
    """
    የቴሌብር ሪሲፕትን በቀጥታ ከኢትዮ ቴሌኮም ሰርቨር ላይ ያረጋግጣል።
    """
    receipt_id = parse_receipt_input(receipt_input)
    if not receipt_id:
        return {"ok": False, "status": 400, "error": "የተሳሳተ የቴሌብር ሪሲፕት ቁጥር ወይም ሊንክ።"}

    url = f"https://transactioninfo.ethiotelecom.et/receipt/{receipt_id}"

    try:
        # Browser መስለን እንጠይቃለን (Block እንዳያደርገን)
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )

        if response.status_code == 404:
            return {"ok": False, "status": 404, "transient": False, "error": "ሪሲፕቱ አልተገኘም። እባክዎ ቁጥሩን ያስተካክሉ።"}
        
        if response.status_code != 200:
            return {"ok": False, "status": response.status_code, "transient": True, "error": "የቴሌብር ሰርቨር በአሁኑ ሰአት አይሰራም (Busy)።"}

        soup = BeautifulSoup(response.text, "lxml")
        text = soup.get_text("\n", strip=True)

        if "telebirr" not in text.lower():
            return {"ok": False, "status": 502, "error": "ያገኘነው ገፅ የቴሌብር ሪሲፕት አይመስልም።"}

        data = {
            "receipt": receipt_id,
            "sender": "Unknown",
            "sender_phone": "Unknown",
            "receiver": "Unknown",
            "receiver_account": "Unknown",
            "amount": 0.0,
            "date": "Unknown",
            "transaction_status": "Unknown"
        }

        lines = [x.strip() for x in text.split("\n") if x.strip()]

        for i, line in enumerate(lines):
            lower = line.lower()

            # 1. መረጃው በ '|' ተለያይቶ ከመጣ
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    key, val = parts[0].lower(), parts[1]
                    if "payer name" in key:
                        data["sender"] = val
                    elif "payer telebirr no" in key:
                        data["sender_phone"] = val
                    elif "credited party name" in key:
                        data["receiver"] = val
                    elif "credited party account no" in key:
                        data["receiver_account"] = val
                    elif "payment date" in key:
                        data["date"] = val
                    elif "transaction status" in key:
                        data["transaction_status"] = val
                    elif "settled amount" in key or "total paid amount" in key:
                        clean_amt = re.sub(r"[^\d.]", "", val)
                        data["amount"] = float(clean_amt) if clean_amt else 0.0
                continue

            # 2. መረጃው በተከታታይ መስመር (HTML Table) ከመጣ
            if "payer name" in lower and data["sender"] == "Unknown":
                if i + 1 < len(lines): data["sender"] = lines[i+1].strip()
            elif "payer telebirr no" in lower and data["sender_phone"] == "Unknown":
                if i + 1 < len(lines): data["sender_phone"] = lines[i+1].strip()
            elif "credited party name" in lower and data["receiver"] == "Unknown":
                if i + 1 < len(lines): data["receiver"] = lines[i+1].strip()
            elif "credited party account no" in lower and data["receiver_account"] == "Unknown":
                if i + 1 < len(lines): data["receiver_account"] = lines[i+1].strip()
            elif "payment date" in lower and data["date"] == "Unknown":
                if i + 1 < len(lines): data["date"] = lines[i+1].strip()
            elif "transaction status" in lower and data["transaction_status"] == "Unknown":
                if i + 1 < len(lines): data["transaction_status"] = lines[i+1].strip()
            elif ("settled amount" in lower or "total paid amount" in lower) and data["amount"] == 0.0:
                if i + 1 < len(lines):
                    clean_amt = re.sub(r"[^\d.]", "", lines[i+1])
                    data["amount"] = float(clean_amt) if clean_amt else 0.0

        if data["sender"] == "Unknown" and data["amount"] == 0.0:
            return {"ok": False, "status": 502, "error": "የሪሲፕቱን መረጃ ማንበብ አልተቻለም።"}

        # ማረጋገጫ (Verification Logic)
        name_match = (data["receiver"].lower() == expected_receiver_name.lower()) if expected_receiver_name else None
        
        # የቴሌብር አካውንት ይሸፈናል (ምሳሌ: 2519****4952) ስለዚህ የመጨረሻ 4 አሃዞችን ብቻ እናወዳድራለን
        acc_match = None
        if expected_receiver_no and data["receiver_account"] != "Unknown":
            clean_expected = re.sub(r"\D", "", expected_receiver_no)
            clean_actual = re.sub(r"\D", "", data["receiver_account"])
            acc_match = clean_actual.endswith(clean_expected[-4:]) if len(clean_expected) >= 4 else clean_actual == clean_expected

        is_completed = data["transaction_status"].lower() == "completed"
        verified = is_completed and (name_match is not False and acc_match is not False) and (name_match is True or acc_match is True)

        return {
            "ok": True,
            "bank": "telebirr",
            "transactionId": data["receipt"],
            "amount": data["amount"],
            "amountText": f"{data['amount']:.2f} ETB",
            "payerName": data["sender"],
            "payerPhone": data["sender_phone"],
            "receiverName": data["receiver"],
            "receiverAccount": data["receiver_account"],
            "status": data["transaction_status"],
            "paymentDate": data["date"],
            "verified": verified,
            "verification": {
                "receiver_name_match": name_match,
                "receiver_account_match": acc_match,
                "status_completed": is_completed
            },
            "alreadyUsed": False, # ይህንን በዳታቤዝ ማረጋገጥ ያንተ ስራ ነው!
            "raw": data
        }

    except requests.exceptions.RequestException:
        return {"ok": False, "status": 0, "transient": True, "error": "የቴሌብር ሰርቨር አይሰራም። እባክዎ ትንሽ ቆይተው ይሞክሩ።"}
    except Exception as e:
        return {"ok": False, "status": 500, "transient": False, "error": f"የሲስተም ችግር አጋጥሟል: {str(e)}"}
