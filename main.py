import sys
import customtkinter as ctk
from tkinter import messagebox

import database as db
from database import (
    STATUS_EMPTY,
    STATUS_OCCUPIED,
    STATUS_RESERVED,
    STATUS_OUT_OF_ORDER,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

COLOR_MAP = {
    STATUS_EMPTY: "#2e7d32",
    STATUS_OCCUPIED: "#c62828",
    STATUS_RESERVED: "#1565c0",
    STATUS_OUT_OF_ORDER: "#ef6c00",
    "DEFAULT": "#404040",
}

TEXT_COLOR = "#ffffff"
BG_COLOR = "#2b2b2b"

class SessionStartWindow(ctk.CTkToplevel):
    """Popup window to start a new session for a table."""

    def __init__(self, root, table_id: int):
        super().__init__(root)
        self.title("Start Session")
        self.configure(fg_color=BG_COLOR)
        self.geometry("420x300")
        self.resizable(False, False)

        self.table_id = table_id
        self.selected_type = ctk.StringVar(value="Unlimited")
        self.selected_minutes = ctk.StringVar(value="60")

        frame = ctk.CTkFrame(self, fg_color="#333333", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        title = ctk.CTkLabel(frame, text="Session Selection", text_color=TEXT_COLOR, font=("Segoe UI", 18, "bold"))
        title.pack(pady=(12, 8))

        options_frame = ctk.CTkFrame(frame, fg_color="#303030", corner_radius=12)
        options_frame.pack(fill="x", padx=12, pady=8)
        rb_unlimited = ctk.CTkRadioButton(options_frame, text="Unlimited", variable=self.selected_type, value="Unlimited", command=self.on_radio_change)
        rb_timed = ctk.CTkRadioButton(options_frame, text="Timed", variable=self.selected_type, value="Timed", command=self.on_radio_change)
        rb_unlimited.pack(anchor="w", padx=10, pady=6)
        rb_timed.pack(anchor="w", padx=10, pady=6)

        self.duration_frame = ctk.CTkFrame(frame, fg_color="#303030", corner_radius=12)
        duration_lbl = ctk.CTkLabel(self.duration_frame, text="Duration (min):", text_color=TEXT_COLOR)
        duration_lbl.pack(side="left", padx=8, pady=8)
        self.duration_menu = ctk.CTkOptionMenu(self.duration_frame, values=["30", "60", "120", "180"], variable=self.selected_minutes, command=lambda *_: self.update_price())
        self.duration_menu.pack(side="left", padx=8)

        self.price_lbl = ctk.CTkLabel(frame, text="Opening", text_color=TEXT_COLOR, font=("Segoe UI", 14))
        self.price_lbl.pack(pady=6)

        self.btn_start = ctk.CTkButton(frame, text="Start Unlimited", corner_radius=10, command=self.start_session)
        self.btn_start.pack(padx=12, pady=12, fill="x")

        self.update_view()

    def on_radio_change(self):
        """Handle radio button change and refresh view."""
        self.update_view()

    def update_view(self):
        """Show/hide duration controls and refresh pricing label/button."""
        session_type = self.selected_type.get()
        if session_type == "Unlimited":
            try:
                self.duration_frame.pack_forget()
            except Exception:
                pass
            self.price_lbl.configure(text="Opening")
            self.btn_start.configure(text="Start Unlimited")
        else:
            self.duration_frame.pack(fill="x", padx=12, pady=8)
            self.btn_start.configure(text="Start Timed")
        self.update_price()

    def update_price(self):
        """Update the price label based on selected duration and table rate."""
        session_type = self.selected_type.get()
        if session_type == "Timed":
            try:
                minutes = int(self.selected_minutes.get())
            except Exception:
                minutes = 60
            rate = db.get_hourly_rate(self.table_id)
            upfront = round(rate * (minutes / 60.0), 2)
            self.price_lbl.configure(text=f"Charge: {upfront:.2f} TL")
        else:
            self.price_lbl.configure(text="Opening")

    def start_session(self):
        """Validate selection and start the session."""
        table = db.fetch_table(self.table_id)
        if not table:
            messagebox.showerror("Error", "Table not found.")
            return
        if table["status"] == STATUS_OUT_OF_ORDER:
            messagebox.showerror("Error", "Cannot start a session on an out-of-order table.")
            return
        session_type = self.selected_type.get()
        if session_type == "Timed":
            try:
                minutes = int(self.selected_minutes.get())
            except Exception:
                messagebox.showerror("Error", "Invalid duration.")
                return
            db.start_timed_session(self.table_id, minutes)
        else:
            db.start_unlimited_session(self.table_id)
        self.destroy()

class OrderWindow(ctk.CTkToplevel):
    """Popup window to add an order for the selected table."""

    def __init__(self, root, table_id: int):
        super().__init__(root)
        self.title("Add Order")
        self.configure(fg_color=BG_COLOR)
        self.geometry("520x520")
        self.resizable(False, False)

        self.table_id = table_id
        self.selected_category = ctk.StringVar(value="Food")
        self.selected_product_id = None

        main_frame = ctk.CTkFrame(self, fg_color="#333333", corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        title = ctk.CTkLabel(main_frame, text="Select Product and Quantity", text_color=TEXT_COLOR, font=("Segoe UI", 18, "bold"))
        title.pack(pady=(12, 8))

        cat_frame = ctk.CTkFrame(main_frame, fg_color="#303030", corner_radius=12)
        cat_frame.pack(fill="x", padx=12, pady=8)
        cat_lbl = ctk.CTkLabel(cat_frame, text="Category:", text_color=TEXT_COLOR)
        cat_lbl.pack(side="left", padx=8, pady=8)
        cat_menu = ctk.CTkOptionMenu(cat_frame, values=["Food", "Drink"], variable=self.selected_category, command=self.on_category_change)
        cat_menu.pack(side="left", padx=8)

        self.scroll = ctk.CTkScrollableFrame(main_frame, fg_color="#303030", corner_radius=12)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=8)

        qty_frame = ctk.CTkFrame(main_frame, fg_color="#303030", corner_radius=12)
        qty_frame.pack(fill="x", padx=12, pady=8)
        qty_lbl = ctk.CTkLabel(qty_frame, text="Quantity:", text_color=TEXT_COLOR)
        qty_lbl.pack(side="left", padx=8, pady=8)
        self.qty_entry = ctk.CTkEntry(qty_frame, placeholder_text="1")
        self.qty_entry.pack(side="left", padx=8)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="#303030", corner_radius=12)
        btn_frame.pack(fill="x", padx=12, pady=12)
        btn_add = ctk.CTkButton(btn_frame, text="Add Order", corner_radius=10, command=self.add_order)
        btn_add.pack(side="right", padx=8, pady=8)

        self.load_products("Food")

    def on_category_change(self, *_):
        """Reload products when category changes."""
        self.load_products(self.selected_category.get())

    def load_products(self, category: str):
        """Populate scroll area with product buttons for the category."""
        for widget in self.scroll.winfo_children():
            widget.destroy()
        products = db.fetch_products(category=category)
        for p in products:
            text = f"{p['name']} - {p['price']:.2f} TL"
            btn = ctk.CTkButton(self.scroll, text=text, corner_radius=10)
            btn.configure(command=lambda pid=p['id']: self.select_product(pid))
            btn.pack(fill="x", padx=8, pady=6)

    def select_product(self, product_id: int):
        """Store selected product id for ordering."""
        self.selected_product_id = product_id

    def add_order(self):
        """Validate selection and add the order via database."""
        if self.selected_product_id is None:
            messagebox.showwarning("Warning", "Please select a product.")
            return
        try:
            qty = int(self.qty_entry.get() or "1")
            if qty <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "Invalid quantity.")
            return
        success = db.add_order(self.table_id, self.selected_product_id, qty)
        if success:
            messagebox.showinfo("Success", "Order added.")
            self.destroy()
        else:
            messagebox.showerror("Error", "Insufficient stock or product not found.")

class EndOfDayReportWindow(ctk.CTkToplevel):
    """Popup window to show end-of-day revenue and breakdowns."""

    def __init__(self, root):
        super().__init__(root)
        self.title("End of Day Report")
        self.configure(fg_color=BG_COLOR)
        self.geometry("540x640")
        self.resizable(False, False)

        frame = ctk.CTkFrame(self, fg_color="#333333", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        title = ctk.CTkLabel(frame, text="End of Day Report", text_color=TEXT_COLOR, font=("Segoe UI", 18, "bold"))
        title.pack(pady=(12, 8))

        report = db.get_end_of_day_report()
        lbl_sessions = ctk.CTkLabel(frame, text=f"Session Revenue: {report['session_revenue']:.2f} TL", text_color=TEXT_COLOR)
        lbl_orders = ctk.CTkLabel(frame, text=f"Order Revenue: {report['order_revenue']:.2f} TL", text_color=TEXT_COLOR)
        lbl_total = ctk.CTkLabel(frame, text=f"Total Revenue: {report['total_revenue']:.2f} TL", text_color=TEXT_COLOR, font=("Segoe UI", 15, "bold"))
        lbl_count = ctk.CTkLabel(frame, text=f"Order Count: {report['order_count']}", text_color=TEXT_COLOR)
        lbl_sessions.pack(pady=4)
        lbl_orders.pack(pady=4)
        lbl_total.pack(pady=6)
        lbl_count.pack(pady=4)

        bottom = ctk.CTkScrollableFrame(frame, fg_color="#303030", corner_radius=12)
        bottom.pack(fill="both", expand=True, padx=12, pady=8)
        ctk.CTkLabel(bottom, text="Category Breakdown", text_color=TEXT_COLOR, font=("Segoe UI", 14, "bold")).pack(pady=6)
        for cat, total in report.get("category_totals", {}).items():
            ctk.CTkLabel(bottom, text=f"{cat}: {total:.2f} TL", text_color=TEXT_COLOR).pack(anchor="w", padx=8, pady=2)

        sold = db.get_end_of_day_product_report()
        ctk.CTkLabel(bottom, text="Sold Products", text_color=TEXT_COLOR, font=("Segoe UI", 14, "bold")).pack(pady=(12, 6))
        if sold:
            for name, qty in sold.items():
                ctk.CTkLabel(bottom, text=f"{qty}x {name}", text_color=TEXT_COLOR).pack(anchor="w", padx=8, pady=2)
        else:
            ctk.CTkLabel(bottom, text="No product sales today.", text_color=TEXT_COLOR).pack(anchor="w", padx=8, pady=2)

class CafeApp(ctk.CTk):
    """Main application window for the cafe automation system."""

    def __init__(self):
        super().__init__()
        self.title("Cafe Automation")
        self.geometry("1140x700")
        self.configure(fg_color=BG_COLOR)

        self.selected_table_id = None
        self.table_buttons = {}

        left = ctk.CTkFrame(self, fg_color="#1f1f1f", corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        right = ctk.CTkFrame(self, fg_color="#1f1f1f", corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)

        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.tables = db.fetch_tables()
        grid = ctk.CTkFrame(left, fg_color="#262626", corner_radius=12)
        grid.pack(fill="both", expand=True, padx=12, pady=12)

        for i, table in enumerate(self.tables):
            r = i // 5
            c = i % 5
            btn = ctk.CTkButton(grid, text=self.button_text(table), corner_radius=12, command=lambda tid=table['id']: self.select_table(tid))
            btn.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
            grid.grid_columnconfigure(c, weight=1)
            grid.grid_rowconfigure(r, weight=1)
            self.table_buttons[table['id']] = btn
            self.update_table_color(table['id'], table['status'])

        self.right_title = ctk.CTkLabel(right, text="No Table Selected", text_color=TEXT_COLOR, font=("Segoe UI", 18, "bold"))
        self.right_title.pack(pady=(12, 8))

        self.right_details = ctk.CTkLabel(right, text="Hardware: -\nStatus: -", text_color=TEXT_COLOR, justify="left")
        self.right_details.pack(pady=8)

        self.right_orders_title = ctk.CTkLabel(right, text="Active Orders", text_color=TEXT_COLOR, font=("Segoe UI", 14, "bold"))
        self.right_orders_title.pack(pady=(10, 4))
        self.right_orders_list = ctk.CTkScrollableFrame(right, fg_color="#262626", corner_radius=12)
        self.right_orders_list.pack(fill="both", expand=True, padx=12, pady=6)

        btns = ctk.CTkFrame(right, fg_color="#262626", corner_radius=12)
        btns.pack(fill="x", padx=12, pady=12)

        self.btn_session = ctk.CTkButton(btns, text="Start Session", corner_radius=12, command=self.start_session)
        self.btn_session.pack(fill="x", padx=8, pady=6)

        self.btn_order = ctk.CTkButton(btns, text="Add Order", corner_radius=12, command=self.add_order)
        self.btn_order.pack(fill="x", padx=8, pady=6)

        self.btn_bill = ctk.CTkButton(btns, text="Close Bill", corner_radius=12, command=self.close_bill)
        self.btn_bill.pack(fill="x", padx=8, pady=6)

        self.btn_out = ctk.CTkButton(btns, text="Mark Out of Order", corner_radius=12, command=self.mark_out_of_order)
        self.btn_out.pack(fill="x", padx=8, pady=6)

        self.btn_report = ctk.CTkButton(right, text="End of Day Report", corner_radius=12, command=self.open_report)
        self.btn_report.pack(fill="x", padx=12, pady=8)

    def button_text(self, table: dict) -> str:
        """Compose button label text for a table."""
        return f"{table['name']}\n{table['kind']}\n{table['status']}"

    def update_table_color(self, table_id: int, status: str):
        """Set button color based on table status."""
        btn = self.table_buttons.get(table_id)
        if not btn:
            return
        color = COLOR_MAP.get(status, COLOR_MAP["DEFAULT"])
        btn.configure(fg_color=color)

    def select_table(self, table_id: int):
        """Handle table selection and refresh right panel."""
        self.selected_table_id = table_id
        table = db.fetch_table(table_id)
        if not table:
            return
        self.right_title.configure(text=table['name'])
        self.right_details.configure(text=f"Hardware: {table['hardware']}\nStatus: {table['status']}")
        self.refresh_order_list()

    def refresh_order_list(self):
        """Refresh active orders list for the selected table."""
        for widget in self.right_orders_list.winfo_children():
            widget.destroy()
        if self.selected_table_id is None:
            return
        rows = db.fetch_active_session_orders(self.selected_table_id)
        if not rows:
            ctk.CTkLabel(self.right_orders_list, text="No orders.", text_color=TEXT_COLOR).pack(anchor="w", padx=8, pady=4)
            return
        for row in rows:
            text = f"{row['total_qty']}x {row['name']} - {row['total_amount']:.2f} TL"
            ctk.CTkLabel(self.right_orders_list, text=text, text_color=TEXT_COLOR).pack(anchor="w", padx=8, pady=4)

    def start_session(self):
        """Open session start popup for the selected table."""
        if self.selected_table_id is None:
            messagebox.showwarning("Warning", "Please select a table.")
            return
        table = db.fetch_table(self.selected_table_id)
        if not table:
            return
        if table['status'] == STATUS_OUT_OF_ORDER:
            messagebox.showerror("Error", "Cannot start a session on an out-of-order table.")
            return
        popup = SessionStartWindow(self, self.selected_table_id)
        self.wait_window(popup)
        self.refresh_tables()
        self.refresh_right_panel_details()
        self.refresh_order_list()

    def add_order(self):
        """Open order popup if table has an active session."""
        if self.selected_table_id is None:
            messagebox.showwarning("Warning", "Please select a table.")
            return
        table = db.fetch_table(self.selected_table_id)
        if not table or table['status'] != STATUS_OCCUPIED:
            messagebox.showerror("Error", "No active session; start a session first.")
            return
        popup = OrderWindow(self, self.selected_table_id)
        self.wait_window(popup)
        self.refresh_order_list()

    def close_bill(self):
        """Close the session, show a summary, and refresh UI."""
        if self.selected_table_id is None:
            messagebox.showwarning("Warning", "Please select a table.")
            return
        table = db.fetch_table(self.selected_table_id)
        if not table or table['status'] != STATUS_OCCUPIED:
            messagebox.showerror("Error", "No active session.")
            return
        line_items = db.fetch_active_session_orders(self.selected_table_id)
        orders_total = db.get_active_session_order_total(self.selected_table_id)
        time_charge, minutes = db.end_session(self.selected_table_id)
        total = round(orders_total + time_charge, 2)
        header = f"Table: {table['name']} ({table['kind']})\nDuration: {minutes} min ({time_charge:.1f} TL)"
        lines = "\n".join([f"- {k['total_qty']}x {k['name']} ({k['total_amount']:.0f} TL)" for k in line_items]) if line_items else "(No orders)"
        text = (
            "-------------------\n" +
            header +
            "\n-------------------\nOrders:\n" +
            lines +
            f"\n-------------------\nTOTAL: {total:.1f} TL"
        )
        messagebox.showinfo("Bill Summary", text)
        self.refresh_tables()
        self.refresh_right_panel_details()
        self.refresh_order_list()

    def mark_out_of_order(self):
        """Mark selected table as out of order and refresh UI."""
        if self.selected_table_id is None:
            messagebox.showwarning("Warning", "Please select a table.")
            return
        db.mark_table_out_of_order(self.selected_table_id)
        table = db.fetch_table(self.selected_table_id)
        if table:
            btn = self.table_buttons.get(self.selected_table_id)
            if btn:
                btn.configure(text=self.button_text(table))
                self.update_table_color(self.selected_table_id, table['status'])
            self.right_details.configure(text=f"Hardware: {table['hardware']}\nStatus: {table['status']}")
        self.refresh_order_list()

    def open_report(self):
        """Open end-of-day report window."""
        EndOfDayReportWindow(self)

    def refresh_tables(self):
        """Reload tables from DB and refresh button labels/colors."""
        self.tables = db.fetch_tables()
        for t in self.tables:
            btn = self.table_buttons.get(t['id'])
            if btn:
                btn.configure(text=self.button_text(t))
                self.update_table_color(t['id'], t['status'])

    def refresh_right_panel_details(self):
        """Refresh right panel details for the selected table."""
        if self.selected_table_id is None:
            return
        table = db.fetch_table(self.selected_table_id)
        if table:
            self.right_details.configure(text=f"Hardware: {table['hardware']}\nStatus: {table['status']}")

if __name__ == "__main__":
    try:
        db.init_db()
    except Exception as exc:
        messagebox.showerror("Database Error", f"Failed to initialize database: {exc}")
        sys.exit(1)

    app = CafeApp()
    app.mainloop()