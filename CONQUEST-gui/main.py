import tkinter as tk
from gui import ConquestGUI

def main():
    root = tk.Tk()
    app = ConquestGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
