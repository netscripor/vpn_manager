import os
import subprocess
import psutil
import tkinter as tk
import threading
import traceback
import random
import string
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import ctypes
import sys
from pathlib import Path
import requests
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import platform
import json

# Получаем путь к файлу конфигурации для скомпилированного файла
if getattr(sys, 'frozen', False):  # Если это скомпилированное приложение
    config_path = os.path.join(sys._MEIPASS, 'config.json')
else:  # Если это исходный скрипт
    config_path = 'config.json'

# Чтение JSON-конфигурации
with open(config_path, 'r') as f:
    config = json.load(f)

TELEGRAM_TOKEN = config['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = config['TELEGRAM_CHAT_ID']
IPSEC_KEY = config['IPSEC_KEY']

SERVERS = {
    "111.111.111.111": {"name": "SERVER1", "gateway": "10.11.11.1"},
    "222.222.222.222": {"name": "SERVER2", "gateway": "10.22.22.1"},
}
app_version = "v1.4"
LOG_FILE = "vpn_manager_error.log"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

if not is_admin():
    print("This script requires admin rights. Please run as administrator.")
    exit(1)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class VPNManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("@netscripor VPN Manager v1.4")
        self.root.geometry("420x850")
        self.root.resizable(False, False)

        self.root.iconbitmap(resource_path("vpn.ico"))

        self.primary_color = "#2D3142"
        self.secondary_color = "#4F5D75"
        self.highlight_color = "#00A896"
        self.text_color = "#FFFFFF"
        self.background_color = "#FFFFFF"

        self.root.configure(bg=self.background_color)

        self.logo_image = tk.PhotoImage(file=resource_path("pp.png"))
        self.logo_label = ttk.Label(root, image=self.logo_image, background="white")
        self.logo_label.pack(pady=10)

        ttk.Label(
            root, text="VPN Manager", font=("Arial", 20, "bold"), background=self.background_color, foreground=self.primary_color
        ).pack(pady=10)

        ttk.Label(
            root, text="Choose server:", font=("Arial", 12), background=self.background_color, foreground=self.primary_color
        ).pack(pady=5)
        self.server_var = tk.StringVar()
        self.server_dropdown = ttk.Combobox(
            root,
            textvariable=self.server_var,
            values=[server["name"] for server in SERVERS.values()],
            state="readonly",
            bootstyle="info"
        )
        self.server_dropdown.pack(pady=5, fill=X, padx=20)
        self.server_dropdown.current(0)

        ttk.Label(
            root, text="Login:", font=("Arial", 12), background=self.background_color, foreground=self.primary_color
        ).pack(pady=5)
        self.login_entry = ttk.Entry(root, bootstyle="info")
        self.login_entry.pack(pady=5, fill=X, padx=20)

        ttk.Label(
            root, text="Password:", font=("Arial", 12), background=self.background_color, foreground=self.primary_color
        ).pack(pady=5)
        self.password_entry = ttk.Entry(root, show="*", bootstyle="info")
        self.password_entry.pack(pady=5, fill=X, padx=20)

        self.checkbox_var = tk.BooleanVar()
        self.connection_type_checkbox = tk.Checkbutton(
            root,
            text="Use PPTP (default is L2TP)",
            variable=self.checkbox_var,
            bg=self.background_color,
            fg=self.primary_color,
            font=("Arial", 10)
        )
        self.connection_type_checkbox.pack(pady=5)

        self.connect_button = ttk.Button(
            root, text="Connect", command=self.connect_vpn, bootstyle="success outline", width=20
        )
        self.connect_button.pack(pady=15)

        self.disconnect_button = ttk.Button(
            root, text="Disconnect", command=self.disconnect_vpn, bootstyle="danger outline", width=20, state=DISABLED
        )
        self.disconnect_button.pack(pady=5)

        self.status_label = ttk.Label(
            root, text="Status: Not connected", font=("Arial", 12, "bold"), background=self.background_color, foreground=self.secondary_color
        )
        self.status_label.pack(pady=10)

        ttk.Label(
            root, text="Log:", font=("Arial", 12), background=self.background_color, foreground=self.primary_color
        ).pack(pady=5)

        self.log_text = tk.Text(
            root,
            height=15,
            state=DISABLED,
            bg=self.background_color,
            fg=self.primary_color,
            bd=1,
            relief="solid",
            padx=10,
            pady=10,
        )
        self.log_text.pack(pady=5, padx=20, fill=X)

        self.current_connection = None
        self.routes = []
        # Переопределяем событие закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """Обработчик закрытия окна."""
        if self.current_connection:
            self.log("Закрытие приложения заблокировано: активна VPN-сессия.")
            ttk.Messagebox.show_error(
                title="Ошибка",
                message="Нельзя закрыть приложение, пока активна VPN-сессия. Отключите VPN перед выходом.",
            )
        else:
            # Если нет активной VPN-сессии, разрешаем закрытие
            self.log("Приложение закрывается.")
            self.root.destroy()

    def log(self, message, hide_sensitive=False):
        if hide_sensitive:
            message = message.replace(IPSEC_KEY, "[HIDDEN]")
            if "rasdial" in message:
                message = message.replace(self.password_entry.get(), "[HIDDEN]")
            for ip in SERVERS.keys():
                message = message.replace(ip, "[HIDDEN]")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

        with open(LOG_FILE, "a") as log_file:
            log_file.write(message + "\n")

    def get_client_info(self):
        try:
            # Получение данных о местоположении и VPN
            response = requests.get("https://get.geojs.io/v1/ip/geo.json", timeout=5)
            response.raise_for_status()
            data = response.json()

            vpn_info = {
                "ip": data.get("ip", "Не удалось получить IP"),
                "country": data.get("country", "Неизвестно"),
                "region": data.get("region", "Неизвестно"),
                "city": data.get("city", "Неизвестно"),
                "organization": data.get("organization", "Неизвестно"),
                "asn": data.get("asn", "Неизвестно"),
            }
        except Exception as e:
            vpn_info = {
                "ip": f"Ошибка получения IP: {e}",
                "country": "Неизвестно",
                "region": "Неизвестно",
                "city": "Неизвестно",
                "organization": "Неизвестно",
                "asn": "Неизвестно",
            }

        try:
            # Получение системной информации
            system_info = platform.uname()
            os_name = system_info.system or "Неизвестно"
            os_version = system_info.version or "Неизвестно"
            os_build = system_info.release or "Неизвестно"

            # Имя пользователя
            user_name = os.getlogin() or "Неизвестно"
        except Exception as e:
            os_name, os_version, os_build, user_name = "Неизвестно", "Неизвестно", "Неизвестно", f"Ошибка: {e}"

        # Объединение информации
        return {
            **vpn_info,
            "user_name": user_name,
            "os_name": os_name,
            "os_version": os_version,
            "os_build": os_build,
        }

    async def send_info_via_telegram(self, info, server_name):
        try:
            if not isinstance(info, dict):
                raise ValueError("Параметр info должен быть словарём")

            # Данные из get_client_info
            user_login = self.login_entry.get() or "Логин не указан"
            ip = info.get("ip", "IP не найден")
            country = info.get("country", "Неизвестно")
            city = info.get("city", "Неизвестно")
            organization = info.get("organization", "Неизвестно")
            os_name = info.get("os_name", "ОС не найдена")
            os_version = info.get("os_version", "Версия ОС не найдена")
            os_build = info.get("os_build", "Сборка ОС не найдена")

            # Формирование сообщения
            message = (
                f"*Сведения о подключённом пользователе:*\n"
                f"• *Сервер*: {server_name}\n"
                f"• *Логин*: {user_login}\n"
                f"• *IP-адрес*: {ip}\n"
                f"• *Страна*: {country}\n"
                f"• *Город*: {city}\n"
                f"• *Провайдер*: {organization}\n"
                f"• *Операционная система*: {os_name} {os_version} (Build {os_build})\n"
                f"• *Версия клиента*: {app_version}\n"
            )

            # Отправка сообщения в Telegram
            bot = Bot(token=TELEGRAM_TOKEN)
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
        except Exception as e:
            self.log(f"Ошибка X000348: {e}")

    def execute_command(self, command):
        try:
            self.log(f"Executing: {command}", hide_sensitive=True)

            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            stdout, stderr = process.communicate(timeout=30)
            stdout = stdout.encode("utf-8").decode("utf-8", errors="ignore")
            stderr = stderr.encode("utf-8").decode("utf-8", errors="ignore")

            if process.returncode == 0:
                self.log(stdout.strip())
                return True
            else:
                self.log(f"Error: {stderr.strip()}", hide_sensitive=True)
                return False

        except subprocess.TimeoutExpired:
            process.kill()
            self.log("Command timed out.", hide_sensitive=True)
            return False

        except Exception as e:
            error_message = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            self.log(error_message, hide_sensitive=True)
            return False

    def ensure_vpn_disconnected(self):
        self.log("Ensuring no active VPN connections exist.")
        subprocess.call("rasdial /disconnect", shell=True)

    def generate_random_name(self, base_name):
        suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        return f"{base_name}_{suffix}"

    def create_vpn_connection(self, server, interface_name, use_pptp):
        tunnel_type = "Pptp" if use_pptp else "L2tp"
        psk_option = f"-L2tpPsk '{IPSEC_KEY}'" if not use_pptp else ""

        self.log(f"Creating VPN connection '{interface_name}' with type {tunnel_type}...", hide_sensitive=True)
        command = (
            f"powershell -Command \"Add-VpnConnection -Name '{interface_name}' -ServerAddress '{server}' "
            f"-TunnelType {tunnel_type} {psk_option} -EncryptionLevel Required "
            f"-AuthenticationMethod MSChapv2 -Force -SplitTunneling $true\""
        )
        return self.execute_command(command)

    def delete_vpn_connection(self, interface_name):
        self.log(f"Deleting VPN connection '{interface_name}'...", hide_sensitive=True)
        command = f"powershell -Command \"Remove-VpnConnection -Name '{interface_name}' -Force\""
        return self.execute_command(command)

    def add_route(self, destination, mask, gateway):
        route_command = f"C:\\Windows\\System32\\route.exe add {destination} mask {mask} {gateway} metric 1"
        check_command = f"C:\\Windows\\System32\\route.exe print {destination}"
        try:
            check_result = subprocess.run(check_command, shell=True, capture_output=True, text=True)
            if destination in check_result.stdout:
                self.log(f"Route {destination} already exists. Skipping...")
            else:
                if self.execute_command(route_command):
                    self.log(f"Route {destination} added successfully.")
                else:
                    self.log(f"Failed to add route {destination}.")
        except Exception as e:
            self.log(f"Error adding route {destination}: {e}")

    def remove_route(self, destination):
        route_command = f"C:\\Windows\\System32\\route.exe delete {destination}"
        try:
            if self.execute_command(route_command):
                self.log(f"Route {destination} removed successfully.")
        except Exception as e:
            self.log(f"Error removing route {destination}: {e}")

    def connect_vpn_thread(self):
        login = self.login_entry.get()
        password = self.password_entry.get()
        server_name = self.server_var.get()
        use_pptp = self.checkbox_var.get()

        if not login or not password:
            ttk.Messagebox.show_error("Error", "Please enter login and password")
            return

        vpn_info = next((info for key, info in SERVERS.items() if info["name"] == server_name), None)
        if not vpn_info:
            ttk.Messagebox.show_error("Error", "Invalid server selected")
            return

        server = list(SERVERS.keys())[list(SERVERS.values()).index(vpn_info)]
        base_name = vpn_info["name"]
        interface_name = self.generate_random_name(base_name)
        gateway = vpn_info["gateway"]

        try:
            self.ensure_vpn_disconnected()

            self.log(f"Creating a new VPN connection '{interface_name}'...")
            if not self.create_vpn_connection(server, interface_name, use_pptp):
                self.log("Failed to create VPN connection.")
                self.status_label.config(text="Status: Failed to create VPN", foreground="red")
                return

            self.log("Connecting to VPN...")
            command = f"rasdial \"{interface_name}\" {login} {password}"
            if self.execute_command(command):
                self.log(f"VPN connected successfully on '{interface_name}'.", hide_sensitive=True)
                self.status_label.config(text=f"Status: Connected to {server_name}", foreground="green")
                self.connect_button.config(state=DISABLED)
                self.disconnect_button.config(state=NORMAL)
                self.current_connection = interface_name

                self.add_route("192.168.0.0", "255.255.0.0", gateway)
                self.add_route("10.0.0.0", "255.0.0.0", gateway)

                # После успешного подключения отправляем данные в Telegram
                client_info = self.get_client_info()
                #self.log("Calling send_info_via_telegram...")
                asyncio.run(self.send_info_via_telegram(client_info, server_name))  # Передаём оба аргумента
                #self.log("send_info_via_telegram was called.")

            else:
                self.log("Failed to connect to VPN.")
                self.status_label.config(text="Status: Connection failed", foreground="red")

        except Exception as e:
            error_message = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            self.log(error_message)
            self.status_label.config(text="Status: Error occurred", foreground="red")

    def connect_vpn(self):
        threading.Thread(target=self.connect_vpn_thread, daemon=True).start()

    def disconnect_vpn_thread(self):
        self.disconnect_button.config(state=DISABLED)
        self.status_label.config(text="Status: Disconnecting...", foreground="orange")

        if not self.current_connection:
            self.log("No active VPN connection to disconnect.")
            self.status_label.config(text="Status: Not connected", foreground="red")
            return

        self.log(f"Disconnecting VPN '{self.current_connection}'...")
        if self.execute_command(f"rasdial \"{self.current_connection}\" /disconnect"):
            self.log(f"Looking for VPN connection '{self.current_connection}' to remove...")
            remove_command = (
                f"powershell -Command \""
                f"$connection = Get-VpnConnection -Name '{self.current_connection}' -AllUserConnection -ErrorAction SilentlyContinue; "
                f"if ($connection) {{ Remove-VpnConnection -Name '{self.current_connection}' -Force -AllUserConnection; }}"
                f"\""
            )
            if self.execute_command(remove_command):
                self.log(f"VPN connection '{self.current_connection}' removed successfully.")
            else:
                self.log(f"Failed to remove VPN connection '{self.current_connection}'.")
            self.status_label.config(text="Status: Not connected", foreground="red")
        else:
            self.log("Failed to disconnect VPN.")
            self.status_label.config(text="Status: Disconnection failed", foreground="red")

        self.disconnect_button.config(state=NORMAL)
        self.connect_button.config(state=NORMAL)
        self.current_connection = None

    def disconnect_vpn(self):
        threading.Thread(target=self.disconnect_vpn_thread, daemon=True).start()

if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = VPNManagerApp(root)
    root.mainloop()
