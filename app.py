import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

SDCC_EXE = resource_path(os.path.join("sdcc", "bin", "sdcc.exe"))
PACKIHX_EXE = resource_path(os.path.join("sdcc", "bin", "packihx.exe"))

current_file = None

root = tk.Tk()
root.title("Robolark 8051 Studio")
root.geometry("1000x650")
root.configure(bg="#1e1e1e")

def new_file():
    global current_file
    current_file = None
    editor.delete("1.0", tk.END)
    output_box.delete("1.0", tk.END)

def open_file():
    global current_file
    path = filedialog.askopenfilename(
        filetypes=[("C Files", "*.c"), ("All Files", "*.*")]
    )

    if path:
        current_file = path

        with open(path, "r", encoding="utf-8") as f:
            editor.delete("1.0", tk.END)
            editor.insert(tk.END, f.read())

def save_file():
    global current_file

    if current_file is None:
        current_file = filedialog.asksaveasfilename(
            defaultextension=".c",
            filetypes=[("C Files", "*.c")]
        )

    if current_file:
        with open(current_file, "w", encoding="utf-8") as f:
            f.write(editor.get("1.0", tk.END))

    return current_file

def compile_code():
    global current_file

    save_file()

    if not current_file:
        return

    if not os.path.exists(SDCC_EXE):
        messagebox.showerror(
            "Missing SDCC",
            "sdcc.exe not found!"
        )
        return

    project_folder = os.path.dirname(current_file)
    file_name = os.path.basename(current_file)

    output_box.delete("1.0", tk.END)
    output_box.insert(tk.END, "Compiling 8051 code...\n\n")

    result = subprocess.run(
        [SDCC_EXE, "-mmcs51", file_name],
        cwd=project_folder,
        capture_output=True,
        text=True
    )

    output_box.insert(tk.END, result.stdout)
    output_box.insert(tk.END, result.stderr)

    ihx_file = current_file.replace(".c", ".ihx")
    hex_file = current_file.replace(".c", ".hex")

    if os.path.exists(ihx_file):

        with open(hex_file, "w", encoding="utf-8") as out:
            subprocess.run(
                [PACKIHX_EXE, ihx_file],
                cwd=project_folder,
                stdout=out,
                text=True
            )

        output_box.insert(
            tk.END,
            f"\nHEX Generated Successfully:\n{hex_file}\n"
        )

        messagebox.showinfo(
            "Success",
            f"HEX Generated:\n{hex_file}"
        )

    else:
        output_box.insert(
            tk.END,
            "\nCompilation failed.\n"
        )

        messagebox.showerror(
            "Failed",
            "HEX not generated."
        )

def load_led_blink():

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

toolbar = tk.Frame(root, bg="#2b2b2b")
toolbar.pack(fill=tk.X)

btn_style = {
    "bg": "#3c3f41",
    "fg": "white",
    "font": ("Segoe UI", 10, "bold"),
    "bd": 0,
    "padx": 10,
    "pady": 5
}

tk.Button(
    toolbar,
    text="New",
    command=new_file,
    **btn_style
).pack(side=tk.LEFT, padx=5, pady=5)

tk.Button(
    toolbar,
    text="Open",
    command=open_file,
    **btn_style
).pack(side=tk.LEFT, padx=5, pady=5)

tk.Button(
    toolbar,
    text="Save",
    command=save_file,
    **btn_style
).pack(side=tk.LEFT, padx=5, pady=5)

tk.Button(
    toolbar,
    text="Compile & Generate HEX",
    command=compile_code,
    bg="#007acc",
    fg="white",
    font=("Segoe UI", 10, "bold"),
    bd=0,
    padx=10,
    pady=5
).pack(side=tk.LEFT, padx=10, pady=5)

tk.Button(
    toolbar,
    text="Load LED Blink",
    command=load_led_blink,
    **btn_style
).pack(side=tk.LEFT, padx=5, pady=5)

editor = tk.Text(
    root,
    bg="#1e1e1e",
    fg="#dcdcdc",
    insertbackground="white",
    font=("Consolas", 12),
    undo=True
)

editor.pack(
    fill=tk.BOTH,
    expand=True,
    padx=5,
    pady=5
)

output_box = tk.Text(
    root,
    height=10,
    bg="#111111",
    fg="#00ff00",
    insertbackground="white",
    font=("Consolas", 10)
)

output_box.pack(
    fill=tk.X,
    padx=5,
    pady=5
)

editor.insert(
    tk.END,
    """// Robolark 8051 Studio
// Write your 8051 C code here.
// Click 'Load LED Blink' for sample code.
"""
)

root.mainloop()
