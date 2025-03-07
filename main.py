import requests
import os
import threading
import ctypes
import time
import platform
import json
import random
import itertools
from typing import Optional, Tuple
from colorama import Fore, init

init(autoreset=True)  # Initialize colorama for Windows support

ascii_text = """
        _           _        
       (_)         | |       
        _ _ __  ___| |_ __ _ 
       | | '_ \/ __| __/ _` |
       | | | | \__ \ || (_| |
       |_|_| |_|___/\__\__,_|"""

class Instagram:
    def __init__(self):
        self.base_url = "https://www.instagram.com"
        self.lock = threading.Lock()
        self.claiming = True
        self.proxy_errors = 0
        self.errors = 0
        self.attempts = 0
        self.retries = 0
        self.proxy_cycle = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        ]
        self.clear_cmd = "cls" if platform.system() == "Windows" else "clear"

    def change_title(self):
        if platform.system() == "Windows":
            ctypes.windll.kernel32.SetConsoleTitleW(
                f"Instagram Claimer | Attempts: {self.attempts} | Errors: {self.errors} | Proxy Errors: {self.proxy_errors}"
            )

    def safe_print(self, message: str):
        with self.lock:
            print(f"\n{Fore.WHITE}[{Fore.LIGHTMAGENTA_EX}Console{Fore.WHITE}] {message}")

    def load_proxies(self):
        if not os.path.exists("proxies.txt"):
            open("proxies.txt", "w").close()
            self.safe_print(f"{Fore.RED}Proxy list not found. Created proxies.txt")
            time.sleep(5)
            exit()
        
        with open("proxies.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
            if not proxies:
                self.safe_print(f"{Fore.RED}No proxies found in proxies.txt")
                time.sleep(5)
                exit()
            self.proxy_cycle = itertools.cycle(proxies)
            self.safe_print(f"{Fore.GREEN}Loaded {len(proxies)} proxies")

    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)

    def create_session(self, proxy: Optional[str] = None) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        if proxy:
            session.proxies.update({"http": proxy, "https": proxy})
        return session

    def login(self, session: requests.Session, username: str, password: str) -> Optional[str]:
        try:
            # Initial request to get CSRF token
            session.headers.update({"User-Agent": self.get_random_user_agent()})
            resp = session.get(self.base_url, timeout=10)
            csrf_token = resp.cookies.get("csrftoken")

            # Perform login
            login_data = {
                "username": username,
                "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}",
                "queryParams": {},
                "optIntoOneTap": "false"
            }
            
            session.headers.update({
                "X-CSRFToken": csrf_token,
                "Referer": f"{self.base_url}/",
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            response = session.post(
                f"{self.base_url}/accounts/login/ajax/",
                data=login_data,
                timeout=15
            )
            
            if response.json().get("authenticated"):
                self.safe_print(f"{Fore.GREEN}Successfully logged in as @{username}")
                return csrf_token
            else:
                self.safe_print(f"{Fore.RED}Login failed: {response.text}")
                return None
                
        except Exception as e:
            self.safe_print(f"{Fore.RED}Login error: {str(e)}")
            return None

    def get_account_info(self, session: requests.Session) -> Tuple[str, str]:
        try:
            response = session.get(f"{self.base_url}/accounts/edit/", timeout=10)
            # Modern approach using JSON parsing
            start = response.text.find('{"config":')
            end = response.text.find('};</script>', start) + 1
            json_data = json.loads(response.text[start:end])
            return (
                json_data["user"]["email"],
                json_data["user"]["full_name"]
            )
        except Exception as e:
            self.safe_print(f"{Fore.YELLOW}Failed to get account info: {str(e)}")
            return input("Email: "), input("Full Name: ")

    def claim_username(self, target: str, username: str, password: str):
        while self.claiming:
            proxy = next(self.proxy_cycle)
            session = self.create_session(proxy)
            try:
                # Login with new session
                csrf_token = self.login(session, username, password)
                if not csrf_token:
                    continue
                
                # Get account info
                email, name = self.get_account_info(session)
                
                # Attempt username claim
                payload = {
                    "username": target,
                    "email": email,
                    "first_name": name
                }
                
                session.headers.update({
                    "X-CSRFToken": csrf_token,
                    "Referer": f"{self.base_url}/accounts/edit/",
                    "User-Agent": self.get_random_user_agent()
                })
                
                response = session.post(
                    f"{self.base_url}/accounts/edit/",
                    data=payload,
                    timeout=15
                )
                
                json_response = response.json()
                if json_response.get("status") == "ok":
                    self.safe_print(f"{Fore.GREEN}Successfully claimed @{target}!")
                    self.claiming = False
                    return
                elif "error_type" in json_response:
                    self.handle_errors(json_response)
                else:
                    self.attempts += 1
                    
            except requests.exceptions.RequestException as e:
                self.proxy_errors += 1
            except Exception as e:
                self.errors += 1
            finally:
                self.change_title()
                time.sleep(0.5)  # Rate limiting

    def handle_errors(self, response: dict):
        error_type = response.get("error_type")
        if error_type == "username_is_taken":
            self.attempts += 1
        elif error_type == "rate_limit":
            self.retries += 1
            time.sleep(5)
        else:
            self.errors += 1

    def main(self):
        os.system(self.clear_cmd)
        if platform.system() == "Windows":
            ctypes.windll.kernel32.SetConsoleTitleW("Instagram Auto Claimer")
        print(Fore.LIGHTMAGENTA_EX + ascii_text)
        
        self.load_proxies()
        username = input(f"\n{Fore.WHITE}[{Fore.LIGHTMAGENTA_EX}Input{Fore.WHITE}] Username: @")
        password = input(f"{Fore.WHITE}[{Fore.LIGHTMAGENTA_EX}Input{Fore.WHITE}] Password: ")
        target = input(f"{Fore.WHITE}[{Fore.LIGHTMAGENTA_EX}Input{Fore.WHITE}] Target: @")
        threads = int(input(f"{Fore.WHITE}[{Fore.LIGHTMAGENTA_EX}Input{Fore.WHITE}] Threads: "))
        
        for _ in range(threads):
            threading.Thread(
                target=self.claim_username,
                args=(target, username, password),
                daemon=True
            ).start()
        
        while self.claiming:
            time.sleep(0.1)

if __name__ == "__main__":
    try:
        Instagram().main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Process interrupted by user")
    input("Press Enter to exit...")
