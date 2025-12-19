# Net Cafe Automation
Desktop automation for an internet cafe built with Python, SQLite, and CustomTkinter. It manages table sessions (timed/unlimited), orders with stock tracking, and end-of-day revenue summaries.

## Tech Stack
- Python 3.10+
- SQLite (file-backed)
- CustomTkinter (modern Tk UI)

## Folder Structure
```
net-cafe-automation/
├── main.py             # UI for sessions, orders, billing, reports
├── database.py         # Schema, seeding, data helpers, shared status constants
├── README.md           # Project documentation
├── requirements.txt    # Python dependencies
├── cafe.db             # Auto-created on first run (not in repo by default)
└── __pycache__/        # Python bytecode cache (auto-generated)
```

## Features
- Start and stop timed or unlimited sessions per table
- Add food/drink orders with live stock decrement
- Color-coded table states: Empty, Occupied, Reserved, OutOfOrder
- End-of-day revenue with category breakdown and per-product counts

## Setup
```bash
cd net-cafe-automation
pip install -r requirements.txt
```

## Run
```bash
python main.py
```
A `cafe.db` file will be created in the project folder on first launch. Change `DB_PATH` in `database.py` if you need a different location.

## Notes
- Status/category strings live in `database.py` to keep UI and DB consistent.
- Uses default hourly rates by table kind (VIP vs Standard) inside `database.py`.
