import requests
from bs4 import BeautifulSoup

def verify(receipt):
    url = f"https://transactioninfo.ethiotelecom.et/receipt/{receipt}"

    try:
        # ቴሌኮም bot እንዳይመስለው ትክክለኛ User-Agent መጠቀም
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            }
        )

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "lxml")
        text = soup.get_text("\n", strip=True)

        # ሪሲፕቱ ትክክለኛ የቴሌብር መሆኑን ማረጋገጥ
        if "telebirr" not in text.lower():
            return None

        # Data Dictionary (አዲስ 'receiver' ተጨምሯል)
        data = {
            "receipt": receipt,
            "sender": "Unknown",
            "receiver": "Unknown", 
            "amount": "Unknown",
            "date": "Unknown"
        }

        lines = [x.strip() for x in text.split("\n") if x.strip()]

        for i, line in enumerate(lines):
            lower = line.lower()

            # 1. መረጃው በ '|' ተለያይቶ ከመጣ (ለምሳሌ: Payer Name | Abebe)
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    key = parts[0].lower()
                    val = parts[1]
                    
                    if "payer name" in key:
                        data["sender"] = val
                    elif "credited party name" in key:
                        data["receiver"] = val
                    elif "payment date" in key:
                        data["date"] = val
                    elif "settled amount" in key or "total paid amount" in key:
                        # 'Birr' እና ኮማዎችን (,) እናጠፋለን በዳታቤዝ በቀላሉ ማስላት እንዲቻል
                        data["amount"] = val.lower().replace("birr", "").replace(",", "").strip()
                continue

            # 2. መረጃው በተከታዩ መስመር ላይ ከመጣ (HTML Table Structure)
            if "payer name" in lower and data["sender"] == "Unknown":
                if i + 1 < len(lines):
                    data["sender"] = lines[i+1].strip()

            elif "credited party name" in lower and data["receiver"] == "Unknown":
                if i + 1 < len(lines):
                    data["receiver"] = lines[i+1].strip()

            elif "payment date" in lower and data["date"] == "Unknown":
                if i + 1 < len(lines):
                    data["date"] = lines[i+1].strip()

            elif ("settled amount" in lower or "total paid amount" in lower) and data["amount"] == "Unknown":
                if i + 1 < len(lines):
                    raw_amount = lines[i+1].lower().replace("birr", "").replace(",", "").strip()
                    data["amount"] = raw_amount

        # ማረጋገጫ፡ ቢያንስ የከፋዩ ስም ወይም የገንዘብ መጠን ካልተገኘ Parsing አልሰራም ማለት ነው
        if data["sender"] == "Unknown" and data["amount"] == "Unknown":
            return None

        return data

    except Exception as e:
        print("VERIFY ERROR:", e)
        return None
