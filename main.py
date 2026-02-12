import requests
import json
import os
import time
from datetime import datetime, timedelta

# GİZLİ AYARLAR (GitHub Secrets'tan otomatik gelecek)
STEAM_API_KEY = os.environ["STEAM_API_KEY"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["DATABASE_ID"]

headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_steam_id_from_url(url):
    if not url: return None
    url = url.strip().rstrip('/')
    parts = url.split('/')
    if 'profiles' in parts:
        return parts[-1]
    return None

def check_bans():
    print("--- 🕵️‍♂️ Detaylı Ban Kontrolü Başlıyor ---")
    
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    query_payload = {
        "filter": {
            "property": "Durum",
            "status": { "equals": "Not Banned" }
        }
    }
    
    response = requests.post(query_url, headers=headers, json=query_payload)
    if response.status_code != 200:
        print(f"❌ Notion Hatası: {response.text}")
        return

    results = response.json().get("results", [])
    print(f"📋 Listede {len(results)} kişi var, taranıyor...\n")

    count = 0
    for page in results:
        count += 1
        props = page["properties"]
        steam_link = None
        
        # Notion'dan linki çek
        try:
            prop_data = props.get("Şüpheli ID", {})
            if "url" in prop_data and prop_data["url"]:
                steam_link = prop_data["url"]
            elif "rich_text" in prop_data and len(prop_data["rich_text"]) > 0:
                steam_link = prop_data["rich_text"][0].get("plain_text")
        except: 
            print(f"{count}. ⚠️ Link Bulunamadı - Atlanıyor")
            continue

        if not steam_link: 
            print(f"{count}. ⚠️ Link Boş - Atlanıyor")
            continue
            
        steam_id = get_steam_id_from_url(steam_link)
        if not steam_id: 
            print(f"{count}. ⚠️ ID Çözülemedi: {steam_link}")
            continue

        # Steam'den sor
        steam_url = f"http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key={STEAM_API_KEY}&steamids={steam_id}"
        steam_res = requests.get(steam_url)
        
        if steam_res.status_code == 200:
            data = steam_res.json()
            if "players" in data and len(data["players"]) > 0:
                player = data["players"][0]
                is_banned = player["VACBanned"] or player["NumberOfGameBans"] > 0
                
                if is_banned:
                    days_ago = player.get("DaysSinceLastBan", 0)
                    real_ban_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                    print(f"{count}. 🚨 BANLANDI! -> {steam_id} ({days_ago} gün önce)")
                    
                    # Notion güncelle
                    update_url = f"https://api.notion.com/v1/pages/{page['id']}"
                    update_payload = {
                        "properties": {
                            "Durum": { "status": { "name": "Banned" } },
                            "Banlanma Tarihi": { "date": { "start": real_ban_date } }
                        }
                    }
                    requests.patch(update_url, headers=headers, json=update_payload)
                else:
                    # BURASI YENİ EKLENDİ: Temiz olanları da yazsın
                    print(f"{count}. 🟢 Temiz -> {steam_id}")
            else:
                print(f"{count}. ❓ Steam verisi boş döndü -> {steam_id}")
        else:
            print(f"{count}. ❌ Steam API Hatası")
        
        # Çok hızlı istek atıp Steam'i kızdırmayalım, minik bir bekleme
        # (GitHub sunucuları çok hızlıdır)
        time.sleep(0.1) 

    print("\n--- ✅ Kontrol Bitti ---")

if __name__ == "__main__":
    check_bans()
