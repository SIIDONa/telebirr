import requests
import re
from bs4 import BeautifulSoup


def verify(receipt):

    url=f"https://transactioninfo.ethiotelecom.et/receipt/{receipt}"

    try:

        r=requests.get(
            url,
            headers={
                "User-Agent":"Mozilla/5.0"
            },
            timeout=15
        )


        if r.status_code != 200:
            return None


        soup=BeautifulSoup(
            r.text,
            "lxml"
        )


        text=soup.get_text(
            " ",
            strip=True
        )


        amount=re.search(
            r'(\d+\.\d+)\s*(?:ብር|ETB)',
            text
        )


        date=re.search(
            r'\d{2}/\d{2}/\d{4}',
            text
        )


        sender=re.search(
            r'ከ\s+(.*?)\(',
            text
        )


        return {

            "receipt":receipt,

            "sender":
            sender.group(1)
            if sender else "Unknown",

            "amount":
            amount.group(1)
            if amount else "Unknown",

            "date":
            date.group(0)
            if date else "Unknown",

            "status":"SUCCESS"

        }


    except:
        return None
