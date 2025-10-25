# Telegram Daily Sticker Pack Bot

Trimite zilnic la **07:00** un sticker aleator din **sticker pack-ul** pe care îl alegi.

## Pași rapizi
1. Ia `BOT_TOKEN` de la **@BotFather**.
2. Rulează:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export BOT_TOKEN="TOKENUL_TAU"   # Windows: set BOT_TOKEN=TOKENUL_TAU
python main.py
```
3. În Telegram:
   - `/start`
   - `/pack <short_name>` (ex: `MemePackByJohn` sau numele după `addstickers/` din link)
   - opțional `/test` ca să vezi că merge
   - zilnic la 07:00 (Europe/Chisinau) vei primi un sticker aleator.

## Comenzi
- `/pack <short_name>` – setează pack-ul; se cache-uiește lista de `file_id` local.
- `/showpack` – afișează pack-ul curent + câte stickere are în cache.
- `/test` – trimite acum un sticker random.
- `/when HH:MM` – schimbă ora zilnică dacă vrei altceva decât 07:00.
- `/tz Europe/Chisinau` – schimbă fusul orar (implicite Europe/Chisinau).

## Observații
- Folosește `get_sticker_set` → ia toate stickerele din pack și le salvează în cache (per chat).
- Dacă pack-ul se actualizează, poți rula din nou `/pack <short_name>` ca să refacă lista.
- Rulează pe long-polling. Pentru server, ține procesul în viață (systemd, PM2, etc.).
