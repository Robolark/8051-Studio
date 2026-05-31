import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import subprocess
import os
import sys
import json

APP_NAME = "Robolark 8051 Studio V2"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def app_folder():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

SDCC_EXE = resource_path(os.path.join("sdcc", "bin", "sdcc.exe"))
PACKIHX_EXE = resource_path(os.path.join("sdcc", "bin", "packihx.exe"))
CONFIG_FILE = os.path.join(app_folder(), "robolark_8051_config.json")

current_file = None
last_hex_file = None

root = tk.Tk()
root.title(APP_NAME)
root.geometry("1150x750")
root.configure(bg="#1e1e1e")

def log(message):
    output_box.insert(tk.END, message + "\n")
    output_box.see(tk.END)

def clear_log():
    output_box.delete("1.0", tk.END)

def save_config():
    data = {
        "programmer": programmer_var.get(),
        "com_port": com_var.get(),
        "baud": baud_var.get(),
        "uploader_path": uploader_path_var.get(),
        "custom_command": custom_command_var.get(),
        "chip": chip_var.get()
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            programmer_var.set(data.get("programmer", "Manual HEX Export Only"))
            com_var.set(data.get("com_port", ""))
            baud_var.set(data.get("baud", "115200"))
            uploader_path_var.set(data.get("uploader_path", ""))
            custom_command_var.set(data.get("custom_command", ""))
            chip_var.set(data.get("chip", "AT89S52"))
        except Exception:
            pass

def new_file():
    global current_file, last_hex_file
    current_file = None
    last_hex_file = None
    editor.delete("1.0", tk.END)
    clear_log()
    root.title(APP_NAME)

def open_file():
    global current_file
    path = filedialog.askopenfilename(
        filetypes=[("C Files", "*.c"), ("ASM Files", "*.asm"), ("All Files", "*.*")]
    )
    if path:
        current_file = path
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            editor.delete("1.0", tk.END)
            editor.insert(tk.END, f.read())
        root.title(f"{APP_NAME} - {os.path.basename(path)}")

def save_file():
    global current_file
    if current_file is None:
        current_file = filedialog.asksaveasfilename(
            defaultextension=".c",
            filetypes=[("C Files", "*.c"), ("All Files", "*.*")]
        )
    if current_file:
        with open(current_file, "w", encoding="utf-8") as f:
            f.write(editor.get("1.0", tk.END))
        root.title(f"{APP_NAME} - {os.path.basename(current_file)}")
    return current_file

def compile_code():
    global current_file, last_hex_file

    save_file()
    if not current_file:
        return None

    clear_log()

    if not os.path.exists(SDCC_EXE):
        messagebox.showerror("Missing SDCC", "sdcc.exe not found inside this application.")
        return None

    if not os.path.exists(PACKIHX_EXE):
        messagebox.showerror("Missing PACKIHX", "packihx.exe not found inside this application.")
        return None

    project_folder = os.path.dirname(current_file)
    file_name = os.path.basename(current_file)
    base_name = os.path.splitext(current_file)[0]
    ihx_file = base_name + ".ihx"
    hex_file = base_name + ".hex"

    log("Compiling using bundled SDCC...")
    log(f"Source: {current_file}")
    log("")

    result = subprocess.run(
        [SDCC_EXE, "-mmcs51", file_name],
        cwd=project_folder,
        capture_output=True,
        text=True
    )

    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(result.stderr)

    if os.path.exists(ihx_file):
        with open(hex_file, "w", encoding="utf-8") as out:
            pack_result = subprocess.run(
                [PACKIHX_EXE, ihx_file],
                cwd=project_folder,
                stdout=out,
                stderr=subprocess.PIPE,
                text=True
            )
        if pack_result.stderr:
            log(pack_result.stderr)

        last_hex_file = hex_file
        log("")
        log("HEX generated successfully.")
        log(f"HEX Path: {hex_file}")
        messagebox.showinfo("Success", f"HEX generated:\n{hex_file}")
        return hex_file

    log("")
    log("Compilation failed. HEX not generated.")
    messagebox.showerror("Compilation Failed", "HEX file was not generated. Check build output.")
    return None

def compile_and_upload():
    hex_file = compile_code()
    if hex_file:
        upload_hex(hex_file)

def select_hex_file():
    global last_hex_file
    path = filedialog.askopenfilename(
        filetypes=[("HEX Files", "*.hex"), ("All Files", "*.*")]
    )
    if path:
        last_hex_file = path
        log(f"Selected HEX: {path}")

def open_hex_folder():
    path = last_hex_file
    if not path and current_file:
        possible = os.path.splitext(current_file)[0] + ".hex"
        if os.path.exists(possible):
            path = possible

    if not path or not os.path.exists(path):
        messagebox.showwarning("No HEX", "No HEX file found. Compile first.")
        return

    folder = os.path.dirname(path)
    try:
        os.startfile(folder)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def refresh_ports():
    ports = []
    try:
        import serial.tools.list_ports
        ports = [p.device for p in serial.tools.list_ports.comports()]
    except Exception:
        ports = [f"COM{i}" for i in range(1, 31)]

    com_dropdown["values"] = ports
    if ports and not com_var.get():
        com_var.set(ports[0])

def browse_uploader():
    path = filedialog.askopenfilename(
        filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
    )
    if path:
        uploader_path_var.set(path)
        save_config()

def build_upload_command(hex_file):
    method = programmer_var.get()
    chip = chip_var.get()
    com = com_var.get()
    baud = baud_var.get()
    uploader = uploader_path_var.get()
    custom = custom_command_var.get().strip()

    if method == "Manual HEX Export Only":
        return None

    if method == "Custom Command":
        if not custom:
            messagebox.showerror("Missing Command", "Enter custom upload command.")
            return None
        return custom.replace("{hex}", hex_file).replace("{com}", com).replace("{baud}", baud).replace("{chip}", chip)

    if method == "STC ISP Software":
        if not uploader:
            messagebox.showerror("Missing Uploader", "Select STC-ISP executable path.")
            return None
        return f'"{uploader}" "{hex_file}"'

    if method == "ProgISP / USBASP Tool":
        if not uploader:
            messagebox.showerror("Missing Uploader", "Select ProgISP or programmer executable path.")
            return None
        return f'"{uploader}" "{hex_file}"'

    if method == "AVRDUDE USBASP for AT89S52":
        if not uploader:
            messagebox.showerror("Missing AVRDUDE", "Select avrdude.exe path.")
            return None
        return f'"{uploader}" -c usbasp -p {chip} -U flash:w:"{hex_file}":i'

    return None

def upload_hex(hex_file=None):
    global last_hex_file
    save_config()

    if hex_file is None:
        hex_file = last_hex_file

    if not hex_file and current_file:
        possible = os.path.splitext(current_file)[0] + ".hex"
        if os.path.exists(possible):
            hex_file = possible

    if not hex_file or not os.path.exists(hex_file):
        messagebox.showwarning("No HEX", "Compile first or select a HEX file.")
        return

    method = programmer_var.get()

    if method == "Manual HEX Export Only":
        messagebox.showinfo(
            "Manual Upload",
            f"HEX is ready:\n{hex_file}\n\nUse your programmer software to upload this HEX file."
        )
        return

    command = build_upload_command(hex_file)
    if not command:
        return

    log("")
    log("Uploading...")
    log(f"Method: {method}")
    log(f"Command: {command}")
    log("")

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.stdout:
            log(result.stdout)
        if result.stderr:
            log(result.stderr)

        if result.returncode == 0:
            log("Upload command completed.")
            messagebox.showinfo("Upload", "Upload command completed. Check console for status.")
        else:
            log(f"Upload command failed. Return code: {result.returncode}")
            messagebox.showerror("Upload Failed", "Upload command failed. Check console output.")

    except Exception as e:
        messagebox.showerror("Upload Error", str(e))

def load_led_blink_p10():
    sample = """#include <8051.h>

void delay()
{
    unsigned int i, j;
    for(i = 0; i < 1000; i++)
    {
        for(j = 0; j < 100; j++);
    }
}

void main()
{
    while(1)
    {
        P1_0 = 1;
        delay();

        P1_0 = 0;
        delay();
    }
}
"""
    editor.delete("1.0", tk.END)
    editor.insert(tk.END, sample)

def load_led_blink_p11():
    sample = """#include <8051.h>

void delay()
{
    unsigned int i, j;
    for(i = 0; i < 1000; i++)
    {
        for(j = 0; j < 100; j++);
    }
}

void main()
{
    while(1)
    {
        P1_1 = 1;
        delay();

        P1_1 = 0;
        delay();
    }
}
"""
    editor.delete("1.0", tk.END)
    editor.insert(tk.END, sample)

def load_bare_template():
    sample = """#include <8051.h>

void main()
{
    while(1)
    {
        // Write your code here
    }
}
"""
    editor.delete("1.0", tk.END)
    editor.insert(tk.END, sample)

topbar = tk.Frame(root, bg="#2b2b2b")
topbar.pack(fill=tk.X)

btn_style = {
    "bg": "#3c3f41",
    "fg": "white",
    "font": ("Segoe UI", 10, "bold"),
    "bd": 0,
    "padx": 10,
    "pady": 5
}

tk.Button(topbar, text="New", command=new_file, **btn_style).pack(side=tk.LEFT, padx=4, pady=5)
tk.Button(topbar, text="Open", command=open_file, **btn_style).pack(side=tk.LEFT, padx=4, pady=5)
tk.Button(topbar, text="Save", command=save_file, **btn_style).pack(side=tk.LEFT, padx=4, pady=5)

tk.Button(topbar, text="Compile HEX", command=compile_code, bg="#007acc", fg="white",
          font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=5).pack(side=tk.LEFT, padx=8, pady=5)

tk.Button(topbar, text="Compile + Upload", command=compile_and_upload, bg="#188038", fg="white",
          font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=5).pack(side=tk.LEFT, padx=4, pady=5)

tk.Button(topbar, text="Open HEX Folder", command=open_hex_folder, **btn_style).pack(side=tk.LEFT, padx=4, pady=5)

main = tk.Frame(root, bg="#1e1e1e")
main.pack(fill=tk.BOTH, expand=True)

left = tk.Frame(main, bg="#252526", width=270)
left.pack(side=tk.LEFT, fill=tk.Y)
left.pack_propagate(False)

right = tk.Frame(main, bg="#1e1e1e")
right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

tk.Label(left, text="8051 Project Templates", bg="#252526", fg="white",
         font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(12, 6))

tk.Button(left, text="LED Blink P1.0", command=load_led_blink_p10, **btn_style).pack(fill=tk.X, padx=10, pady=3)
tk.Button(left, text="LED Blink P1.1", command=load_led_blink_p11, **btn_style).pack(fill=tk.X, padx=10, pady=3)
tk.Button(left, text="Bare Template", command=load_bare_template, **btn_style).pack(fill=tk.X, padx=10, pady=3)

tk.Label(left, text="Programmer Settings", bg="#252526", fg="white",
         font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(18, 6))

programmer_var = tk.StringVar(value="Manual HEX Export Only")
chip_var = tk.StringVar(value="AT89S52")
com_var = tk.StringVar(value="")
baud_var = tk.StringVar(value="115200")
uploader_path_var = tk.StringVar(value="")
custom_command_var = tk.StringVar(value="")

tk.Label(left, text="Upload Method", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
programmer_dropdown = ttk.Combobox(
    left,
    textvariable=programmer_var,
    values=[
        "Manual HEX Export Only",
        "STC ISP Software",
        "ProgISP / USBASP Tool",
        "AVRDUDE USBASP for AT89S52",
        "Custom Command"
    ],
    state="readonly"
)
programmer_dropdown.pack(fill=tk.X, padx=10, pady=3)

tk.Label(left, text="Chip", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
chip_dropdown = ttk.Combobox(
    left,
    textvariable=chip_var,
    values=["AT89S52", "AT89S51", "AT89C51", "STC89C52", "STC15", "STC8", "m89s52"],
)
chip_dropdown.pack(fill=tk.X, padx=10, pady=3)

tk.Label(left, text="COM Port", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
com_dropdown = ttk.Combobox(left, textvariable=com_var)
com_dropdown.pack(fill=tk.X, padx=10, pady=3)
tk.Button(left, text="Refresh COM Ports", command=refresh_ports, **btn_style).pack(fill=tk.X, padx=10, pady=3)

tk.Label(left, text="Baud", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
tk.Entry(left, textvariable=baud_var).pack(fill=tk.X, padx=10, pady=3)

tk.Label(left, text="Uploader EXE Path", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
tk.Entry(left, textvariable=uploader_path_var).pack(fill=tk.X, padx=10, pady=3)
tk.Button(left, text="Browse Uploader", command=browse_uploader, **btn_style).pack(fill=tk.X, padx=10, pady=3)

tk.Label(left, text="Custom Command", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10, pady=(10, 0))
tk.Entry(left, textvariable=custom_command_var).pack(fill=tk.X, padx=10, pady=3)

tk.Label(left, text="Use placeholders: {hex}, {com}, {baud}, {chip}",
         bg="#252526", fg="#9cdcfe", wraplength=240, justify="left").pack(anchor="w", padx=10, pady=3)

tk.Button(left, text="Select HEX", command=select_hex_file, **btn_style).pack(fill=tk.X, padx=10, pady=(12, 3))
tk.Button(left, text="Upload HEX", command=lambda: upload_hex(), bg="#188038", fg="white",
          font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=5).pack(fill=tk.X, padx=10, pady=3)

tk.Label(left, text="Note: Classic AT89 chips usually need USBASP/ISP programmer. STC chips use serial ISP.",
         bg="#252526", fg="#cccccc", wraplength=240, justify="left").pack(anchor="w", padx=10, pady=(15, 3))

editor = tk.Text(
    right,
    bg="#1e1e1e",
    fg="#dcdcdc",
    insertbackground="white",
    font=("Consolas", 12),
    undo=True
)
editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

output_box = tk.Text(
    right,
    height=11,
    bg="#111111",
    fg="#00ff00",
    insertbackground="white",
    font=("Consolas", 10)
)
output_box.pack(fill=tk.X, padx=5, pady=5)

editor.insert(tk.END, """// Robolark 8051 Studio V2
// Write 8051 C code, compile HEX, and upload using selected programmer.
// Start with LED Blink P1.0 or P1.1 from the left side.
""")

programmer_dropdown.bind("<<ComboboxSelected>>", lambda e: save_config())
chip_dropdown.bind("<<ComboboxSelected>>", lambda e: save_config())

load_config()
refresh_ports()

root.mainloop()
