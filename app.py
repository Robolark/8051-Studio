import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import subprocess
import os
import sys
import json
import threading
import time

APP_NAME = "Robolark Embedded Studio V3"


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
CONFIG_FILE = os.path.join(app_folder(), "robolark_embedded_studio_config.json")

current_file = None
last_hex_file = None
serial_obj = None
serial_thread_running = False

BOARD_PROFILES = {
    "AT89S52 - USBASP": {"chip": "m89s52", "method": "AVRDUDE USBASP", "notes": "Use USBASP programmer. Requires avrdude.exe path."},
    "AT89S51 - USBASP": {"chip": "m89s51", "method": "AVRDUDE USBASP", "notes": "Use USBASP programmer. Requires avrdude.exe path."},
    "AT89C51 - Manual HEX": {"chip": "AT89C51", "method": "Manual HEX Export Only", "notes": "AT89C51 usually needs external programmer. Generate HEX and upload manually."},
    "STC89C52 - Serial ISP": {"chip": "STC89C52", "method": "STC ISP / Custom Tool", "notes": "Use STC-ISP software or stcgal through custom command."},
    "STC8 Series - Serial ISP": {"chip": "STC8", "method": "STC ISP / Custom Tool", "notes": "Use STC-ISP software or stcgal through custom command."},
    "Nuvoton W78E052DDG - Serial ISP": {"chip": "W78E052DDG", "method": "Nuvoton ISP / Custom Tool", "notes": "8052-compatible Nuvoton chip. Use Nuvoton ISP/ICP tool or custom serial ISP command."},
    "Custom 8051": {"chip": "CUSTOM8051", "method": "Custom Command", "notes": "Use your own uploader command with placeholders."}
}

root = tk.Tk()
root.title(APP_NAME)
root.geometry("1280x780")
root.configure(bg="#1e1e1e")

board_var = tk.StringVar(value="AT89S52 - USBASP")
chip_var = tk.StringVar(value="m89s52")
upload_method_var = tk.StringVar(value="AVRDUDE USBASP")
com_var = tk.StringVar(value="")
baud_var = tk.StringVar(value="9600")
uploader_path_var = tk.StringVar(value="")
custom_command_var = tk.StringVar(value="")
serial_send_var = tk.StringVar(value="")


def log(message):
    output_box.insert(tk.END, str(message) + "\n")
    output_box.see(tk.END)


def clear_log():
    output_box.delete("1.0", tk.END)


def serial_log(message):
    serial_output.insert(tk.END, str(message))
    serial_output.see(tk.END)


def save_config():
    data = {
        "board": board_var.get(),
        "chip": chip_var.get(),
        "upload_method": upload_method_var.get(),
        "com_port": com_var.get(),
        "baud": baud_var.get(),
        "uploader_path": uploader_path_var.get(),
        "custom_command": custom_command_var.get()
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
            board_var.set(data.get("board", "AT89S52 - USBASP"))
            chip_var.set(data.get("chip", "m89s52"))
            upload_method_var.set(data.get("upload_method", "AVRDUDE USBASP"))
            com_var.set(data.get("com_port", ""))
            baud_var.set(data.get("baud", "9600"))
            uploader_path_var.set(data.get("uploader_path", ""))
            custom_command_var.set(data.get("custom_command", ""))
        except Exception:
            pass


def get_bare_template():
    return """#include <8051.h>\n\nvoid main()\n{\n    while(1)\n    {\n        // Write your code here\n    }\n}\n"""


def new_file():
    global current_file, last_hex_file
    current_file = None
    last_hex_file = None
    editor.delete("1.0", tk.END)
    clear_log()
    root.title(APP_NAME)
    editor.insert(tk.END, get_bare_template())


def open_file():
    global current_file
    path = filedialog.askopenfilename(filetypes=[("C Files", "*.c"), ("ASM Files", "*.asm"), ("All Files", "*.*")])
    if path:
        current_file = path
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            editor.delete("1.0", tk.END)
            editor.insert(tk.END, f.read())
        root.title(f"{APP_NAME} - {os.path.basename(path)}")


def save_file():
    global current_file
    if current_file is None:
        current_file = filedialog.asksaveasfilename(defaultextension=".c", filetypes=[("C Files", "*.c"), ("All Files", "*.*")])
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
    log("Robolark Embedded Studio V3")
    log("Compiling using bundled SDCC...")
    log(f"Board: {board_var.get()}")
    log(f"Source: {current_file}\n")
    result = subprocess.run([SDCC_EXE, "-mmcs51", file_name], cwd=project_folder, capture_output=True, text=True)
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(result.stderr)
    if os.path.exists(ihx_file):
        with open(hex_file, "w", encoding="utf-8") as out:
            pack_result = subprocess.run([PACKIHX_EXE, ihx_file], cwd=project_folder, stdout=out, stderr=subprocess.PIPE, text=True)
        if pack_result.stderr:
            log(pack_result.stderr)
        last_hex_file = hex_file
        log("\nHEX generated successfully.")
        log(f"HEX Path: {hex_file}")
        messagebox.showinfo("Success", f"HEX generated:\n{hex_file}")
        return hex_file
    log("\nCompilation failed. HEX not generated.")
    messagebox.showerror("Compilation Failed", "HEX file was not generated. Check build output.")
    return None


def compile_and_upload():
    hex_file = compile_code()
    if hex_file:
        upload_hex(hex_file)


def select_hex_file():
    global last_hex_file
    path = filedialog.askopenfilename(filetypes=[("HEX Files", "*.hex"), ("All Files", "*.*")])
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
    try:
        os.startfile(os.path.dirname(path))
    except Exception as e:
        messagebox.showerror("Error", str(e))


def browse_uploader():
    path = filedialog.askopenfilename(filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")])
    if path:
        uploader_path_var.set(path)
        save_config()


def build_upload_command(hex_file):
    method = upload_method_var.get()
    board = board_var.get()
    chip = chip_var.get()
    com = com_var.get()
    baud = baud_var.get()
    uploader = uploader_path_var.get()
    custom = custom_command_var.get().strip()
    if method == "Manual HEX Export Only":
        return None
    if method == "AVRDUDE USBASP":
        if not uploader:
            messagebox.showerror("Missing AVRDUDE", "Browse and select avrdude.exe.")
            return None
        return f'"{uploader}" -c usbasp -p {chip} -U flash:w:"{hex_file}":i'
    if method in ["STC ISP / Custom Tool", "Nuvoton ISP / Custom Tool"]:
        if custom:
            return custom.replace("{hex}", hex_file).replace("{com}", com).replace("{baud}", baud).replace("{chip}", chip).replace("{board}", board)
        if uploader:
            return f'"{uploader}" "{hex_file}"'
        messagebox.showerror("Missing Uploader", "Select uploader executable or enter custom command.")
        return None
    if method == "Custom Command":
        if not custom:
            messagebox.showerror("Missing Command", "Enter custom upload command.")
            return None
        return custom.replace("{hex}", hex_file).replace("{com}", com).replace("{baud}", baud).replace("{chip}", chip).replace("{board}", board)
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
    method = upload_method_var.get()
    if method == "Manual HEX Export Only":
        messagebox.showinfo("Manual Upload", f"HEX is ready:\n{hex_file}\n\nUse your external programmer software.")
        return
    command = build_upload_command(hex_file)
    if not command:
        return
    log("\nUploading...")
    log(f"Board: {board_var.get()}")
    log(f"Method: {method}")
    log(f"Command: {command}\n")
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


def serial_reader():
    global serial_thread_running, serial_obj
    while serial_thread_running and serial_obj:
        try:
            if serial_obj.in_waiting:
                data = serial_obj.read(serial_obj.in_waiting).decode(errors="ignore")
                serial_output.after(0, lambda d=data: serial_log(d))
            time.sleep(0.05)
        except Exception:
            break


def connect_serial():
    global serial_obj, serial_thread_running
    try:
        import serial
    except Exception:
        messagebox.showerror("Missing PySerial", "PySerial not available in this EXE.")
        return
    if serial_obj:
        disconnect_serial()
    try:
        port = com_var.get()
        baud = int(baud_var.get())
        serial_obj = serial.Serial(port, baud, timeout=0.1)
        serial_thread_running = True
        threading.Thread(target=serial_reader, daemon=True).start()
        serial_log(f"\nConnected to {port} @ {baud}\n")
    except Exception as e:
        messagebox.showerror("Serial Error", str(e))


def disconnect_serial():
    global serial_obj, serial_thread_running
    serial_thread_running = False
    try:
        if serial_obj:
            serial_obj.close()
    except Exception:
        pass
    serial_obj = None
    serial_log("\nSerial disconnected.\n")


def send_serial():
    if not serial_obj:
        messagebox.showwarning("Not Connected", "Connect serial port first.")
        return
    text = serial_send_var.get()
    if text:
        try:
            serial_obj.write((text + "\r\n").encode())
            serial_send_var.set("")
        except Exception as e:
            messagebox.showerror("Serial Send Error", str(e))


def apply_board_profile(event=None):
    profile = BOARD_PROFILES.get(board_var.get(), BOARD_PROFILES["Custom 8051"])
    chip_var.set(profile["chip"])
    upload_method_var.set(profile["method"])
    notes_label.config(text=profile["notes"])
    save_config()


def load_template(code):
    editor.delete("1.0", tk.END)
    editor.insert(tk.END, code)


def load_led_p10():
    load_template("""#include <8051.h>\n\nvoid delay()\n{\n    unsigned int i, j;\n    for(i = 0; i < 1000; i++)\n    {\n        for(j = 0; j < 100; j++);\n    }\n}\n\nvoid main()\n{\n    while(1)\n    {\n        P1_0 = 1;\n        delay();\n        P1_0 = 0;\n        delay();\n    }\n}\n""")


def load_led_p11():
    load_template("""#include <8051.h>\n\nvoid delay()\n{\n    unsigned int i, j;\n    for(i = 0; i < 1000; i++)\n    {\n        for(j = 0; j < 100; j++);\n    }\n}\n\nvoid main()\n{\n    while(1)\n    {\n        P1_1 = 1;\n        delay();\n        P1_1 = 0;\n        delay();\n    }\n}\n""")


def load_uart_echo():
    load_template("""#include <8051.h>\n\nvoid uart_init()\n{\n    TMOD = 0x20;\n    TH1 = 0xFD;     // 9600 baud for 11.0592 MHz\n    SCON = 0x50;\n    TR1 = 1;\n}\n\nvoid uart_tx(char c)\n{\n    SBUF = c;\n    while(TI == 0);\n    TI = 0;\n}\n\nchar uart_rx()\n{\n    while(RI == 0);\n    RI = 0;\n    return SBUF;\n}\n\nvoid main()\n{\n    char c;\n    uart_init();\n    while(1)\n    {\n        c = uart_rx();\n        uart_tx(c);\n    }\n}\n""")


def load_button_led():
    load_template("""#include <8051.h>\n\nvoid main()\n{\n    while(1)\n    {\n        if(P3_2 == 0)\n        {\n            P1_0 = 1;\n        }\n        else\n        {\n            P1_0 = 0;\n        }\n    }\n}\n""")

# UI
topbar = tk.Frame(root, bg="#2b2b2b")
topbar.pack(fill=tk.X)
btn_style = {"bg": "#3c3f41", "fg": "white", "font": ("Segoe UI", 10, "bold"), "bd": 0, "padx": 10, "pady": 5}
tk.Button(topbar, text="New", command=new_file, **btn_style).pack(side=tk.LEFT, padx=4, pady=5)
tk.Button(topbar, text="Open", command=open_file, **btn_style).pack(side=tk.LEFT, padx=4, pady=5)
tk.Button(topbar, text="Save", command=save_file, **btn_style).pack(side=tk.LEFT, padx=4, pady=5)
tk.Button(topbar, text="Compile HEX", command=compile_code, bg="#007acc", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=5).pack(side=tk.LEFT, padx=8, pady=5)
tk.Button(topbar, text="Upload", command=lambda: upload_hex(), bg="#188038", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=5).pack(side=tk.LEFT, padx=4, pady=5)
tk.Button(topbar, text="Compile + Upload", command=compile_and_upload, bg="#0f9d58", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=5).pack(side=tk.LEFT, padx=4, pady=5)
tk.Button(topbar, text="Open HEX Folder", command=open_hex_folder, **btn_style).pack(side=tk.LEFT, padx=4, pady=5)

main = tk.Frame(root, bg="#1e1e1e")
main.pack(fill=tk.BOTH, expand=True)
left = tk.Frame(main, bg="#252526", width=300)
left.pack(side=tk.LEFT, fill=tk.Y)
left.pack_propagate(False)
right = tk.Frame(main, bg="#1e1e1e")
right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

tk.Label(left, text="Board Manager", bg="#252526", fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(12, 6))
tk.Label(left, text="Board", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
board_dropdown = ttk.Combobox(left, textvariable=board_var, values=list(BOARD_PROFILES.keys()), state="readonly")
board_dropdown.pack(fill=tk.X, padx=10, pady=3)
board_dropdown.bind("<<ComboboxSelected>>", apply_board_profile)
tk.Label(left, text="Chip / Programmer ID", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
tk.Entry(left, textvariable=chip_var).pack(fill=tk.X, padx=10, pady=3)
tk.Label(left, text="Upload Method", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
upload_method_dropdown = ttk.Combobox(left, textvariable=upload_method_var, values=["Manual HEX Export Only", "AVRDUDE USBASP", "STC ISP / Custom Tool", "Nuvoton ISP / Custom Tool", "Custom Command"], state="readonly")
upload_method_dropdown.pack(fill=tk.X, padx=10, pady=3)
notes_label = tk.Label(left, text="", bg="#252526", fg="#9cdcfe", wraplength=275, justify="left")
notes_label.pack(anchor="w", padx=10, pady=(4, 10))

tk.Label(left, text="Examples", bg="#252526", fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 6))
tk.Button(left, text="Blink LED P1.0", command=load_led_p10, **btn_style).pack(fill=tk.X, padx=10, pady=3)
tk.Button(left, text="Blink LED P1.1", command=load_led_p11, **btn_style).pack(fill=tk.X, padx=10, pady=3)
tk.Button(left, text="Button P3.2 → LED P1.0", command=load_button_led, **btn_style).pack(fill=tk.X, padx=10, pady=3)
tk.Button(left, text="UART Echo 9600", command=load_uart_echo, **btn_style).pack(fill=tk.X, padx=10, pady=3)
tk.Button(left, text="Bare Template", command=lambda: load_template(get_bare_template()), **btn_style).pack(fill=tk.X, padx=10, pady=3)

tk.Label(left, text="Programmer Settings", bg="#252526", fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(18, 6))
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
tk.Label(left, text="Placeholders: {hex}, {com}, {baud}, {chip}, {board}", bg="#252526", fg="#cccccc", wraplength=275, justify="left").pack(anchor="w", padx=10, pady=3)
tk.Button(left, text="Select HEX", command=select_hex_file, **btn_style).pack(fill=tk.X, padx=10, pady=(12, 3))

notebook = ttk.Notebook(right)
notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
editor_frame = tk.Frame(notebook, bg="#1e1e1e")
serial_frame = tk.Frame(notebook, bg="#1e1e1e")
notebook.add(editor_frame, text="Code Editor")
notebook.add(serial_frame, text="Serial Monitor")
editor = tk.Text(editor_frame, bg="#1e1e1e", fg="#dcdcdc", insertbackground="white", font=("Consolas", 12), undo=True)
editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
output_box = tk.Text(editor_frame, height=11, bg="#111111", fg="#00ff00", insertbackground="white", font=("Consolas", 10))
output_box.pack(fill=tk.X, padx=5, pady=5)
serial_toolbar = tk.Frame(serial_frame, bg="#2b2b2b")
serial_toolbar.pack(fill=tk.X, padx=5, pady=5)
tk.Button(serial_toolbar, text="Connect", command=connect_serial, bg="#188038", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=5).pack(side=tk.LEFT, padx=4)
tk.Button(serial_toolbar, text="Disconnect", command=disconnect_serial, bg="#b3261e", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=5).pack(side=tk.LEFT, padx=4)
tk.Entry(serial_toolbar, textvariable=serial_send_var, width=50).pack(side=tk.LEFT, padx=8)
tk.Button(serial_toolbar, text="Send", command=send_serial, **btn_style).pack(side=tk.LEFT, padx=4)
serial_output = tk.Text(serial_frame, bg="#111111", fg="#00ff00", insertbackground="white", font=("Consolas", 10))
serial_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

editor.insert(tk.END, """// Robolark Embedded Studio V3\n// Supports regular 8051 boards + Nuvoton W78E052DDG profile.\n// Select board from left side, write code, compile HEX, then upload.\n""")
load_config()
apply_board_profile()
refresh_ports()
root.mainloop()
