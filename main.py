
import requests
import json
import os
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
    print("--- Ban Kontrolü Başlıyor ---")
    
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    query_payload = {
        "filter": {
            "property": "Durum",
            "status": { "equals": "Not Banned" }
        }
    }
    
    response = requests.post(query_url, headers=headers, json=query_payload)
    if response.status_code != 200:
        print("Notion Bağlantı Hatası")
        return

    results = response.json().get("results", [])
    print(f"Taranacak kişi: {len(results)}")

    for page in results:
        props = page["properties"]
        steam_link = None
        try:
            prop_data = props.get("Şüpheli ID", {})
            if "url" in prop_data and prop_data["url"]:
                steam_link = prop_data["url"]
            elif "rich_text" in prop_data and len(prop_data["rich_text"]) > 0:
                steam_link = prop_data["rich_text"][0].get("plain_text")
        except: continue

        if not steam_link: continue
        steam_id = get_steam_id_from_url(steam_link)
        if not steam_id: continue

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
                    print(f"🚨 BANLANDI! -> {steam_id}")
                    
                    update_url = f"https://api.notion.com/v1/pages/{page['id']}"
                    update_payload = {
                        "properties": {
                            "Durum": { "status": { "name": "Banned" } },
                            "Banlanma Tarihi": { "date": { "start": real_ban_date } }
                        }
                    }
                    requests.patch(update_url, headers=headers, json=update_payload)
                    
    print("--- Bitti ---")

if __name__ == "__main__":
    check_bans()
