# netscripor VPN Manager 🛡️

VPN-клиент с графическим интерфейсом для Windows, написанный на Python.  
Поддерживает L2TP и PPTP, работает через встроенные средства Windows (`Add-VpnConnection` и `rasdial`), не требует сторонних клиентов.

> Создан сетевиком, не программистом. Работает — и этого достаточно.

## 🚀 Возможности

- Поддержка L2TP и PPTP (с выбором типа в GUI)
- Split-tunnel: интернет остаётся через локального провайдера
- Автоматическое добавление маршрутов (`192.168.0.0/16`, `10.0.0.0/8`)
- Telegram-уведомления при подключении (IP, страна, ОС и т.д.)
- GUI на `ttkbootstrap` (тёмная тема)
- Защита логов от утечек пароля и IPSEC-ключа
- Не требует стороннего VPN-софта — только Windows и права администратора

## 🖼️ Интерфейс
 <img width="271" height="533" alt="image" src="https://github.com/user-attachments/assets/f134eaf6-9d4b-4ca8-8049-ddead7472427" />

_Клиент имеет компактный интерфейс с выбором сервера и логированием всех действий._

## 📦 Установка

### 1. Установите зависимости

```bash
pip install -r requirements.txt
```
### 2. Файл config.json
Создайте config.json в корне проекта (или при сборке в .exe — будет встроен):

```json
{
  "TELEGRAM_TOKEN": "your_bot_token",
  "TELEGRAM_CHAT_ID": "your_chat_id",
  "IPSEC_KEY": "your_shared_secret"
}
```
Измените сервера и сети на свои:
```python
SERVERS = {
    "111.111.111.111": {"name": "SERVER1", "gateway": "10.11.11.1"},
    "222.222.222.222": {"name": "SERVER2", "gateway": "10.22.22.1"},
}
```
### 3. Запуск
```bash
python main.py
```
Требует запуска от имени администратора.

🛠 Сборка .exe
Собираем с помощью PyInstaller:

```shell  
pyinstaller --onefile --noconsole --uac-admin --icon=vpn.ico --version-file=version.txt --add-data "pp.png;." --add-data "vpn.ico;." --add-data "config.json:." "main.py"
```
После сборки финальный файл будет лежать в dist/main.exe.

Пример version.txt
```ini
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 4, 0, 0),
        prodvers=(1, 4, 0, 0),
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo([
            StringTable(
                '040904B0',
                [
                    StringStruct('CompanyName', 'netscripor'),
                    StringStruct('FileDescription', 'VPN-клиент с GUI и Telegram-уведомлениями'),
                    StringStruct('FileVersion', '1.4.0.0'),
                    StringStruct('InternalName', 'VPNManager.exe'),
                    StringStruct('OriginalFilename', 'VPNManager.exe'),
                    StringStruct('ProductName', 'netscripor VPN Manager'),
                    StringStruct('ProductVersion', '1.4.0.0'),
                    StringStruct('Comments', 'https://t.me/netscripor'),
                    StringStruct('LegalTrademarks', 'Python + ttkbootstrap'),
                    StringStruct('LegalCopyright', '© 2025 netscripor')
                ]
            )
        ]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])
    ]
)
```
🧠 Примечания
При каждом запуске клиент создаёт уникальное имя VPN-соединения и удаляет его после отключения

Все логи пишутся в vpn_manager_error.log

Работает только на Windows (используются rasdial, PowerShell и route.exe)

Telegram используется только для уведомлений, данные не отправляются третьим лицам

📡 Подпишись и поддержи проект:

🔗 GitHub: github.com/netscripor 💰 Boosty: boosty.to/netscripor ✈️ Telegram-канал: t.me/netscripor

⭐️ Поддержи проект звездой 🛠 Нашёл баг или есть идея? Создай Issue!
