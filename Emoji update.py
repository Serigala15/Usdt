#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMOJIFY EARN BOT - ULTRA MASTER EDITION
Auto Query_ID | Continuous Mining & Tasks Farming Loop
Loop interval: 12 Hours per mission cycle
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime
import requests

# ==================== [ LOGGING & SILENCER ] ====================
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("EMOJIFY")

from telethon import functions, types
from telethon.sync import TelegramClient

# ==================== [ TELEGRAM CONFIG ] ====================
API_ID = 31810886
API_HASH = "8cfcea6500abce782ec0596b3fbc89b2"

DEFAULT_BOT_ALTERNATIVES = [
    "EmojifyEarnBot",
    "emojify_earn_bot",
]
APP_URL = "https://emojify.app/"
BASE_URL = "https://api.emojify.app"

SESSIONS_DIR = "sessions"
ACCOUNTS_FILE = "emojify_master_accounts.json"

if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

# ==================== [ COLOR THEME ] ====================
G1 = "\033[38;5;45m"
G2 = "\033[38;5;51m"
G3 = "\033[38;5;123m"
G4 = "\033[38;5;159m"
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
PURPLE = "\033[1;35m"
RED = "\033[1;31m"
BLUE = "\033[1;34m"
WHITE = "\033[1;37m"
GRAY = "\033[1;30m"
RESET = "\033[0m"
BOLD = "\033[1m"


# ==================== [ UI HELPERS ] ====================
def clear_screen():
    os.system("clear" if os.name == "posix" else "cls")


def type_anim(text, speed=0.005):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)


def spinner_anim(text, duration=0.8):
    chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    idx = 0
    while time.time() < end_time:
        sys.stdout.write(
            f"\r {CYAN}{chars[idx % len(chars)]}{RESET} {BOLD}{text}{RESET}"
        )
        sys.stdout.flush()
        time.sleep(0.08)
        idx += 1
    sys.stdout.write(f"\r {GREEN}✓{RESET} {BOLD}{text}... Done!{RESET}\n")
    sys.stdout.flush()


def ts():
    return datetime.now().strftime("%H:%M:%S")


def log_info(m):
    print(f"{GRAY}[{ts()}]{RESET} {CYAN}ℹ{RESET}  {m}")


def log_ok(m):
    print(f"{GRAY}[{ts()}]{RESET} {GREEN}✔{RESET}  {m}")


def log_warn(m):
    print(f"{GRAY}[{ts()}]{RESET} {YELLOW}⚠{RESET}  {m}")


def log_err(m):
    print(f"{GRAY}[{ts()}]{RESET} {RED}✖{RESET}  {m}")


# ==================== [ STORAGE HELPERS ] ====================
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=4, ensure_ascii=False)


# ==================== [ INITDATA PARSER ] ====================
def extract_init_data_from_url(full_url):
    candidates = []
    if "#" in full_url:
        frag = full_url.split("#", 1)[1]
        for part in frag.split("&"):
            if part.startswith("tgWebAppData="):
                candidates.append(
                    urllib.parse.unquote(part[len("tgWebAppData=") :])
                )
                break

    pu = urllib.parse.urlparse(full_url)
    if pu.query:
        for part in pu.query.split("&"):
            if part.startswith("tgWebAppData="):
                candidates.append(
                    urllib.parse.unquote(part[len("tgWebAppData=") :])
                )
                break

    m = re.search(r"tgWebAppData=([^&#\s]+)", full_url)
    if m:
        candidates.append(urllib.parse.unquote(m.group(1)))

    for cand in candidates:
        if "user=" in cand and ("auth_date=" in cand or "hash=" in cand):
            return cand
    return candidates[0] if candidates else None


# ==================== [ DUAL TELETHON WEBAPP GETTER ] ====================
async def get_tg_webapp_data(client, bot_name):
    bots = [bot_name] + [b for b in DEFAULT_BOT_ALTERNATIVES if b != bot_name]
    for b in bots:
        b_clean = b.replace("@", "").replace("https://t.me/", "").strip()
        try:
            peer = await client.get_input_entity(b_clean)

            res = await client(
                functions.messages.RequestWebViewRequest(
                    peer=peer,
                    bot=peer,
                    platform="android",
                    url=APP_URL,
                    from_bot_menu=False,
                )
            )
            if res and res.url:
                init_data = extract_init_data_from_url(res.url)
                if init_data and "user=" in init_data:
                    return init_data, b_clean

            res = await client(
                functions.messages.RequestAppWebViewRequest(
                    peer=peer,
                    app=types.InputBotAppShortName(
                        bot_id=peer, short_name="app"
                    ),
                    platform="android",
                    write_allowed=True,
                )
            )
            if res and res.url:
                init_data = extract_init_data_from_url(res.url)
                if init_data and "user=" in init_data:
                    return init_data, b_clean
        except Exception:
            continue
    return None, None


# ==================== [ EMOJIFY WORKER ENGINE ] ====================
class EmojifyWorker:

    def __init__(self, account_data):
        self.name = account_data.get("name", "Account")
        self.session_file = os.path.join(
            SESSIONS_DIR, account_data.get("session", "")
        )
        self.manual_init = account_data.get("init_data", "")
        self.bot_target = account_data.get(
            "bot_username", "EmojifyEarnBot"
        )
        self.init_data = ""
        self.token = ""

        self.http = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20, pool_maxsize=20, max_retries=1
        )
        self.http.mount("http://", adapter)
        self.http.mount("https://", adapter)

        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en,en-US;q=0.9",
            "origin": "https://emojify.app",
            "referer": "https://emojify.app/",
            "sec-ch-ua": '"Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Linux; Android 15; SM-S928B) Telegram-Android/12.1.1 (Samsung Galaxy S24 Ultra; Android 15; SDK 35; LOW)",
            "x-requested-with": "org.telegram.messenger",
        }

    def api_get(self, endpoint, headers=None):
        try:
            h = {**self.headers, **(headers or {})}
            r = self.http.get(BASE_URL + endpoint, headers=h, timeout=20)
            return r.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def api_post(self, endpoint, payload=None, headers=None):
        try:
            h = {**self.headers, **(headers or {})}
            r = self.http.post(
                BASE_URL + endpoint, headers=h, json=payload, timeout=20
            )
            return r.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def authenticate(self):
        uid = 0
        name = "User"
        username = ""
        photo_url = ""
        is_premium = False

        try:
            match = re.search(r"user=([^&]+)", self.init_data)
            if match:
                user_json_str = urllib.parse.unquote(match.group(1))
                user_obj = json.loads(user_json_str)
                uid = user_obj.get("id", 0)
                name = user_obj.get("first_name", "User")
                username = user_obj.get("username", "")
                photo_url = user_obj.get("photo_url", "")
                is_premium = user_obj.get("is_premium", False)
        except Exception as e:
            logger.warning(f"Could not fully parse user JSON from init_data: {e}")

        payload = {
            "uid": uid,
            "name": name,
            "username": username,
            "referBy": "0",
            "photo_url": photo_url,
            "isPremium": is_premium,
            "raw": self.init_data,
        }

        h = {**self.headers, "content-type": "application/json"}
        res = self.api_post("/api/v1/user", payload=payload, headers=h)

        if "token" in res:
            self.token = res.get("token")
            return True
        elif res.get("message") == "Login Successful":
            self.token = res.get("token")
            return True
        else:
            logger.error(f"Server Auth Response: {res}")
            return False

    def get_profile(self):
        h = {"token": self.token}
        res = self.api_get("/api/v1/user", headers=h)
        if res.get("status") == "success":
            return res.get("data")
        return None

    def print_profile_card(self, u):
        print(
            f"\n{CYAN}┌────────────────────────────────────────────────────────┐{RESET}"
        )
        print(
            f"{CYAN}│{RESET}  👤 {BOLD}UID         :{RESET} {WHITE}{u.get('_id', '-'):<38}{CYAN}│{RESET}"
        )
        print(
            f"{CYAN}│{RESET}  💰 {BOLD}Balance     :{RESET} {GREEN}{BOLD}{u.get('balance', 0)} Coins{RESET}"
        )
        print(
            f"{CYAN}│{RESET}  ⛏️ {BOLD}Mining Active:{RESET} {YELLOW}{u.get('isMining')} | Tasks Completed: {u.get('tasks_completed', 0)}{RESET}"
        )
        print(
            f"{CYAN}└────────────────────────────────────────────────────────┘{RESET}\n"
        )

    # 1. Claim Misi & Mining Loop
    async def run_mission_claim_loop(self):
        print(
            f"\n{PURPLE}╔════════════════════════════════════════════════════════╗{RESET}"
        )
        print(
            f"{PURPLE}║{RESET} {BOLD}{GREEN}⛏️ EMOJIFY MISSION & MINING CLAIM ENGINE ACTIVE           {RESET}{PURPLE}║{RESET}"
        )
        print(
            f"{PURPLE}╚════════════════════════════════════════════════════════╝{RESET}\n"
        )

        h = {"token": self.token}
        for attempt in range(1, 4):
            res = self.api_post("/api/v1/user/miners/claim", headers=h)
            msg = res.get("message", "")
            if msg == "Miner Started" or msg == "Claim Successful":
                log_ok("Mission / Mining claim completed successfully!")
                break
            else:
                log_info(f"Attempt {attempt}: {msg}")
                await asyncio.sleep(2)

        profile = self.get_profile()
        if profile:
            print(
                f" {GREEN}✦{RESET} {BOLD}Updated Balance after Mission:{RESET} {GREEN}{profile.get('balance', 0)} Coins{RESET}\n"
            )

    # 2. Farming Tasks / Ads
    async def farm_tasks(self):
        print(
            f"\n{PURPLE}╔════════════════════════════════════════════════════════╗{RESET}"
        )
        print(
            f"{PURPLE}║{RESET} {BOLD}{CYAN}📺 EMOJIFY TASKS & ADS FARMING ENGINE ACTIVE               {RESET}{PURPLE}║{RESET}"
        )
        print(
            f"{PURPLE}╚════════════════════════════════════════════════════════╝{RESET}\n"
        )

        h = {"token": self.token}
        task_count = 0

        while True:
            gen_res = self.api_post("/api/v1/user/generate-ads-id", headers=h)
            if gen_res.get("status") == "success":
                ads_id = gen_res.get("data", {}).get("adsId")
                task_count += 1
                logger.info(
                    f"   🎟 [{task_count}] Generated Task ID: {cyan_text(ads_id)}"
                )

                for s in range(5, 0, -1):
                    sys.stdout.write(
                        f"\r   {GRAY}⏱ Processing Task/Ad... {YELLOW}{s:02d}s{RESET}"
                    )
                    sys.stdout.flush()
                    await asyncio.sleep(1)
                sys.stdout.write("\r" + " " * 35 + "\r")

                watch_res = self.api_post(
                    "/api/v1/user/watch",
                    payload={"adsId": ads_id},
                    headers={**h, "content-type": "application/json"},
                )
                if watch_res.get("message") == "Watch Successful":
                    prof = self.get_profile()
                    bal = prof.get("balance", "Unknown") if prof else "Unknown"
                    log_ok(
                        f"Task #{task_count} Done! | Reward: {GREEN}+Coins{RESET} | Current Balance: {YELLOW}{bal} Coins{RESET}"
                    )
                else:
                    log_err(
                        f"Task Stopped: {watch_res.get('message', watch_res)}"
                    )
                    break
            else:
                log_warn(
                    f"Tasks Limit Reached or No Tasks Available: {gen_res.get('message', gen_res)}"
                )
                break
            await asyncio.sleep(2)

    # Master Execution
    async def run(self):
        client = None
        if self.manual_init:
            self.init_data = self.manual_init
            log_info(f"[{self.name}] Using Manual initData token...")
        else:
            spinner_anim(f"[{self.name}] Connecting Telegram Client")
            client = TelegramClient(self.session_file, API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                log_err(f"[{self.name}] Session unauthorized! Re-login.")
                await client.disconnect()
                return

            spinner_anim(f"[{self.name}] Auto Extracting Query_ID")
            self.init_data, detected_bot = await get_tg_webapp_data(
                client, self.bot_target
            )
            if detected_bot:
                log_ok(f"Query_ID verified with Bot: @{detected_bot}")

        if not self.init_data:
            log_err(f"[{self.name}] Failed to obtain valid initData!")
            if client:
                await client.disconnect()
            return

        logger.info(f"[{self.name}] Authenticating with Emojify Server...")
        if not self.authenticate():
            log_err(f"[{self.name}] Authentication failed!")
            if client:
                await client.disconnect()
            return

        clear_screen()
        show_banner(animated=False)

        log_ok(f"[{self.name}] Account Authenticated Successfully!")

        user = self.get_profile()
        if user:
            self.print_profile_card(user)

        try:
            # 1. Farm Tasks
            await self.farm_tasks()
            await asyncio.sleep(1)

            # 2. Claim Mission / Mining
            await self.run_mission_claim_loop()
            await asyncio.sleep(1)

        finally:
            if client:
                await client.disconnect()

        updated_user = self.get_profile()
        if updated_user:
            print(
                f"\n{GREEN}{BOLD}🏁 [{self.name}] Mission Cycle Finished! Final Profile:{RESET}"
            )
            self.print_profile_card(updated_user)


def cyan_text(t):
    return f"{CYAN}{t}{RESET}"


# ==================== [ ACCOUNT MANAGEMENT ] ====================
def add_account_telethon():
    clear_screen()
    show_banner(animated=False)
    print(
        f"\n{CYAN}┌────────────────────────────────────────────────────────┐{RESET}"
    )
    print(
        f"{CYAN}│{YELLOW}         EMOJIFY - LOGIN TELEGRAM (AUTO QUERY_ID)       {CYAN}│{RESET}"
    )
    print(
        f"{CYAN}└────────────────────────────────────────────────────────┘{RESET}\n"
    )

    name = input(f" {YELLOW}●{RESET} Enter Account Label (e.g. Acc1): ").strip()
    if not name:
        name = f"Account_{int(time.time())}"

    bot_target = input(
        f" {YELLOW}●{RESET} Enter Bot Username (Press Enter for 'EmojifyEarnBot'): "
    ).strip()
    if not bot_target:
        bot_target = "EmojifyEarnBot"

    phone = input(
        f" {YELLOW}●{RESET} Enter Phone Number with Country Code (+62...): "
    ).strip()
    if not phone:
        print(f"\n {RED}[✗]{RESET} Phone number cannot be empty!")
        return

    session_filename = f"{name}.session"
    session_filepath = os.path.join(SESSIONS_DIR, session_filename)

    client = TelegramClient(session_filepath, API_ID, API_HASH)
    try:
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone)
            code = input(
                f" {CYAN}●{RESET} Enter Telegram Login Code (OTP): "
            ).strip()
            try:
                client.sign_in(phone, code)
            except Exception as e:
                if "password" in str(e).lower() or "two-step" in str(e).lower():
                    pwd = input(
                        f" {YELLOW}●{RESET} 2FA Password required: "
                    ).strip()
                    client.sign_in(password=pwd)
                else:
                    raise e

        me = client.get_me()
        client.disconnect()

        accounts = load_accounts()
        accounts = [a for a in accounts if a.get("phone") != phone]
        accounts.append(
            {
                "name": name,
                "phone": phone,
                "session": session_filename,
                "bot_username": bot_target,
                "tg_id": me.id,
                "username": me.username or "",
            }
        )
        save_accounts(accounts)

        print(
            f"\n {GREEN}[✓]{RESET} {BOLD}Login Successful & Session Saved!{RESET}"
        )
    except Exception as e:
        print(f"\n {RED}[✗]{RESET} Login Error: {e}")
        try:
            client.disconnect()
        except Exception:
            pass


def add_account_manual():
    clear_screen()
    show_banner(animated=False)
    print(
        f"\n{CYAN}┌────────────────────────────────────────────────────────┐{RESET}"
    )
    print(
        f"{CYAN}│{YELLOW}          EMOJIFY - ADD ACCOUNT (MANUAL INITDATA)       {CYAN}│{RESET}"
    )
    print(
        f"{CYAN}└────────────────────────────────────────────────────────┘{RESET}\n"
    )

    name = input(
        f" {YELLOW}●{RESET} Enter Account Label (e.g. Manual1): "
    ).strip()
    if not name:
        name = f"Manual_{int(time.time())}"

    init_data = input(
        f" {YELLOW}●{RESET} Paste FRESH initData: "
    ).strip()
    if not init_data:
        print(f"\n {RED}[✗]{RESET} initData cannot be empty!")
        return

    accounts = load_accounts()
    accounts = [a for a in accounts if a.get("init_data") != init_data]
    accounts.append(
        {"name": name, "session": "", "phone": "Manual", "init_data": init_data}
    )
    save_accounts(accounts)
    print(
        f"\n {GREEN}[✓]{RESET} {BOLD}Manual Account Added Successfully!{RESET}"
    )


# OPSI NOMOR 3: LOOP 12 JAM TIAP MISI
def run_all_accounts():
    accounts = load_accounts()
    if not accounts:
        print(f"\n {RED}[✗]{RESET} No accounts found!")
        return

    loop_count = 1
    # 12 Jam = 12 * 3600 = 43200 detik
    LOOP_DELAY = 43200

    try:
        while True:
            clear_screen()
            show_banner(animated=False)
            print(f"\n{YELLOW}================ [ LOOP CYCLE #{loop_count} - 12 HOURS MISSIOIN ] ================{RESET}\n")
            print(f" {CYAN}📱{RESET} Processing {GREEN}{len(accounts)}{RESET} account(s) continuously...\n")
            
            for acc in accounts:
                worker = EmojifyWorker(acc)
                asyncio.run(worker.run())
                time.sleep(2)
            
            print(f"\n{CYAN}💤 Mission cycle finished. Waiting 12 hours before next mission loop...{RESET}")
            for remaining in range(LOOP_DELAY, 0, -1):
                hrs, rem = divmod(remaining, 3600)
                mins, secs = divmod(rem, 60)
                sys.stdout.write(f"\r {GRAY}⏳ Next 12-hour auto-run in: {YELLOW}{hrs:02d}h {mins:02d}m {secs:02d}s{RESET}")
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write("\r" + " " * 60 + "\r")
            loop_count += 1
    except KeyboardInterrupt:
        print(f"\n\n {YELLOW}⏹ Continuous loop stopped by user.{RESET}\n")


def run_specific_account():
    accounts = load_accounts()
    if not accounts:
        print(f"\n {RED}[✗]{RESET} No accounts found!")
        return

    print(f"\n{BOLD}Available accounts:{RESET}")
    for i, a in enumerate(accounts, 1):
        print(
            f"  {CYAN}{i}.{RESET} {WHITE}{a.get('name')}{RESET} - {a.get('phone')}"
        )

    LOOP_DELAY = 43200

    try:
        idx = int(input(f"\n {CYAN}➜{RESET} Select Account number: ").strip()) - 1
        if 0 <= idx < len(accounts):
            try:
                while True:
                    clear_screen()
                    show_banner(animated=False)
                    print(f"\n {CYAN}📱{RESET} Running account continuously (12 Hours Loop)...\n")
                    worker = EmojifyWorker(accounts[idx])
                    asyncio.run(worker.run())
                    print(f"\n{CYAN}💤 Waiting 12 hours before next check...{RESET}")
                    for remaining in range(LOOP_DELAY, 0, -1):
                        hrs, rem = divmod(remaining, 3600)
                        mins, secs = divmod(rem, 60)
                        sys.stdout.write(f"\r {GRAY}⏳ Next auto-run in: {YELLOW}{hrs:02d}h {mins:02d}m {secs:02d}s{RESET}")
                        sys.stdout.flush()
                        time.sleep(1)
                    sys.stdout.write("\r" + " " * 60 + "\r")
            except KeyboardInterrupt:
                print(f"\n\n {YELLOW}⏹ Stopped by user.{RESET}\n")
        else:
            print(f" {RED}[✗]{RESET} Invalid number")
    except ValueError:
        print(f" {RED}[✗]{RESET} Input error")


def delete_account():
    clear_screen()
    show_banner(animated=False)
    accounts = load_accounts()
    if not accounts:
        print(f"\n {RED}[✗]{RESET} No accounts found!")
        return

    print(f"\n{BOLD}Choose account to delete:{RESET}")
    for i, a in enumerate(accounts, 1):
        print(f"  {RED}{i}.{RESET} {WHITE}{a.get('name')}{RESET} ({a.get('phone')})")

    try:
        idx = int(input(f"\n {CYAN}➜{RESET} Enter Account number: ").strip()) - 1
        if 0 <= idx < len(accounts):
            confirm = (
                input(
                    f" {YELLOW}⚠️ Delete '{accounts[idx].get('name')}'? (y/N): {RESET}"
                )
                .strip()
                .lower()
            )
            if confirm == "y":
                deleted = accounts.pop(idx)
                save_accounts(accounts)
                session_path = os.path.join(
                    SESSIONS_DIR, deleted.get("session", "")
                )
                if os.path.exists(session_path):
                    os.remove(session_path)
                print(f" {GREEN}[✓]{RESET} Deleted {deleted.get('name')}")
            else:
                print(f" {GRAY}Cancelled.{RESET}")
        else:
            print(f" {RED}[✗]{RESET} Invalid number")
    except ValueError:
        print(f" {RED}[✗]{RESET} Input error")


# ==================== [ BANNER & UI ] ====================
def show_banner(animated=False):
    banner_lines = [
        f"{G1} ███████╗███╗   ███╗██████╗  ██╗███████╗██╗   ██╗",
        f"{G2} ██╔════╝████╗ ████║██╔══██╗ ██║██╔════╝╚██╗ ██╔╝",
        f"{G3} █████╗  ██╔████╔██║██║  ██║ ██║█████╗   ╚████╔╝ ",
        f"{G4} ██╔══╝  ██║╚██╔╝██║██║  ██║ ██║██╔══╝    ╚██╔╝  ",
        f"{G2} ███████╗██║ ╚═╝ ██║██████╔╝ ██║██║        ██║   ",
        f"{G1} ╚══════╝╚═╝     ╚═╝╚═════╝  ╚═╝╚═╝        ╚═╝   {RESET}",
    ]

    if animated:
        for line in banner_lines:
            print(line)
            time.sleep(0.04)
    else:
        print("\n".join(banner_lines))

    info_card = f"""
{CYAN}┌────────────────────────────────────────────────────────┐
{CYAN}│ {YELLOW}●{RESET} {BOLD}Tool Name{RESET}  {CYAN}➔{RESET} {WHITE}EMOJIFY EARN BOT [12H LOOP EDITION]      {CYAN}│
{CYAN}│ {GREEN}●{RESET} {BOLD}Target Bot{RESET} {CYAN}➔{RESET} {WHITE}t.me/EmojifyEarnBot                      {CYAN}│
{CYAN}│ {PURPLE}●{RESET} {BOLD}Version{RESET}    {CYAN}➔{RESET} {GREEN}v1.0.0 [CONTINUOUS 12H MISSIOIN LOOP]   {CYAN}│
{CYAN}│ {RED}●{RESET} {BOLD}Status{RESET}     {CYAN}➔{RESET} {GREEN}ACTIVE & UNDETECTED                      {CYAN}│
{CYAN}└────────────────────────────────────────────────────────┘{RESET}
"""
    if animated:
        type_anim(info_card, speed=0.002)
        spinner_anim("Initializing Emojify Core Systems", duration=0.6)
        print(f" {GREEN}[✓]{RESET} {BOLD}All Modules Loaded Successfully!{RESET}\n")
    else:
        print(info_card)
        print(f" {GREEN}[✓]{RESET} {BOLD}Emojify Engine Ready!{RESET}\n")


# ==================== [ MAIN CONTROL PANEL ] ====================
def main():
    clear_screen()
    show_banner(animated=True)

    while True:
        accounts = load_accounts()
        count = len(accounts)

        print(
            f"""{CYAN}┌────────────────────────────────────────────────────────┐
{CYAN}│ {YELLOW}EMOJIFY EARN BOT MASTER CONTROL PANEL{RESET}                  {CYAN}│
{CYAN}├────────────────────────────────────────────────────────┤
{CYAN}│ {GREEN}●{RESET} Accounts Loaded {CYAN}➜{RESET} {WHITE}{count:<35}{CYAN}│
{CYAN}│                                                        │
{CYAN}│ {YELLOW}[1]{RESET} Add Telegram Account (Phone + Auto Query_ID)        {CYAN}│
{CYAN}│ {YELLOW}[2]{RESET} Add Account Manually (Paste initData)              {CYAN}│
{CYAN}│ {YELLOW}[3]{RESET} Run All Accounts (12 Hours Loop Each Mission)      {CYAN}│
{CYAN}│ {YELLOW}[4]{RESET} Run Specific Account (12 Hours Loop Mode)          {CYAN}│
{CYAN}│ {YELLOW}[5]{RESET} Delete Account                                     {CYAN}│
{CYAN}│ {YELLOW}[6]{RESET} Exit                                               {CYAN}│
{CYAN}└────────────────────────────────────────────────────────┘{RESET}
"""
        )

        choice = input(f" {CYAN}emojify@termux{RESET}:{RED}~$ {RESET}").strip()

        if choice == "1":
            add_account_telethon()
        elif choice == "2":
            add_account_manual()
        elif choice == "3":
            run_all_accounts()
        elif choice == "4":
            run_specific_account()
        elif choice == "5":
            delete_account()
        elif choice == "6":
            print(f"\n {GREEN}[✓]{RESET} Emojify Bot stopped. Bye! 👋\n")
            sys.exit(0)
        else:
            print(f"\n {RED}[✗]{RESET} Invalid choice! Please select 1-6.")

        input(f"\n {GRAY}Press [Enter] to return to panel...{RESET}")
        clear_screen()
        show_banner(animated=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n {YELLOW}⏹ Stopped by user.{RESET}\n")
        sys.exit(0)