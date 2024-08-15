import requests


def telegram_bot(message):
    """TOKEN = "7443228939:AAH1Yc_Zb4LpH_naJC1o2TbbKj_zCaBU-2I"
    url = f"https://api.telegram.org/bot7443228939:AAH1Yc_Zb4LpH_naJC1o2TbbKj_zCaBU-2I/getUpdates"
    print(requests.get(url).json())
"""
    chat_id = "1609010851"
    # message = "Air Conditioner Exceeded Recommended Useage! Please mannually turn off the airconditioner to save electricity and money. "
    url = f"https://api.telegram.org/bot7443228939:AAH1Yc_Zb4LpH_naJC1o2TbbKj_zCaBU-2I/sendMessage?chat_id={chat_id}&text={message}"
    print(requests.get(url).json())