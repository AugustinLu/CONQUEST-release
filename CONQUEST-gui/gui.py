import tkinter as tk
from tkinter import filedialog, ttk
import json
import os
import subprocess
import threading
import queue
import time
import psutil
from parsers import combine_data

class ConquestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CONQUEST GUI")
        self.root.geometry("1000x800")

        self.config = self.load_config()
        self.process = None
        self.monitoring_active = False

        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.create_file_selection_area()
        self.create_static_dashboard()
        self.create_control_panel()
        self.create_resource_dashboard()
        self.create_progress_dashboard()
        self.create_results_area()

        self.start_resource_monitor()

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {"executable": "Conquest", "mpi_command": "mpirun", "default_mpi_processes": 4}

    def create_file_selection_area(self):
        frame = ttk.LabelFrame(self.main_frame, text="Input Files", padding="10")
        frame.pack(fill=tk.X, pady=5)

        self.input_path_var = tk.StringVar()
        self.coords_path_var = tk.StringVar()
        self.ion_dir_var = tk.StringVar()

        self._add_file_row(frame, "Conquest_input:", self.input_path_var, 0)
        self._add_file_row(frame, "Structure file (coords.dat):", self.coords_path_var, 1)
        self._add_dir_row(frame, "Ion files directory:", self.ion_dir_var, 2)

        ttk.Button(frame, text="Load Data", command=self.load_data).grid(row=3, column=0, columnspan=3, pady=10)

    def _add_file_row(self, parent, label_text, string_var, row):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(parent, textvariable=string_var, width=50).grid(row=row, column=1, padx=5, pady=2)
        ttk.Button(parent, text="Browse", command=lambda: string_var.set(filedialog.askopenfilename())).grid(row=row, column=2, padx=5, pady=2)

    def _add_dir_row(self, parent, label_text, string_var, row):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(parent, textvariable=string_var, width=50).grid(row=row, column=1, padx=5, pady=2)
        ttk.Button(parent, text="Browse", command=lambda: string_var.set(filedialog.askdirectory())).grid(row=row, column=2, padx=5, pady=2)

    def create_static_dashboard(self):
        frame = ttk.LabelFrame(self.main_frame, text="System Information", padding="10")
        frame.pack(fill=tk.X, pady=5)

        self.sys_info_text = tk.Text(frame, height=5, state=tk.DISABLED, wrap=tk.WORD)
        self.sys_info_text.pack(fill=tk.X)

    def create_control_panel(self):
        frame = ttk.Frame(self.main_frame, padding="10")
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="MPI Processes:").pack(side=tk.LEFT, padx=5)
        self.mpi_var = tk.IntVar(value=self.config.get("default_mpi_processes", 4))
        ttk.Entry(frame, textvariable=self.mpi_var, width=5).pack(side=tk.LEFT, padx=5)

        self.run_btn = ttk.Button(frame, text="Run Conquest", command=self.run_simulation)
        self.run_btn.pack(side=tk.LEFT, padx=20)

        self.stop_btn = ttk.Button(frame, text="Stop", command=self.stop_simulation, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

    def create_resource_dashboard(self):
        frame = ttk.LabelFrame(self.main_frame, text="Resource Monitor", padding="10")
        frame.pack(fill=tk.X, pady=5)

        self.cpu_var = tk.StringVar(value="CPU: 0%")
        self.mem_var = tk.StringVar(value="Memory: 0%")
        self.disk_var = tk.StringVar(value="Disk: 0%")

        ttk.Label(frame, textvariable=self.cpu_var, width=20).pack(side=tk.LEFT, padx=10)
        ttk.Label(frame, textvariable=self.mem_var, width=20).pack(side=tk.LEFT, padx=10)
        ttk.Label(frame, textvariable=self.disk_var, width=20).pack(side=tk.LEFT, padx=10)

    def create_progress_dashboard(self):
        frame = ttk.LabelFrame(self.main_frame, text="Simulation Progress", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.progress_text = tk.Text(frame, height=10, state=tk.DISABLED, wrap=tk.WORD)
        self.progress_text.pack(fill=tk.BOTH, expand=True)

    def create_results_area(self):
        frame = ttk.LabelFrame(self.main_frame, text="Results", padding="10")
        frame.pack(fill=tk.X, pady=5)

        self.results_var = tk.StringVar(value="Simulation not started.")
        ttk.Label(frame, textvariable=self.results_var).pack(anchor=tk.W)

    def load_data(self):
        input_path = self.input_path_var.get()
        coords_path = self.coords_path_var.get()
        ion_dir = self.ion_dir_var.get()

        ion_files = []
        if os.path.isdir(ion_dir):
            for f in os.listdir(ion_dir):
                if f.endswith('.ion') or 'Conquest_ion_input' in f:
                    ion_files.append(os.path.join(ion_dir, f))

        data = combine_data(input_path, coords_path, ion_files)

        info_str = f"Cutoff: {data['input'].get('Grid.GridCutoff', 'N/A')}\n"
        info_str += f"Total Atoms: {data['coords'].get('total_atoms', 'N/A')}\n"

        species = data.get('species_summary', {})
        if species:
            species_str = ", ".join([f"{k}: {v}" for k,v in species.items()])
            info_str += f"Species: {species_str}\n"

        if data['ion_files']:
            sizes = set([ion.get('basis_size', 'Unknown') for ion in data['ion_files']])
            info_str += f"Basis Sizes: {', '.join(sizes)}\n"

        self.sys_info_text.config(state=tk.NORMAL)
        self.sys_info_text.delete(1.0, tk.END)
        self.sys_info_text.insert(tk.END, info_str)
        self.sys_info_text.config(state=tk.DISABLED)

    def start_resource_monitor(self):
        def monitor():
            while True:
                try:
                    cpu = psutil.cpu_percent(interval=1)
                    mem = psutil.virtual_memory()
                    disk = psutil.disk_usage('/')

                    self.root.after(0, lambda: self.cpu_var.set(f"CPU: {cpu}%"))
                    self.root.after(0, lambda: self.mem_var.set(f"Memory: {mem.percent}%"))
                    self.root.after(0, lambda: self.disk_var.set(f"Disk: {disk.percent}%"))
                except Exception as e:
                    pass
                time.sleep(1)

        t = threading.Thread(target=monitor, daemon=True)
        t.start()

    def log_progress(self, message):
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state=tk.DISABLED)

    def parse_output_line(self, line):
        self.log_progress(line.strip())

        # Super simple scraping logic for energy or steps
        if "Total energy" in line:
            self.root.after(0, lambda: self.results_var.set(f"Energy: {line.strip()}"))
        if "SCF" in line or "iteration" in line.lower():
            pass # can extract detailed info here in future

    def run_simulation(self):
        if self.process is not None:
            return

        input_path = self.input_path_var.get()
        if not input_path or not os.path.exists(input_path):
            self.results_var.set("Error: Conquest_input not found!")
            return

        work_dir = os.path.dirname(input_path)
        mpi_cmd = self.config.get('mpi_command', 'mpirun')
        executable = self.config.get('executable', 'Conquest')
        processes = str(self.mpi_var.get())

        cmd = [mpi_cmd, '-np', processes, executable]

        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.results_var.set("Running...")
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.config(state=tk.DISABLED)

        def run_thread():
            try:
                self.process = subprocess.Popen(
                    cmd,
                    cwd=work_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                for line in self.process.stdout:
                    self.root.after(0, self.parse_output_line, line)

                self.process.wait()

                if self.process.returncode == 0:
                    self.root.after(0, lambda: self.results_var.set(self.results_var.get() + " | Finished Successfully."))
                else:
                    self.root.after(0, lambda: self.results_var.set(self.results_var.get() + " | Terminated or Crashed."))

            except Exception as e:
                self.root.after(0, lambda: self.results_var.set(f"Execution Error: {str(e)}"))

            finally:
                self.process = None
                self.root.after(0, lambda: self.run_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

        t = threading.Thread(target=run_thread, daemon=True)
        t.start()

    def stop_simulation(self):
        if self.process:
            self.process.terminate()
            self.results_var.set("Simulation Stopped by User.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConquestGUI(root)
    root.mainloop()
