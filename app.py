import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import subprocess
import os
import sys
import json
import tempfile

APP_NAME = "Robolark 8051 Simple IDE"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

SDCC_EXE = resource_path(os.path.join("sdcc", "bin", "sdcc.exe"))
PACKIHX_EXE = resource_path(os.path.join("sdcc", "bin", "packihx.exe"))
CONFIG_FILE = os.path.join(app_dir(), "robolark_simple_ide_config.json")

current_file = None
last_hex = None

root = tk.Tk()
root.title(APP_NAME)
root.geometry("1050x700")
root.configure(bg="#1e1e1e")

board_var = tk.StringVar(value="Nuvoton W78E052DDG")
port_var = tk.StringVar(value="")
baud_var = tk.StringVar(value="9600")
uploader_var = tk.StringVar(value="")
command_var = tk.StringVar(value='"{uploader}" "{hex}"')

def log(msg):
    console.insert(tk.END, str(msg) + "\n")
    console.see(tk.END)

def clear_log():
    console.delete("1.0", tk.END)

def save_config():
    data = {
        "board": board_var.get(),
        "port": port_var.get(),
        "baud": baud_var.get(),
        "uploader": uploader_var.get(),
        "command": command_var.get()
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
            board_var.set(data.get("board", "Nuvoton W78E052DDG"))
            port_var.set(data.get("port", ""))
            baud_var.set(data.get("baud", "9600"))
            uploader_var.set(data.get("uploader", ""))
            command_var.set(data.get("command", '"{uploader}" "{hex}"'))
        except Exception:
            pass

def refresh_ports():
    ports = []
    try:
        import serial.tools.list_ports
        ports = [p.device for p in serial.tools.list_ports.comports()]
    except Exception:
        ports = [f"COM{i}" for i in range(1, 31)]
    port_box["values"] = ports
    if ports and not port_var.get():
        port_var.set(ports[0])

def browse_uploader():
    path = filedialog.askopenfilename(filetypes=[("EXE Files", "*.exe"), ("All Files", "*.*")])
    if path:
        uploader_var.set(path)
        save_config()

def new_file():
    global current_file
    current_file = None
    editor.delete("1.0", tk.END)
    editor.insert(tk.END, sample_code())
    root.title(APP_NAME)

def open_file():
    global current_file
    path = filedialog.askopenfilename(filetypes=[("C Files", "*.c"), ("All Files", "*.*")])
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
            initialfile="main.c",
            filetypes=[("C Files", "*.c")]
        )
    if current_file:
        if not current_file.lower().endswith(".c"):
            current_file += ".c"
        with open(current_file, "w", encoding="utf-8") as f:
            f.write(editor.get("1.0", tk.END))
        root.title(f"{APP_NAME} - {os.path.basename(current_file)}")
    return current_file

def compile_to_hex(source_file):
    global last_hex

    if not os.path.exists(SDCC_EXE):
        raise Exception("Bundled SDCC not found: sdcc/bin/sdcc.exe")

    if not os.path.exists(PACKIHX_EXE):
        raise Exception("Bundled packihx not found: sdcc/bin/packihx.exe")

    if not source_file.lower().endswith(".c"):
        raise Exception("Please save/open only .c source files.")

    folder = os.path.dirname(source_file)
    filename = os.path.basename(source_file)
    base = os.path.splitext(source_file)[0]
    ihx = base + ".ihx"
    hexfile = base + ".hex"

    log("Step 1: Compiling C code...")
    result = subprocess.run(
        [SDCC_EXE, "-mmcs51", "--out-fmt-ihx", filename],
        cwd=folder,
        capture_output=True,
        text=True
    )

    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(result.stderr)

    if not os.path.exists(ihx):
        raise Exception("Compilation failed. IHX file not created.")

    log("Step 2: Creating HEX file...")
    with open(hexfile, "w", encoding="utf-8") as out:
        pack = subprocess.run(
            [PACKIHX_EXE, ihx],
            cwd=folder,
            stdout=out,
            stderr=subprocess.PIPE,
            text=True
        )

    if pack.stderr:
        log(pack.stderr)

    if not os.path.exists(hexfile):
        raise Exception("HEX generation failed.")

    last_hex = hexfile
    log(f"HEX ready: {hexfile}")
    return hexfile

def upload_hex(hexfile):
    save_config()

    uploader = uploader_var.get().strip()
    command_template = command_var.get().strip()

    if not uploader and "{uploader}" in command_template:
        log("Upload tool not selected.")
        log("HEX generated successfully, but upload skipped.")
        log("Select your programmer EXE once from settings.")
        messagebox.showinfo("HEX Ready", f"HEX generated:\n{hexfile}\n\nSelect uploader tool to enable direct upload.")
        try:
            os.startfile(os.path.dirname(hexfile))
        except Exception:
            pass
        return

    command = command_template
    command = command.replace("{uploader}", uploader)
    command = command.replace("{hex}", hexfile)
    command = command.replace("{port}", port_var.get())
    command = command.replace("{baud}", baud_var.get())
    command = command.replace("{board}", board_var.get())

    log("Step 3: Uploading to board...")
    log(command)

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(result.stderr)

    if result.returncode == 0:
        messagebox.showinfo("Done", "Code compiled and upload command completed.")
        log("Upload command completed.")
    else:
        messagebox.showerror("Upload Failed", "Upload command failed. Check console.")
        log(f"Upload failed with return code: {result.returncode}")

def upload_to_board():
    clear_log()
    try:
        source = save_file()
        if not source:
            return
        hexfile = compile_to_hex(source)
        upload_hex(hexfile)
    except Exception as e:
        log("ERROR:")
        log(str(e))
        messagebox.showerror("Failed", str(e))

def open_output_folder():
    if last_hex and os.path.exists(last_hex):
        os.startfile(os.path.dirname(last_hex))
    elif current_file:
        os.startfile(os.path.dirname(current_file))
    else:
        messagebox.showinfo("No output", "Upload/compile first.")

def sample_code():
    return """#include <8051.h>

void delay()
{
    unsigned int i;
    unsigned int j;

    for(i = 0; i < 1000; i++)
    {
        for(j = 0; j < 100; j++)
        {
        }
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

# UI
top = tk.Frame(root, bg="#2b2b2b")
top.pack(fill=tk.X)

btn = {
    "bg": "#3c3f41",
    "fg": "white",
    "font": ("Segoe UI", 10, "bold"),
    "bd": 0,
    "padx": 10,
    "pady": 6
}

tk.Button(top, text="New", command=new_file, **btn).pack(side=tk.LEFT, padx=5, pady=6)
tk.Button(top, text="Open", command=open_file, **btn).pack(side=tk.LEFT, padx=5, pady=6)
tk.Button(top, text="Save", command=save_file, **btn).pack(side=tk.LEFT, padx=5, pady=6)

tk.Button(
    top,
    text="UPLOAD TO BOARD",
    command=upload_to_board,
    bg="#0f9d58",
    fg="white",
    font=("Segoe UI", 12, "bold"),
    bd=0,
    padx=18,
    pady=7
).pack(side=tk.LEFT, padx=12, pady=6)

tk.Button(top, text="Open Output Folder", command=open_output_folder, **btn).pack(side=tk.LEFT, padx=5, pady=6)

main = tk.Frame(root, bg="#1e1e1e")
main.pack(fill=tk.BOTH, expand=True)

left = tk.Frame(main, bg="#252526", width=310)
left.pack(side=tk.LEFT, fill=tk.Y)
left.pack_propagate(False)

right = tk.Frame(main, bg="#1e1e1e")
right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

tk.Label(left, text="Simple Upload Settings", bg="#252526", fg="white", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(15,8))

tk.Label(left, text="Board", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
ttk.Combobox(
    left,
    textvariable=board_var,
    values=["Nuvoton W78E052DDG", "AT89S52", "AT89S51", "STC89C52", "Custom 8051"],
    state="readonly"
).pack(fill=tk.X, padx=10, pady=4)

tk.Label(left, text="COM Port", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
port_box = ttk.Combobox(left, textvariable=port_var)
port_box.pack(fill=tk.X, padx=10, pady=4)

tk.Button(left, text="Refresh COM Ports", command=refresh_ports, **btn).pack(fill=tk.X, padx=10, pady=4)

tk.Label(left, text="Baud", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10)
tk.Entry(left, textvariable=baud_var).pack(fill=tk.X, padx=10, pady=4)

tk.Label(left, text="Uploader Tool EXE", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10, pady=(12,0))
tk.Entry(left, textvariable=uploader_var).pack(fill=tk.X, padx=10, pady=4)
tk.Button(left, text="Select Uploader Tool", command=browse_uploader, **btn).pack(fill=tk.X, padx=10, pady=4)

tk.Label(left, text="Upload Command", bg="#252526", fg="#dcdcdc").pack(anchor="w", padx=10, pady=(12,0))
tk.Entry(left, textvariable=command_var).pack(fill=tk.X, padx=10, pady=4)

tk.Label(
    left,
    text="One button flow:\nSave C → Compile HEX → Upload\n\nPlaceholders:\n{uploader}\n{hex}\n{port}\n{baud}\n{board}",
    bg="#252526",
    fg="#9cdcfe",
    justify="left",
    wraplength=285
).pack(anchor="w", padx=10, pady=12)

editor = tk.Text(
    right,
    bg="#1e1e1e",
    fg="#dcdcdc",
    insertbackground="white",
    font=("Consolas", 12),
    undo=True
)
editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

console = tk.Text(
    right,
    height=12,
    bg="#111111",
    fg="#00ff00",
    insertbackground="white",
    font=("Consolas", 10)
)
console.pack(fill=tk.X, padx=5, pady=5)

load_config()
refresh_ports()
editor.insert(tk.END, sample_code())

root.mainloop()
