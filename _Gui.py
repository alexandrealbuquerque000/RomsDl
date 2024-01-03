import os
import tkinter.ttk as ttk
import tkinter as tk
from operator import setitem
from queue import Queue, Empty
from tkinter.filedialog import askdirectory
from _RomsDl import Roms_Dl


def validate(condition, entry, result):
    if not condition:
        entry.config(highlightbackground="red")
        return result
    else:
        entry.config(highlightbackground="black")


class MainFrame(tk.Frame):
    def __init__(self, _master, input_dir=None, systems_list=[]):
        self.update_time=100
        tk.Frame.__init__(self, master=_master, width=400, height=150)
        self.master.protocol("WM_DELETE_WINDOW", self.close)
        self.generic_queue = Queue()
        self.progress_queue = Queue()

        if input_dir and os.path.isdir(input_dir):
            self.input_dir = os.path.abspath(input_dir)
            self.input_dir_var = tk.StringVar(value=self.input_dir)
        else:
            self.input_dir = None
            self.input_dir_var = tk.StringVar(value="No directory given")
            
        self.working = False
        self.thread = None
        self.showerror = tk.messagebox.showerror

        self.master.title("Get_ROMs")

        self.systems_list=systems_list
        self.systems_list_var=None

        panel = tk.Frame()
        panel.place(in_=self, anchor="c", relx=.5, rely=.5)

        # Directory
        self.input_dir_entry = tk.Entry(panel, state='readonly', textvariable=self.input_dir_var, width=41)
        self.input_dir_entry.grid(row=0, column=0, padx=5)

        self.button_dir = tk.Button(panel, text="Change directory", command=self.get_dir, width=15)
        self.button_dir.grid(row=0, column=1, padx=5, pady=3)

        # Options
        systems_list_names=[system.get('Name') for system in self.systems_list]
        system_entry_width=len(sorted(systems_list_names, key=len)[-1])
        qnt_systems_list=len(self.systems_list)
        system_entry_height=4
        system_entry_height=(system_entry_height if qnt_systems_list>system_entry_height else qnt_systems_list)
        self.systems_entry = tk.Listbox(panel, selectmode = tk.MULTIPLE, justify='center', width=system_entry_width, height=system_entry_height, listvariable=self.systems_list_var) 
        self.systems_entry.grid(row=1, column=0, columnspan=2, padx=5) 
        self.systems_entry.insert(tk.END,*systems_list_names)
    
        # Progress
        progress = tk.Frame(panel)
        progress.grid(row=2, column=0, columnspan=2, pady=3)
        self.button_start = tk.Button(progress, text="Start", command=self.start, width=10)
        self.button_start.grid(row=0, column=0, padx=5, pady=3)

        self.progress = ttk.Progressbar(progress, length=200, mode='determinate', name='progress of making the ePub')
        self.progress.grid(row=0, column=1, padx=5, pady=3)

        self.button_stop = tk.Button(progress, text="Stop", command=self.stop, width=10)
        self.button_stop.grid(row=0, column=2, padx=5, pady=3)

        self.set_state()

        self.pack(expand=True)

        self.after(self.update_time, self.process_queue)

    def get_dir(self):
        self.input_dir = os.path.abspath(askdirectory(master=self))
        self.input_dir_var.set(self.input_dir or "No directory given")
        self.set_state()
       
        self.set_state()
    def get_invalid(self):
        result =    [
                        validate(self.input_dir and os.path.isdir(self.input_dir), self.input_dir_entry, "input directory"),
                        validate(self.systems_list_var, self.systems_entry, "select systems"),
                    ]
        
        return list(filter(None, result))

    def set_state(self):
        state = tk.DISABLED if self.working else tk.NORMAL
        self.button_dir.config(state=state)
        self.button_stop.config(state=tk.NORMAL if self.working else tk.DISABLED)
        self.button_start.config(state=tk.NORMAL if not self.working else tk.DISABLED)
        return True

    def start(self):
        self.systems_list_var=self.systems_entry.curselection()
        invalid = self.get_invalid()
        if not invalid:
            self.working = True
            self.thread = Roms_Dl(
                master=self, main_path=self.input_dir, choosed_systems=self.systems_list_var, progress=self.progress,
                                    )
            self.thread.start()
        else:
            tk.messagebox.showerror(
                "Invalid input",
                f"Please check the following field{'s' if 1 < len(invalid) else ''}: the {', the '.join(invalid)}"
            )
        self.set_state()

    def stop(self, value=0):
        if self.thread:
            self.thread.stop()
            self.thread.join()
            self.thread = None
            self.working = False
            self.clear_progress_queue()
            self.progress["maximum"] = 1
            self.progress["value"] = value
        self.set_state()

    def clear_progress_queue(self):
        last = None
        try:
            while True:
                last = self.progress_queue.get_nowait()
        except Empty:
            return last

    def progress_set_maximum(self, maximum):
        self.generic_queue.put(lambda: setitem(self.progress, "maximum", maximum))
        self.clear_progress_queue()

    def progress_set_value(self, value):
        self.progress_queue.put(lambda: setitem(self.progress, "value", value))

    def close(self):
        self.stop()
        self.master.destroy()

    def process_queue(self):
        try:
            while True:
                self.generic_queue.get_nowait()()
        except Empty:
            pass
        last = self.clear_progress_queue()
        if last is not None:
            last()
        self.after(self.update_time, self.process_queue)


def start_gui(input_dir=None, systems_list=[]):
    root = tk.Tk()
    MainFrame(root, input_dir=input_dir, systems_list=systems_list).mainloop()


if __name__ == "__main__":
    start_gui(systems_list=Roms_Dl().main())