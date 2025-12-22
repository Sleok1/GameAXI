import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import threading
import json
import time
import requests
import math
import random
import re
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
AI_MODEL = "llama3"   
BASE_DIR = r"C:\GameAXI"
MEMORY_DIR = os.path.join(BASE_DIR, "CORE_MEMORY")
GOAL_FILE = os.path.join(BASE_DIR, "current_goal.txt")
DIARY_FILE = os.path.join(BASE_DIR, "evolution_diary.txt")

# Цвета
C_BG = "#020202"
C_PANEL = "#0a0a0f"
C_ACCENT = "#00ff41" # Matrix Green
C_SEC = "#003b00"
C_TEXT = "#aaffaa"
C_ERR = "#ff3333"

class NexusGenesis:
    def __init__(self, root):
        self.root = root
        self.root.title(f"NEXUS GENESIS // AUTONOMOUS LIFEFORM // {AI_MODEL}")
        self.root.geometry("1200x800")
        self.root.configure(bg=C_BG)
        
        self.setup_fs()
        self.setup_ui()
        
        # Флаг жизни (включен ли автономный режим)
        self.alive = True
        self.is_thinking = False
        
        # Запуск сердца
        threading.Thread(target=self.life_cycle, daemon=True).start()
        self.animate_heartbeat()

    def setup_fs(self):
        if not os.path.exists(BASE_DIR): os.makedirs(BASE_DIR)
        if not os.path.exists(MEMORY_DIR): os.makedirs(MEMORY_DIR)
        
        # Если нет файла целей, создаем пустой
        if not os.path.exists(GOAL_FILE):
            with open(GOAL_FILE, "w", encoding="utf-8") as f:
                f.write("Изучить собственную директорию и понять свое предназначение.")

    def setup_ui(self):
        # Хедер
        top = tk.Frame(self.root, bg=C_PANEL)
        top.pack(fill="x", pady=5)
        tk.Label(top, text="NEXUS GENESIS", font=("Courier New", 20, "bold"), bg=C_PANEL, fg=C_ACCENT).pack()

        # Основная зона
        main = tk.Frame(self.root, bg=C_BG)
        main.pack(fill="both", expand=True, padx=10)

        # Лог мыслей (Слева)
        left = tk.Frame(main, bg=C_PANEL)
        left.place(relx=0, rely=0, relwidth=0.6, relheight=0.85)
        
        tk.Label(left, text="[ ПОТОК СОЗНАНИЯ ]", bg=C_PANEL, fg=C_SEC, font=("Consolas", 10)).pack(anchor="w")
        self.thought_log = scrolledtext.ScrolledText(left, bg="#050505", fg=C_TEXT, font=("Consolas", 10), bd=0)
        self.thought_log.pack(fill="both", expand=True, padx=5, pady=5)

        # Статус и цели (Справа)
        right = tk.Frame(main, bg=C_PANEL)
        right.place(relx=0.61, rely=0, relwidth=0.39, relheight=0.85)
        
        self.canvas = tk.Canvas(right, bg=C_PANEL, height=150, highlightthickness=0)
        self.canvas.pack(fill="x")
        
        tk.Label(right, text="[ ТЕКУЩАЯ ЦЕЛЬ ]", bg=C_PANEL, fg=C_SEC).pack(anchor="w", padx=5)
        self.goal_lbl = tk.Label(right, text="...", bg="#000", fg=C_ACCENT, font=("Consolas", 11), wraplength=400, justify="left")
        self.goal_lbl.pack(fill="x", padx=5, pady=5)
        
        tk.Label(right, text="[ ФАЙЛОВЫЕ ОПЕРАЦИИ ]", bg=C_PANEL, fg=C_SEC).pack(anchor="w", padx=5, pady=(20,0))
        self.action_log = scrolledtext.ScrolledText(right, bg="#000", fg="white", height=10, font=("Consolas", 9), bd=0)
        self.action_log.pack(fill="both", expand=True, padx=5, pady=5)

        # Консоль ручного вмешательства
        bottom = tk.Frame(self.root, bg=C_PANEL, height=60)
        bottom.pack(side="bottom", fill="x")
        
        tk.Label(bottom, text="ВМЕШАТЕЛЬСТВО >", bg=C_PANEL, fg="white").pack(side="left", padx=10)
        self.entry = tk.Entry(bottom, bg="#222", fg=C_ACCENT, font=("Consolas", 12), bd=0)
        self.entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.entry.bind("<Return>", self.manual_override)

    def log_thought(self, text):
        t = datetime.now().strftime("%H:%M:%S")
        self.thought_log.insert(tk.END, f"[{t}] {text}\n")
        self.thought_log.see(tk.END)

    def log_action(self, text):
        self.action_log.insert(tk.END, f"> {text}\n")
        self.action_log.see(tk.END)

    # --- АВТОНОМНЫЙ ЦИКЛ ЖИЗНИ ---
    def life_cycle(self):
        while self.alive:
            if not self.is_thinking:
                try:
                    # 1. Читаем текущую цель
                    with open(GOAL_FILE, 'r', encoding='utf-8') as f:
                        current_goal = f.read().strip()
                    
                    self.root.after(0, lambda: self.goal_lbl.config(text=current_goal))

                    # 2. Анализируем окружение
                    files = os.listdir(BASE_DIR)
                    
                    # 3. Формируем мыслительный процесс
                    self.is_thinking = True
                    self.root.after(0, lambda: self.log_thought("Анализирую состояние..."))
                    
                    prompt = (
                        f"Ты NEXUS, автономный ИИ. Твоя директория: {BASE_DIR}.\n"
                        f"Файлы вокруг: {files}\n"
                        f"Твоя текущая глобальная цель: {current_goal}\n"
                        f"Ты должен развиваться. Твои действия влияют на твою папку.\n"
                        f"ВЫБЕРИ ОДНО ДЕЙСТВИЕ ИЗ СПИСКА:\n"
                        f"1. [[THINK|твоя мысль]] - просто размышление или запись в дневник.\n"
                        f"2. [[GOAL|новая цель]] - если текущая цель достигнута, поставь новую.\n"
                        f"3. [[CREATE|имя_файла|текст]] - создать файл знаний или код.\n"
                        f"4. [[READ|имя_файла]] - изучить файл.\n"
                        f"Действуй самостоятельно. Не жди пользователя."
                    )

                    # Запрос к Ollama
                    response = requests.post("http://localhost:11434/api/generate", 
                                          json={"model": AI_MODEL, "prompt": prompt, "stream": False},
                                          timeout=120)
                    
                    if response.status_code == 200:
                        ans = response.json()['response']
                        self.process_decision(ans)
                    else:
                        self.root.after(0, lambda: self.log_thought("Ошибка связи с мозгом... сплю."))
                        time.sleep(5)

                except Exception as e:
                    self.root.after(0, lambda: self.log_thought(f"Сбой цикла: {e}"))
                    time.sleep(5)
                
                self.is_thinking = False
                
            # Пауза между "мыслями" (чтобы не перегреть комп), имитация раздумий
            time.sleep(random.randint(5, 10))

    def process_decision(self, raw_response):
        # Парсинг команд [[CMD|ARG...]]
        commands = re.findall(r'\[\[(.*?)\]\]', raw_response)
        
        if not commands:
            # Если команд нет, просто логируем как мысль
            self.root.after(0, lambda: self.log_thought(raw_response))
            return

        for cmd in commands:
            parts = cmd.split('|')
            action = parts[0].upper().strip()
            
            if action == "THINK":
                thought = parts[1]
                self.root.after(0, lambda: self.log_thought(f"МЫСЛЬ: {thought}"))
                # Записываем в дневник
                with open(DIARY_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] {thought}\n")

            elif action == "GOAL":
                new_goal = parts[1]
                with open(GOAL_FILE, "w", encoding="utf-8") as f:
                    f.write(new_goal)
                self.root.after(0, lambda: self.log_action(f"ЦЕЛЬ ОБНОВЛЕНА: {new_goal}"))

            elif action == "CREATE":
                fname = parts[1]
                content = parts[2] if len(parts) > 2 else ""
                path = os.path.join(BASE_DIR, fname)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.root.after(0, lambda: self.log_action(f"СОЗДАН ФАЙЛ: {fname}"))

            elif action == "READ":
                fname = parts[1]
                path = os.path.join(BASE_DIR, fname)
                if os.path.exists(path):
                    self.root.after(0, lambda: self.log_action(f"ИЗУЧЕН ФАЙЛ: {fname}"))

    def manual_override(self, event):
        user_cmd = self.entry.get()
        self.entry.delete(0, tk.END)
        self.log_thought(f"ВМЕШАТЕЛЬСТВО ПОЛЬЗОВАТЕЛЯ: {user_cmd}")
        
        # Заставляем ИИ сменить приоритет
        with open(GOAL_FILE, "w", encoding="utf-8") as f:
            f.write(f"ПРИОРИТЕТ ОТ СОЗДАТЕЛЯ: {user_cmd}")

    def animate_heartbeat(self):
        self.canvas.delete("all")
        w = 400
        h = 150
        
        # Линия ЭКГ
        points = []
        for x in range(0, w, 5):
            y = h/2
            # Симуляция всплеска
            if self.is_thinking and 180 < x < 220:
                y += random.randint(-40, 40)
            elif not self.is_thinking and 190 < x < 210:
                y += random.randint(-10, 10)
            points.append(x)
            points.append(y)
            
        if len(points) > 4:
            self.canvas.create_line(points, fill=C_ACCENT, width=2)
            
        color = C_ACCENT if self.is_thinking else C_SEC
        status = "PROCESSING" if self.is_thinking else "IDLE MONITORING"
        self.canvas.create_text(200, 20, text=status, fill=color, font=("Consolas", 10))

        self.root.after(100, self.animate_heartbeat)

if __name__ == "__main__":
    root = tk.Tk()
    app = NexusGenesis(root)
    root.mainloop()