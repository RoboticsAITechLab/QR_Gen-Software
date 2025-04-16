import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
import qrcode
from PIL import Image, ImageTk, ImageDraw, ImageFont
import base64
import os
import time
import json
import datetime
import shutil  # For sharing QR code

# Ensure assets, logs, and user_data folders exist
if not os.path.exists("assets"):
    os.makedirs("assets")
if not os.path.exists("logs"):
    os.makedirs("logs")
if not os.path.exists("user_data"):
    os.makedirs("user_data")

def simple_encrypt(plaintext, key):
    key_bytes = key.encode('utf-8')
    plaintext_bytes = plaintext.encode('utf-8')
    encrypted_bytes = bytearray()
    for i, byte in enumerate(plaintext_bytes):
        encrypted_bytes.append(byte ^ key_bytes[i % len(key_bytes)])
    return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')

class AdvancedQRGenerator(ttk.Frame):
    def __init__(self, master=None, plugin_mode=False, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master
        self.plugin_mode = plugin_mode

        # Default global settings
        self.qr_color = "#000000"
        self.include_watermark = tk.BooleanVar(value=True)
        self.include_logo = tk.BooleanVar(value=False)
        self.box_size = tk.IntVar(value=10)
        self.border = tk.IntVar(value=4)
        self.logo_path = None
        self.current_theme = "dark"

        # QR type selection options
        self.qr_types = [
            "URL/Plain Text",
            "Payment Request",
            "WiFi Connection",
            "vCard Contact",
            "TOTP Authentication",
            "Event Ticket/Coupon",
            "Secure/Encrypted Text"
        ]
        self.selected_qr_type = tk.StringVar(value=self.qr_types[0])
        
        # Dictionary to hold dynamic input widget references
        self.inputs = {}
        self.saved_data = {qr_type: {} for qr_type in self.qr_types}  # To save user inputs
        self.load_saved_data()

        # Animation variables
        self.fade_alpha = 0
        self.scale_factor = 0.8

        # QR code history
        self.qr_history = []
        self.filtered_history = []  # For search functionality
        self.load_history()

        # Build UI
        self._build_ui()
        
        # Make the UI responsive
        self.master.bind("<Configure>", self._resize_ui)

    def load_saved_data(self):
        """Load previously saved user data from a JSON file."""
        try:
            with open("user_data/saved_inputs.json", "r") as f:
                self.saved_data = json.load(f)
        except FileNotFoundError:
            pass

    def save_user_data(self):
        """Save user inputs to a JSON file."""
        with open("user_data/saved_inputs.json", "w") as f:
            json.dump(self.saved_data, f, indent=4)

    def load_history(self):
        """Load QR code generation history from a JSON file."""
        try:
            with open("logs/qr_history.json", "r") as f:
                self.qr_history = json.load(f)
                self.filtered_history = self.qr_history.copy()
        except FileNotFoundError:
            self.qr_history = []
            self.filtered_history = []

    def save_history(self):
        """Save QR code generation history to a JSON file."""
        with open("logs/qr_history.json", "w") as f:
            json.dump(self.qr_history, f, indent=4)
        self.filtered_history = self.qr_history.copy()

    def _build_ui(self):
        self.master.title("ZyroTech | Advanced QR Code Generator")
        if not self.plugin_mode:
            self.master.geometry("1200x800")
        
        # Configure ttk style for a modern look
        style = ttk.Style()
        style.theme_use('clam')
        
        # Define themes
        self.themes = {
            "dark": {
                "background": "#1e1e2f",
                "foreground": "#e0e0e0",
                "fieldbackground": "#2a2a3b",
                "buttonbackground": "#3b82f6",
                "buttonforeground": "#ffffff",
                "highlight": "#3b82f6"
            },
            "light": {
                "background": "#f0f0f0",
                "foreground": "#333333",
                "fieldbackground": "#ffffff",
                "buttonbackground": "#007bff",
                "buttonforeground": "#ffffff",
                "highlight": "#007bff"
            }
        }

        self.configure(style="TFrame")
        self.grid(sticky="nsew", padx=20, pady=20)
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        # Header with logo, stats, and theme toggle
        header_frame = ttk.Frame(self, padding=(20, 10), style="TFrame")
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=1)
        header_frame.columnconfigure(2, weight=0)

        header_label = ttk.Label(header_frame, text="ZyroTech QR Code Generator", font=("Arial", 28, "bold"), style="TLabel")
        header_label.grid(row=0, column=0, sticky="w")

        # Stats label
        self.stats_label = ttk.Label(header_frame, text=f"Total QR Codes: {len(self.qr_history)}", font=("Arial", 12), style="TLabel")
        self.stats_label.grid(row=0, column=1, sticky="e", padx=10)

        # Theme toggle button
        theme_button = ttk.Button(header_frame, text="🌙 Toggle Theme", command=self.toggle_theme, style="TButton")
        theme_button.grid(row=0, column=2, sticky="e", padx=10)

        # Main content: Sidebar, Input Area, Preview Area
        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.grid(row=1, column=0, columnspan=3, sticky="nsew")
        
        # Sidebar for history and actions
        sidebar_frame = ttk.Frame(self.main_paned, style="TFrame")
        self.main_paned.add(sidebar_frame, weight=1)
        
        # Search bar for history
        search_frame = ttk.Frame(sidebar_frame, style="TFrame")
        search_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(search_frame, text="Search History:", style="TLabel").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_history)
        ttk.Entry(search_frame, textvariable=self.search_var, style="TEntry").pack(side="right", fill="x", expand=True)

        ttk.Label(sidebar_frame, text="History", font=("Arial", 16, "bold"), style="TLabel").pack(pady=10)
        self.history_listbox = tk.Listbox(sidebar_frame, font=("Arial", 12))
        self.history_listbox.pack(fill="both", expand=True, padx=10, pady=5)
        self.history_listbox.bind("<<ListboxSelect>>", self.show_history_details)
        
        # History action buttons
        history_btn_frame = ttk.Frame(sidebar_frame, style="TFrame")
        history_btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(history_btn_frame, text="View", command=self.show_history_details, style="TButton").pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(history_btn_frame, text="Update", command=self.update_history_entry, style="TButton").pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(history_btn_frame, text="Delete", command=self.delete_history_entry, style="TButton").pack(side="left", fill="x", expand=True, padx=2)
        
        # Export options
        export_frame = ttk.Frame(sidebar_frame, style="TFrame")
        export_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(export_frame, text="Export Logs", command=self.export_logs, style="TButton").pack(fill="x", pady=2)
        ttk.Button(export_frame, text="Export User Data", command=self.export_user_data, style="TButton").pack(fill="x", pady=2)
        ttk.Button(export_frame, text="Export All", command=self.export_all, style="TButton").pack(fill="x", pady=2)

        # Left Frame: Controls and dynamic inputs
        left_frame = ttk.Frame(self.main_paned, style="TFrame")
        self.main_paned.add(left_frame, weight=2)
        
        # QR Type selection
        type_frame = ttk.Frame(left_frame, style="TFrame")
        type_frame.pack(fill="x", pady=10)
        ttk.Label(type_frame, text="Select QR Code Type:", style="TLabel").pack(side="left")
        type_combo = ttk.Combobox(type_frame, textvariable=self.selected_qr_type, values=self.qr_types, state="readonly", style="TCombobox")
        type_combo.pack(side="right", fill="x", expand=True, padx=10)
        type_combo.bind("<<ComboboxSelected>>", self.update_dynamic_frame)
        
        # Common Options: QR color, box size, border, watermark, logo
        options_border_frame = tk.Frame(left_frame, bd=2)
        options_border_frame.pack(fill="x", pady=10)
        options_frame = ttk.LabelFrame(options_border_frame, text="QR Options", padding=15, style="CustomLabelFrame.TLabelframe")
        options_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        ttk.Button(options_frame, text="Pick QR Color", command=self.pick_color, style="TButton").pack(fill="x", pady=5)
        self.color_label = ttk.Label(options_frame, text=f"Color: {self.qr_color}", style="TLabel")
        self.color_label.pack(anchor="w", pady=5)
        
        ttk.Label(options_frame, text="Box Size:", style="TLabel").pack(anchor="w")
        ttk.Entry(options_frame, textvariable=self.box_size, width=5, style="TEntry").pack(anchor="w", pady=5)
        
        ttk.Label(options_frame, text="Border Width:", style="TLabel").pack(anchor="w")
        ttk.Entry(options_frame, textvariable=self.border, width=5, style="TEntry").pack(anchor="w", pady=5)
        
        ttk.Checkbutton(options_frame, text="Include ZyroTech Watermark", variable=self.include_watermark, style="TCheckbutton").pack(anchor="w", pady=5)
        
        ttk.Button(options_frame, text="Upload Logo", command=self.upload_logo, style="TButton").pack(fill="x", pady=5)
        ttk.Checkbutton(options_frame, text="Include Logo in Center", variable=self.include_logo, style="TCheckbutton").pack(anchor="w", pady=5)
        
        # Dynamic Input Frame
        dynamic_border_frame = tk.Frame(left_frame, bd=2)
        dynamic_border_frame.pack(fill="x", pady=10)
        self.dynamic_frame = ttk.LabelFrame(dynamic_border_frame, text="QR Data", padding=15, style="CustomLabelFrame.TLabelframe")
        self.dynamic_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Buttons for actions
        btn_frame = ttk.Frame(left_frame, style="TFrame")
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Generate QR Code", command=self.generate_qr, style="TButton").pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(btn_frame, text="Save Image", command=self.save_image, style="TButton").pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear, style="TButton").pack(side="left", fill="x", expand=True, padx=5)
        
        # Right Frame: Image preview, details, and share option
        right_frame = ttk.Frame(self.main_paned, style="TFrame")
        self.main_paned.add(right_frame, weight=2)
        
        ttk.Label(right_frame, text="QR Code Preview:", style="TLabel").pack(anchor="w")
        
        self.image_canvas = tk.Canvas(right_frame, highlightthickness=0)
        self.image_canvas.pack(fill="both", expand=True, pady=5)
        self.image_label = ttk.Label(self.image_canvas, style="TLabel")
        self.image_label_id = self.image_canvas.create_window(0, 0, window=self.image_label, anchor="center")
        
        self.image_canvas.bind("<Configure>", self._update_canvas_window)
        
        # Details frame for history
        self.details_frame = ttk.LabelFrame(right_frame, text="QR Code Details", padding=10, style="CustomLabelFrame.TLabelframe")
        self.details_frame.pack(fill="x", pady=10)
        self.details_text = tk.Text(self.details_frame, height=5, font=("Arial", 12))
        self.details_text.pack(fill="both", expand=True)
        
        # Share button
        ttk.Button(right_frame, text="Share QR Code", command=self.share_qr_code, style="TButton").pack(fill="x", pady=5)

        # Apply theme after all widgets are created
        self.apply_theme(self.current_theme)
        
        # Initialize dynamic inputs and history
        self.update_dynamic_frame()
        self.update_history_list()

    def _resize_ui(self, event=None):
        """Make the UI responsive to window resizing."""
        # Update canvas size
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        self.image_canvas.coords(self.image_label_id, canvas_width // 2, canvas_height // 2)

        # Adjust font sizes based on window size
        window_width = self.master.winfo_width()
        base_font_size = max(10, int(window_width / 100))
        header_font_size = max(20, int(window_width / 50))
        
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", base_font_size))
        style.configure("CustomLabelFrame.TLabelframe.Label", font=("Arial", base_font_size))
        self.history_listbox.configure(font=("Arial", base_font_size))
        self.details_text.configure(font=("Arial", base_font_size))

        # Update header font
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label) and child.cget("text") == "ZyroTech QR Code Generator":
                        child.configure(font=("Arial", header_font_size, "bold"))

    def apply_theme(self, theme):
        """Apply the selected theme to the UI."""
        colors = self.themes[theme]
        style = ttk.Style()
        style.configure("TFrame", background=colors["background"])
        style.configure("TLabel", background=colors["background"], foreground=colors["foreground"], font=("Arial", 12))
        style.configure("TButton", background=colors["buttonbackground"], foreground=colors["buttonforeground"], font=("Arial", 11, "bold"), borderwidth=0, padding=8)
        style.configure("TEntry", fieldbackground=colors["fieldbackground"], foreground=colors["foreground"], font=("Arial", 11))
        style.configure("TCheckbutton", background=colors["background"], foreground=colors["foreground"], font=("Arial", 11))
        style.configure("TCombobox", fieldbackground=colors["fieldbackground"], foreground=colors["foreground"], font=("Arial", 11))
        style.configure("CustomLabelFrame.TLabelframe", background=colors["background"])
        style.configure("CustomLabelFrame.TLabelframe.Label", background=colors["background"], foreground=colors["foreground"], font=("Arial", 12))
        style.map("TButton",
                  background=[("active", colors["buttonbackground"]), ("!active", colors["buttonbackground"])],
                  foreground=[("active", colors["buttonforeground"]), ("!active", colors["buttonforeground"])])
        
        if hasattr(self, 'image_canvas'):
            self.image_canvas.configure(bg=colors["background"])
        if hasattr(self, 'image_label'):
            self.image_label.configure(background=colors["background"])
        if hasattr(self, 'details_text'):
            self.details_text.configure(bg=colors["fieldbackground"], fg=colors["foreground"])
        if hasattr(self, 'history_listbox'):
            self.history_listbox.configure(bg=colors["background"], fg=colors["foreground"])
        
        for frame in self.winfo_children():
            for child in frame.winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg=colors["highlight"])

    def toggle_theme(self):
        """Toggle between dark and light themes."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(self.current_theme)

    def _update_canvas_window(self, event=None):
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        self.image_canvas.coords(self.image_label_id, canvas_width // 2, canvas_height // 2)

    def update_dynamic_frame(self, event=None):
        # Save current inputs before switching
        qrtype = self.selected_qr_type.get()
        for key, widget in self.inputs.items():
            if isinstance(widget, ttk.Entry):
                self.saved_data[qrtype][key] = widget.get()
            elif isinstance(widget, ttk.Combobox):
                self.saved_data[qrtype][key] = widget.get()
        self.save_user_data()
        
        self.fade_out_dynamic_frame()

    def fade_out_dynamic_frame(self):
        self.fade_alpha = 1.0
        self._fade_out_step()

    def _fade_out_step(self):
        if self.fade_alpha > 0:
            self.fade_alpha -= 0.1
            hex_value = f"{max(0, int(self.fade_alpha * 255)):02x}"
            for widget in self.dynamic_frame.winfo_children():
                widget.configure(foreground=f"#{hex_value}{hex_value}{hex_value}")
            self.master.after(50, self._fade_out_step)
        else:
            for widget in self.dynamic_frame.winfo_children():
                widget.destroy()
            self.inputs.clear()
            self._build_dynamic_inputs()
            self.fade_in_dynamic_frame()

    def fade_in_dynamic_frame(self):
        self.fade_alpha = 0.0
        self._fade_in_step()

    def _fade_in_step(self):
        if self.fade_alpha < 1:
            self.fade_alpha += 0.1
            hex_value = f"{max(0, int(self.fade_alpha * 255)):02x}"
            for widget in self.dynamic_frame.winfo_children():
                widget.configure(foreground=f"#{hex_value}{hex_value}{hex_value}")
            self.master.after(50, self._fade_in_step)

    def _build_dynamic_inputs(self):
        qrtype = self.selected_qr_type.get()
        
        if qrtype == "URL/Plain Text":
            ttk.Label(self.dynamic_frame, text="Enter Text or URL:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["text"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["text"].pack(fill="x", pady=3)
            self.inputs["text"].insert(0, self.saved_data[qrtype].get("text", ""))

        elif qrtype == "Payment Request":
            ttk.Label(self.dynamic_frame, text="Payee VPA (e.g., abc@bank):", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["vpa"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["vpa"].pack(fill="x", pady=3)
            self.inputs["vpa"].insert(0, self.saved_data[qrtype].get("vpa", ""))
            
            ttk.Label(self.dynamic_frame, text="Amount:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["amount"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["amount"].pack(fill="x", pady=3)
            self.inputs["amount"].insert(0, self.saved_data[qrtype].get("amount", ""))
            
            ttk.Label(self.dynamic_frame, text="Transaction Note:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["note"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["note"].pack(fill="x", pady=3)
            self.inputs["note"].insert(0, self.saved_data[qrtype].get("note", ""))

        elif qrtype == "WiFi Connection":
            ttk.Label(self.dynamic_frame, text="SSID:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["ssid"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["ssid"].pack(fill="x", pady=3)
            self.inputs["ssid"].insert(0, self.saved_data[qrtype].get("ssid", ""))
            
            ttk.Label(self.dynamic_frame, text="Password:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["wifi_pass"] = ttk.Entry(self.dynamic_frame, style="TEntry", show="*")
            self.inputs["wifi_pass"].pack(fill="x", pady=3)
            self.inputs["wifi_pass"].insert(0, self.saved_data[qrtype].get("wifi_pass", ""))
            
            ttk.Label(self.dynamic_frame, text="Encryption:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["encryption"] = ttk.Combobox(self.dynamic_frame, values=["WPA", "WEP", "nopass"], state="readonly", style="TCombobox")
            self.inputs["encryption"].set(self.saved_data[qrtype].get("encryption", "WPA"))
            self.inputs["encryption"].pack(fill="x", pady=3)

        elif qrtype == "vCard Contact":
            ttk.Label(self.dynamic_frame, text="Name:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["name"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["name"].pack(fill="x", pady=3)
            self.inputs["name"].insert(0, self.saved_data[qrtype].get("name", ""))
            
            ttk.Label(self.dynamic_frame, text="Phone:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["phone"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["phone"].pack(fill="x", pady=3)
            self.inputs["phone"].insert(0, self.saved_data[qrtype].get("phone", ""))
            
            ttk.Label(self.dynamic_frame, text="Email:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["email"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["email"].pack(fill="x", pady=3)
            self.inputs["email"].insert(0, self.saved_data[qrtype].get("email", ""))
            
            ttk.Label(self.dynamic_frame, text="Address:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["address"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["address"].pack(fill="x", pady=3)
            self.inputs["address"].insert(0, self.saved_data[qrtype].get("address", ""))

        elif qrtype == "TOTP Authentication":
            ttk.Label(self.dynamic_frame, text="Account Name:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["account"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["account"].pack(fill="x", pady=3)
            self.inputs["account"].insert(0, self.saved_data[qrtype].get("account", ""))
            
            ttk.Label(self.dynamic_frame, text="Issuer:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["issuer"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["issuer"].pack(fill="x", pady=3)
            self.inputs["issuer"].insert(0, self.saved_data[qrtype].get("issuer", ""))
            
            ttk.Label(self.dynamic_frame, text="Secret (Base32):", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["secret"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["secret"].pack(fill="x", pady=3)
            self.inputs["secret"].insert(0, self.saved_data[qrtype].get("secret", ""))

        elif qrtype == "Event Ticket/Coupon":
            ttk.Label(self.dynamic_frame, text="Event/Offer Name:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["event"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["event"].pack(fill="x", pady=3)
            self.inputs["event"].insert(0, self.saved_data[qrtype].get("event", ""))
            
            ttk.Label(self.dynamic_frame, text="Date/Time:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["datetime"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["datetime"].pack(fill="x", pady=3)
            self.inputs["datetime"].insert(0, self.saved_data[qrtype].get("datetime", ""))
            
            ttk.Label(self.dynamic_frame, text="Venue (Optional):", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["venue"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["venue"].pack(fill="x", pady=3)
            self.inputs["venue"].insert(0, self.saved_data[qrtype].get("venue", ""))
            
            ttk.Label(self.dynamic_frame, text="Details:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["details"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["details"].pack(fill="x", pady=3)
            self.inputs["details"].insert(0, self.saved_data[qrtype].get("details", ""))

        elif qrtype == "Secure/Encrypted Text":
            ttk.Label(self.dynamic_frame, text="Plain Text:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["plain"] = ttk.Entry(self.dynamic_frame, style="TEntry")
            self.inputs["plain"].pack(fill="x", pady=3)
            self.inputs["plain"].insert(0, self.saved_data[qrtype].get("plain", ""))
            
            ttk.Label(self.dynamic_frame, text="Encryption Key:", style="TLabel").pack(anchor="w", pady=3)
            self.inputs["key"] = ttk.Entry(self.dynamic_frame, style="TEntry", show="*")
            self.inputs["key"].pack(fill="x", pady=3)
            self.inputs["key"].insert(0, self.saved_data[qrtype].get("key", ""))

    def pick_color(self):
        color_code = colorchooser.askcolor(title="Choose QR Code Color")
        if color_code[1]:
            self.qr_color = color_code[1]
            self.color_label.config(text=f"Color: {self.qr_color}")

    def upload_logo(self):
        file_path = filedialog.askopenfilename(
            title="Select Logo Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self.logo_path = file_path
            logo_filename = f"assets/logo_{int(time.time())}.png"
            Image.open(file_path).save(logo_filename)
            self.logo_path = logo_filename
            messagebox.showinfo("Success", "Logo uploaded successfully!")

    def apply_watermark(self, img, watermark_text="ZyroTech"):
        watermark = Image.new("RGBA", img.size)
        draw = ImageDraw.Draw(watermark)
        try:
            font = ImageFont.truetype("arial.ttf", int(img.size[1] * 0.05))
        except IOError:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", int(img.size[1] * 0.05))
            except IOError:
                font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = (img.size[0] - text_width - 10, img.size[1] - text_height - 10)
        draw.text(position, watermark_text, font=font, fill=(255, 255, 255, 128))
        watermarked = Image.alpha_composite(img.convert("RGBA"), watermark)
        return watermarked.convert("RGB")

    def apply_logo(self, img):
        if not self.logo_path:
            messagebox.showwarning("Warning", "No logo uploaded! Please upload a logo first.")
            return img
        
        try:
            logo = Image.open(self.logo_path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load logo: {e}")
            return img
        
        qr_width, qr_height = img.size
        logo_size = int(min(qr_width, qr_height) * 0.2)
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        logo_position = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
        qr_rgba = img.convert("RGBA")
        qr_rgba.paste(logo, logo_position, logo)
        return qr_rgba.convert("RGB")

    def generate_qr(self):
        qrtype = self.selected_qr_type.get()
        payload = ""
        
        try:
            box_size = self.box_size.get()
            border = self.border.get()
            if box_size < 1 or border < 0:
                raise ValueError
        except (tk.TclError, ValueError):
            messagebox.showerror("Error", "Box Size must be a positive integer and Border must be a non-negative integer!")
            return
        
        if qrtype == "URL/Plain Text":
            text = self.inputs.get("text").get().strip()
            if not text:
                messagebox.showerror("Error", "Please enter text or URL!")
                return
            payload = text

        elif qrtype == "Payment Request":
            vpa = self.inputs.get("vpa").get().strip()
            amount = self.inputs.get("amount").get().strip()
            note = self.inputs.get("note").get().strip()
            if not vpa or not amount:
                messagebox.showerror("Error", "Please enter at least the VPA and amount!")
                return
            payload = f"upi://pay?pa={vpa}&am={amount}&tn={note}"

        elif qrtype == "WiFi Connection":
            ssid = self.inputs.get("ssid").get().strip()
            wifi_pass = self.inputs.get("wifi_pass").get().strip()
            encryption = self.inputs.get("encryption").get().strip()
            if not ssid:
                messagebox.showerror("Error", "Please enter the SSID!")
                return
            payload = f"WIFI:T:{encryption};S:{ssid};P:{wifi_pass};;"

        elif qrtype == "vCard Contact":
            name = self.inputs.get("name").get().strip()
            phone = self.inputs.get("phone").get().strip()
            email = self.inputs.get("email").get().strip()
            address = self.inputs.get("address").get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter the name!")
                return
            payload = f"BEGIN:VCARD\nVERSION:3.0\nN:{name}\nTEL:{phone}\nEMAIL:{email}\nADR:{address}\nEND:VCARD"

        elif qrtype == "TOTP Authentication":
            account = self.inputs.get("account").get().strip()
            issuer = self.inputs.get("issuer").get().strip()
            secret = self.inputs.get("secret").get().strip()
            if not account or not issuer or not secret:
                messagebox.showerror("Error", "Please fill in all TOTP fields!")
                return
            payload = f"otpauth://totp/{issuer}:{account}?secret={secret}&issuer={issuer}"

        elif qrtype == "Event Ticket/Coupon":
            event = self.inputs.get("event").get().strip()
            datetime_val = self.inputs.get("datetime").get().strip()
            venue = self.inputs.get("venue").get().strip()
            details = self.inputs.get("details").get().strip()
            if not event or not datetime_val:
                messagebox.showerror("Error", "Please enter at least the event name and date/time!")
                return
            payload = f"Event: {event}\nDate/Time: {datetime_val}\nVenue: {venue}\nDetails: {details}"

        elif qrtype == "Secure/Encrypted Text":
            plain = self.inputs.get("plain").get().strip()
            key = self.inputs.get("key").get().strip()
            if not plain or not key:
                messagebox.showerror("Error", "Please provide both text and an encryption key!")
                return
            payload = simple_encrypt(plain, key)

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            box_size=box_size,
            border=border
        )
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color=self.qr_color, back_color="white").convert("RGB")
        
        if self.include_watermark.get():
            img = self.apply_watermark(img)
        
        if self.include_logo.get():
            img = self.apply_logo(img)
        
        # Save QR code with timestamp
        timestamp = int(time.time())
        img_path = f"assets/qr_{timestamp}.png"
        img.save(img_path)

        # Log the generation
        log_entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "qr_type": qrtype,
            "payload": payload,
            "qr_color": self.qr_color,
            "box_size": box_size,
            "border": border,
            "watermark": self.include_watermark.get(),
            "logo_path": self.logo_path,
            "output_path": img_path
        }
        self.qr_history.append(log_entry)
        self.save_history()
        self.update_history_list()
        self.stats_label.config(text=f"Total QR Codes: {len(self.qr_history)}")
        
        self.show_image(img_path)

    def filter_history(self, *args):
        """Filter history based on search term."""
        search_term = self.search_var.get().lower()
        self.filtered_history = [
            entry for entry in self.qr_history
            if search_term in entry["qr_type"].lower() or search_term in entry["payload"].lower()
        ]
        self.update_history_list()

    def update_history_list(self):
        """Update the history listbox with QR code generation history."""
        self.history_listbox.delete(0, tk.END)
        for entry in self.filtered_history:
            self.history_listbox.insert(tk.END, f"{entry['timestamp']} - {entry['qr_type']}")

    def show_history_details(self, event=None):
        """Show details of the selected QR code from history."""
        selection = self.history_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        entry = self.filtered_history[index]
        
        details = f"Timestamp: {entry['timestamp']}\n"
        details += f"QR Type: {entry['qr_type']}\n"
        details += f"Payload: {entry['payload']}\n"
        details += f"QR Color: {entry['qr_color']}\n"
        details += f"Box Size: {entry['box_size']}\n"
        details += f"Border: {entry['border']}\n"
        details += f"Watermark: {entry['watermark']}\n"
        details += f"Logo Path: {entry['logo_path']}\n"
        details += f"Output Path: {entry['output_path']}\n"
        
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, details)
        
        self.show_image(entry["output_path"])

    def update_history_entry(self):
        """Update the selected history entry."""
        selection = self.history_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a history entry to update!")
            return
        index = selection[0]
        entry = self.filtered_history[index]
        
        # Load the entry data into the input fields
        self.selected_qr_type.set(entry["qr_type"])
        self.update_dynamic_frame()
        
        # Populate the inputs
        if entry["qr_type"] == "URL/Plain Text":
            self.inputs["text"].delete(0, tk.END)
            self.inputs["text"].insert(0, entry["payload"])
        elif entry["qr_type"] == "Payment Request":
            parts = entry["payload"].split("?pa=")[1].split("&am=")
            vpa = parts[0]
            amount = parts[1].split("&tn=")[0]
            note = parts[1].split("&tn=")[1]
            self.inputs["vpa"].delete(0, tk.END)
            self.inputs["vpa"].insert(0, vpa)
            self.inputs["amount"].delete(0, tk.END)
            self.inputs["amount"].insert(0, amount)
            self.inputs["note"].delete(0, tk.END)
            self.inputs["note"].insert(0, note)
        elif entry["qr_type"] == "WiFi Connection":
            parts = entry["payload"].split(";")
            encryption = parts[0].split(":")[1]
            ssid = parts[1].split(":")[1]
            wifi_pass = parts[2].split(":")[1]
            self.inputs["ssid"].delete(0, tk.END)
            self.inputs["ssid"].insert(0, ssid)
            self.inputs["wifi_pass"].delete(0, tk.END)
            self.inputs["wifi_pass"].insert(0, wifi_pass)
            self.inputs["encryption"].set(encryption)
        # Add similar logic for other QR types as needed

        self.qr_color = entry["qr_color"]
        self.color_label.config(text=f"Color: {self.qr_color}")
        self.box_size.set(entry["box_size"])
        self.border.set(entry["border"])
        self.include_watermark.set(entry["watermark"])
        self.logo_path = entry["logo_path"]
        self.include_logo.set(bool(self.logo_path))

        # Remove the old entry after updating
        original_index = self.qr_history.index(entry)
        self.qr_history.pop(original_index)
        self.save_history()
        self.update_history_list()

    def delete_history_entry(self):
        """Delete the selected history entry."""
        selection = self.history_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a history entry to delete!")
            return
        index = selection[0]
        entry = self.filtered_history[index]
        original_index = self.qr_history.index(entry)
        self.qr_history.pop(original_index)
        self.save_history()
        self.update_history_list()
        self.stats_label.config(text=f"Total QR Codes: {len(self.qr_history)}")
        self.details_text.delete(1.0, tk.END)

    def export_logs(self):
        """Export QR code generation history to a text file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if file_path:
            with open(file_path, "w") as f:
                for entry in self.qr_history:
                    f.write(f"Timestamp: {entry['timestamp']}\n")
                    f.write(f"QR Type: {entry['qr_type']}\n")
                    f.write(f"Payload: {entry['payload']}\n")
                    f.write(f"QR Color: {entry['qr_color']}\n")
                    f.write(f"Box Size: {entry['box_size']}\n")
                    f.write(f"Border: {entry['border']}\n")
                    f.write(f"Watermark: {entry['watermark']}\n")
                    f.write(f"Logo Path: {entry['logo_path']}\n")
                    f.write(f"Output Path: {entry['output_path']}\n")
                    f.write("-" * 50 + "\n")
            messagebox.showinfo("Success", f"Logs exported to {file_path}")

    def export_user_data(self):
        """Export user saved data to a JSON file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            with open(file_path, "w") as f:
                json.dump(self.saved_data, f, indent=4)
            messagebox.showinfo("Success", f"User data exported to {file_path}")

    def export_all(self):
        """Export both logs and user data to a folder."""
        folder_path = filedialog.askdirectory(title="Select Folder to Export All Data")
        if folder_path:
            # Export logs
            log_file = os.path.join(folder_path, "qr_history.txt")
            with open(log_file, "w") as f:
                for entry in self.qr_history:
                    f.write(f"Timestamp: {entry['timestamp']}\n")
                    f.write(f"QR Type: {entry['qr_type']}\n")
                    f.write(f"Payload: {entry['payload']}\n")
                    f.write(f"QR Color: {entry['qr_color']}\n")
                    f.write(f"Box Size: {entry['box_size']}\n")
                    f.write(f"Border: {entry['border']}\n")
                    f.write(f"Watermark: {entry['watermark']}\n")
                    f.write(f"Logo Path: {entry['logo_path']}\n")
                    f.write(f"Output Path: {entry['output_path']}\n")
                    f.write("-" * 50 + "\n")
            
            # Export user data
            user_data_file = os.path.join(folder_path, "user_data.json")
            with open(user_data_file, "w") as f:
                json.dump(self.saved_data, f, indent=4)
            
            # Copy assets folder
            assets_dest = os.path.join(folder_path, "assets")
            if os.path.exists("assets"):
                shutil.copytree("assets", assets_dest, dirs_exist_ok=True)

            messagebox.showinfo("Success", f"All data exported to {folder_path}")

    def share_qr_code(self):
        """Share the current QR code (placeholder for sharing functionality)."""
        if not os.path.exists("assets/current.png"):
            messagebox.showwarning("Warning", "No QR code to share! Please generate a QR code first.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")]
        )
        if file_path:
            shutil.copy("assets/current.png", file_path)
            messagebox.showinfo("Success", f"QR code shared to {file_path}")

    def show_image(self, path):
        try:
            img = Image.open(path)
            max_size = min(self.image_canvas.winfo_width(), self.image_canvas.winfo_height()) - 20
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            img.save("assets/current.png")
            img_tk = ImageTk.PhotoImage(img)
            self.image_label.config(image=img_tk)
            self.image_label.image = img_tk
            
            self._update_canvas_window()
            self.scale_factor = 0.8
            self._zoom_in_image()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to display image: {e}")

    def _zoom_in_image(self):
        if self.scale_factor < 1.0:
            self.scale_factor += 0.02
            self.image_canvas.delete(self.image_label_id)
            self.image_label_id = self.image_canvas.create_window(
                self.image_canvas.winfo_width() // 2,
                self.image_canvas.winfo_height() // 2,
                window=self.image_label,
                anchor="center"
            )
            self.image_canvas.scale(self.image_label_id, self.image_canvas.winfo_width() // 2, self.image_canvas.winfo_height() // 2, self.scale_factor, self.scale_factor)
            self.master.after(20, self._zoom_in_image)

    def save_image(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg")]
        )
        if file_path:
            try:
                img = Image.open("assets/current.png")
                img.save(file_path)
                messagebox.showinfo("Saved", f"Image saved at {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")

    def clear(self):
        for widget in self.dynamic_frame.winfo_children():
            if isinstance(widget, ttk.Entry):
                widget.delete(0, tk.END)
            elif isinstance(widget, ttk.Combobox):
                widget.set(widget.cget("values")[0])
        self.image_label.config(image="")
        self.image_label.image = None
        self.logo_path = None
        self.include_logo.set(False)
        self.details_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedQRGenerator(master=root, plugin_mode=False)
    app.pack(fill="both", expand=True)
    root.mainloop()