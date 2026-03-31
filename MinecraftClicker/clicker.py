import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import os
from queue import Queue
import sys

# Проверяем библиотеки
try:
    from pynput.mouse import Button, Controller
    from pynput import mouse
except:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput"])
    from pynput.mouse import Button, Controller
    from pynput import mouse

try:
    import keyboard
except:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "keyboard"])
    import keyboard

class SafeClicker:
    def __init__(self):
        self.active = False
        self.is_clicking = False
        self.clicks_per_press = 10
        self.click_delay = 0.05
        self.click_btn = Button.right
        self.toggle_hotkey = 'f6'
        self.toggle_mouse_button = None
        
        self.click_queue = Queue()
        self.worker_thread = None
        self.stop_worker = False
        
        self.window = tk.Tk()
        self.window.title("Minecraft Clicker - Безопасная версия")
        self.window.geometry("550x650")
        
        self.center_window()
        self.setup_ui()
        self.start_listeners()
        self.start_worker()
        self.load_settings()
        
    def center_window(self):
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        canvas = tk.Canvas(self.window)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_frame = ttk.Frame(scrollable_frame, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="MINECRAFT CLICKER", font=("Arial", 20, "bold"), fg="#2c3e50").pack(pady=10)
        tk.Label(main_frame, text="Безопасная версия - клики не накладываются", font=("Arial", 10), fg="green").pack()
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        info_frame = ttk.LabelFrame(main_frame, text="📖 Как это работает", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(info_frame, text="1️⃣ Нажмите F6 для включения кликера", font=("Arial", 9)).pack(anchor=tk.W)
        tk.Label(info_frame, text="2️⃣ Нажмите ПРАВУЮ кнопку мыши → серия кликов", font=("Arial", 9)).pack(anchor=tk.W)
        tk.Label(info_frame, text="3️⃣ Пока идут клики, новые нажатия игнорируются", font=("Arial", 9), fg="blue").pack(anchor=tk.W)
        tk.Label(info_frame, text="4️⃣ Клики не накладываются и не лагают!", font=("Arial", 9), fg="green").pack(anchor=tk.W)
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        clicks_frame = ttk.LabelFrame(main_frame, text="⚙️ Количество кликов за нажатие", padding="10")
        clicks_frame.pack(fill=tk.X, pady=5)
        
        self.clicks_var = tk.StringVar(value="10")
        clicks_control = ttk.Frame(clicks_frame)
        clicks_control.pack()
        
        ttk.Spinbox(clicks_control, from_=1, to=30, textvariable=self.clicks_var, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(clicks_control, text="Применить", command=self.update_clicks, bg="#3498db", fg="white").pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        delay_frame = ttk.LabelFrame(main_frame, text="⏱️ Задержка между кликами (сек)", padding="10")
        delay_frame.pack(fill=tk.X, pady=5)
        
        self.delay_var = tk.StringVar(value="0.05")
        delay_control = ttk.Frame(delay_frame)
        delay_control.pack()
        
        ttk.Spinbox(delay_control, from_=0.01, to=0.2, increment=0.01, textvariable=self.delay_var, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(delay_control, text="Применить", command=self.update_delay, bg="#3498db", fg="white").pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        hotkey_frame = ttk.LabelFrame(main_frame, text="⌨️ Горячие клавиши (ВКЛ/ВЫКЛ)", padding="10")
        hotkey_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(hotkey_frame, text="Клавиатура:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        self.hotkey_var = tk.StringVar(value="F6")
        tk.Entry(hotkey_frame, textvariable=self.hotkey_var, width=15, justify="center").pack(pady=2)
        tk.Button(hotkey_frame, text="Назначить клавишу", command=self.assign_keyboard_hotkey, bg="#2ecc71", fg="white").pack(pady=2)
        
        tk.Label(hotkey_frame, text="Мышь:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(10,0))
        self.mouse_hotkey_var = tk.StringVar(value="Не назначена")
        tk.Label(hotkey_frame, textvariable=self.mouse_hotkey_var, fg="blue", font=("Arial", 10)).pack()
        tk.Button(hotkey_frame, text="Назначить кнопку мыши", command=self.assign_mouse_hotkey, bg="#e67e22", fg="white").pack(pady=2)
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        status_frame = ttk.LabelFrame(main_frame, text="📊 Статус", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = tk.Label(status_frame, text="🔴 КЛИКЕР ВЫКЛЮЧЕН", font=("Arial", 13, "bold"), fg="red")
        self.status_label.pack()
        
        self.click_status = tk.Label(status_frame, text="● Ожидание нажатия", fg="gray")
        self.click_status.pack(pady=5)
        
        self.counter_label = tk.Label(status_frame, text="Всего кликов: 0", fg="blue")
        self.counter_label.pack()
        
        self.total_clicks = 0
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        self.toggle_btn = tk.Button(btn_frame, text="🔘 ВКЛЮЧИТЬ КЛИКЕР", command=self.toggle, 
                                    bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), width=20)
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="💾 Сохранить", command=self.save_settings, bg="#3498db", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📂 Загрузить", command=self.load_settings, bg="#3498db", fg="white").pack(side=tk.LEFT, padx=5)
        
        emergency_frame = ttk.LabelFrame(main_frame, text="🚨 Экстренная остановка", padding="10")
        emergency_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(emergency_frame, text="🛑 НЕМЕДЛЕННО ОСТАНОВИТЬ ВСЕ КЛИКИ", 
                 command=self.emergency_stop, bg="#e74c3c", fg="white", 
                 font=("Arial", 10, "bold"), height=2).pack(fill=tk.X)
        
        example_frame = ttk.LabelFrame(main_frame, text="🎮 Пример для Майнкрафт", padding="10")
        example_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(example_frame, text="1. Включите кликер (F6)", font=("Arial", 9)).pack(anchor=tk.W)
        tk.Label(example_frame, text="2. Нажмите правую кнопку мыши один раз", font=("Arial", 9)).pack(anchor=tk.W)
        tk.Label(example_frame, text="3. Программа сделает 10 кликов и остановится", font=("Arial", 9)).pack(anchor=tk.W)
        tk.Label(example_frame, text="4. Новое нажатие начнет новую серию", font=("Arial", 9)).pack(anchor=tk.W)
        
        tk.Label(main_frame, text="", height=2).pack()
    
    def update_clicks(self):
        try:
            self.clicks_per_press = int(self.clicks_var.get())
            if self.clicks_per_press < 1:
                self.clicks_per_press = 1
            if self.clicks_per_press > 30:
                self.clicks_per_press = 30
        except:
            self.clicks_per_press = 10
    
    def update_delay(self):
        try:
            self.click_delay = float(self.delay_var.get())
            if self.click_delay < 0.01:
                self.click_delay = 0.01
            if self.click_delay > 0.2:
                self.click_delay = 0.2
        except:
            self.click_delay = 0.05
    
    def assign_keyboard_hotkey(self):
        self.status_label.config(text="⏳ Нажмите клавишу...", fg="orange")
        
        def on_press(key):
            try:
                from pynput import keyboard
                if hasattr(key, 'char') and key.char:
                    name = key.char.upper()
                else:
                    name = str(key).replace("Key.", "").upper()
                
                self.hotkey_var.set(name)
                self.toggle_hotkey = name.lower()
                self.status_label.config(text=f"✅ Клавиша: {name}", fg="green")
                return False
            except:
                return False
        
        from pynput import keyboard
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        self.window.after(5000, lambda: listener.stop() if listener.running else None)
    
    def assign_mouse_hotkey(self):
        self.status_label.config(text="⏳ Нажмите кнопку на мыши...", fg="orange")
        
        def on_click(x, y, button, pressed):
            if pressed:
                names = {
                    Button.left: "Левая кнопка",
                    Button.right: "Правая кнопка",
                    Button.middle: "Средняя кнопка",
                    Button.x1: "Боковая кнопка 1",
                    Button.x2: "Боковая кнопка 2"
                }
                button_name = names.get(button, "Неизвестно")
                self.mouse_hotkey_var.set(button_name)
                self.toggle_mouse_button = button
                self.status_label.config(text=f"✅ Кнопка: {button_name}", fg="green")
                return False
        
        listener = mouse.Listener(on_click=on_click)
        listener.start()
        self.window.after(5000, lambda: listener.stop() if listener.running else None)
    
    def toggle(self):
        self.active = not self.active
        
        if self.active:
            self.status_label.config(text="🟢 КЛИКЕР ВКЛЮЧЕН", fg="green")
            self.toggle_btn.config(text="🔴 ВЫКЛЮЧИТЬ КЛИКЕР", bg="#e74c3c")
        else:
            self.status_label.config(text="🔴 КЛИКЕР ВЫКЛЮЧЕН", fg="red")
            self.toggle_btn.config(text="🔘 ВКЛЮЧИТЬ КЛИКЕР", bg="#2ecc71")
            self.click_status.config(text="● Ожидание нажатия", fg="gray")
    
    def add_click_task(self):
        if not self.active:
            return
        if self.is_clicking:
            self.click_status.config(text="⏳ Клики уже выполняются, подождите...", fg="orange")
            self.window.after(1000, lambda: self.click_status.config(text="● Ожидание нажатия", fg="gray"))
            return
        self.click_queue.put(True)
    
    def start_worker(self):
        def worker():
            mouse_controller = Controller()
            while not self.stop_worker:
                try:
                    self.click_queue.get(timeout=0.1)
                    self.is_clicking = True
                    self.window.after(0, lambda: self.click_status.config(text="🔨 Выполняются клики...", fg="green"))
                    
                    for i in range(self.clicks_per_press):
                        if not self.active or self.stop_worker:
                            break
                        try:
                            mouse_controller.click(self.click_btn)
                            self.total_clicks += 1
                            self.window.after(0, lambda: self.counter_label.config(text=f"Всего кликов: {self.total_clicks}"))
                            time.sleep(self.click_delay)
                        except:
                            break
                    
                    self.is_clicking = False
                    self.window.after(0, lambda: self.click_status.config(text="● Готов к нажатию", fg="gray"))
                except:
                    pass
        
        self.stop_worker = False
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
    
    def emergency_stop(self):
        self.active = False
        self.is_clicking = False
        while not self.click_queue.empty():
            try:
                self.click_queue.get_nowait()
            except:
                pass
        
        self.status_label.config(text="🔴 КЛИКЕР ВЫКЛЮЧЕН", fg="red")
        self.toggle_btn.config(text="🔘 ВКЛЮЧИТЬ КЛИКЕР", bg="#2ecc71")
        self.click_status.config(text="● Остановлено экстренно", fg="red")
        self.window.after(1500, lambda: self.click_status.config(text="● Ожидание нажатия", fg="gray"))
        messagebox.showinfo("Экстренная остановка", "Все клики остановлены!")
    
    def start_listeners(self):
        def on_click(x, y, button, pressed):
            if pressed and button == Button.right and self.active:
                self.add_click_task()
        
        mouse.Listener(on_click=on_click, daemon=True).start()
        
        def check_keyboard():
            try:
                if keyboard.is_pressed(self.toggle_hotkey):
                    self.toggle()
                    time.sleep(0.3)
            except:
                pass
            self.window.after(100, check_keyboard)
        
        self.window.after(100, check_keyboard)
        
        def check_mouse():
            def on_click(x, y, button, pressed):
                if self.toggle_mouse_button and button == self.toggle_mouse_button and pressed:
                    self.toggle()
                    time.sleep(0.3)
            mouse.Listener(on_click=on_click, daemon=True).start()
        
        self.window.after(100, check_mouse)
    
    def save_settings(self):
        settings = {
            "clicks_per_press": self.clicks_per_press,
            "click_delay": self.click_delay,
            "toggle_hotkey": self.toggle_hotkey,
            "toggle_mouse_button": self.mouse_hotkey_var.get()
        }
        try:
            with open("clicker_settings.json", "w") as f:
                json.dump(settings, f)
            messagebox.showinfo("Успех", "Настройки сохранены!")
        except:
            messagebox.showerror("Ошибка", "Не удалось сохранить")
    
    def load_settings(self):
        if os.path.exists("clicker_settings.json"):
            try:
                with open("clicker_settings.json", "r") as f:
                    settings = json.load(f)
                
                self.clicks_var.set(str(settings.get("clicks_per_press", 10)))
                self.delay_var.set(str(settings.get("click_delay", 0.05)))
                self.hotkey_var.set(settings.get("toggle_hotkey", "f6").upper())
                self.mouse_hotkey_var.set(settings.get("toggle_mouse_button", "Не назначена"))
                
                self.update_clicks()
                self.update_delay()
                self.toggle_hotkey = settings.get("toggle_hotkey", "f6").lower()
                
                if self.mouse_hotkey_var.get() != "Не назначена":
                    btns = {"Левая кнопка": Button.left, "Правая кнопка": Button.right, 
                            "Средняя кнопка": Button.middle, "Боковая кнопка 1": Button.x1, 
                            "Боковая кнопка 2": Button.x2}
                    self.toggle_mouse_button = btns.get(self.mouse_hotkey_var.get())
                
                messagebox.showinfo("Успех", "Настройки загружены!")
            except:
                pass
    
    def run(self):
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()
    
    def on_closing(self):
        self.stop_worker = True
        self.window.destroy()

if __name__ == "__main__":
    app = SafeClicker()
    app.run()