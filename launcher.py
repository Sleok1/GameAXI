import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import threading
import json
import time
import requests
import random
import re
from datetime import datetime
from pathlib import Path
from typing import List

# --- КОНФИГУРАЦИЯ ---
DEFAULT_SETTINGS = {
    "ai_model": "llama3",
    "ollama_url": "http://localhost:11434/api/generate",
    "min_delay": 5,
    "max_delay": 10,
    "request_timeout": 120,
    "temperature": 0.2,
    "top_p": 0.9,
    "num_predict": 512,
    "context_chars": 3000,
    "memory_files_limit": 5,
    "recent_diary_lines": 6,
    "assistant_mode": True,
    "system_directive": (
        "Ты действуешь как внимательный, надежный и прагматичный ИИ. "
        "Используй контекст, избегай выдумок и делай полезные выводы."
    ),
    "assistant_persona": (
        "Ты персональный ассистент пользователя. Отвечай по-русски, "
        "кратко, полезно и по делу. При необходимости предлагай следующий шаг."
    ),
}

LAUNCHER_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = LAUNCHER_DIR / "nexus_settings.json"


def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                settings.update({
                    "ai_model": raw.get("ai_model", settings["ai_model"]),
                    "ollama_url": raw.get("ollama_url", settings["ollama_url"]),
                    "base_dir": raw.get("base_dir"),
                    "min_delay": raw.get("min_delay", settings["min_delay"]),
                    "max_delay": raw.get("max_delay", settings["max_delay"]),
                    "request_timeout": raw.get("request_timeout", settings["request_timeout"]),
                    "temperature": raw.get("temperature", settings["temperature"]),
                    "top_p": raw.get("top_p", settings["top_p"]),
                    "num_predict": raw.get("num_predict", settings["num_predict"]),
                    "context_chars": raw.get("context_chars", settings["context_chars"]),
                    "memory_files_limit": raw.get("memory_files_limit", settings["memory_files_limit"]),
                    "recent_diary_lines": raw.get("recent_diary_lines", settings["recent_diary_lines"]),
                    "assistant_mode": raw.get("assistant_mode", settings["assistant_mode"]),
                    "system_directive": raw.get("system_directive", settings["system_directive"]),
                    "assistant_persona": raw.get("assistant_persona", settings["assistant_persona"]),
                })
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def clamp_int(value, default, minimum=1, maximum=10_000):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


def clamp_float(value, default, minimum=0.0, maximum=1.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


SETTINGS = load_settings()
SETTINGS["min_delay"] = clamp_int(SETTINGS["min_delay"], DEFAULT_SETTINGS["min_delay"], 1, 60)
SETTINGS["max_delay"] = clamp_int(SETTINGS["max_delay"], DEFAULT_SETTINGS["max_delay"], 1, 300)
if SETTINGS["max_delay"] < SETTINGS["min_delay"]:
    SETTINGS["max_delay"] = SETTINGS["min_delay"]
SETTINGS["request_timeout"] = clamp_int(SETTINGS["request_timeout"], DEFAULT_SETTINGS["request_timeout"], 5, 600)
SETTINGS["num_predict"] = clamp_int(SETTINGS["num_predict"], DEFAULT_SETTINGS["num_predict"], 64, 4096)
SETTINGS["context_chars"] = clamp_int(SETTINGS["context_chars"], DEFAULT_SETTINGS["context_chars"], 500, 20_000)
SETTINGS["memory_files_limit"] = clamp_int(
    SETTINGS["memory_files_limit"], DEFAULT_SETTINGS["memory_files_limit"], 1, 50
)
SETTINGS["recent_diary_lines"] = clamp_int(
    SETTINGS["recent_diary_lines"], DEFAULT_SETTINGS["recent_diary_lines"], 1, 100
)
SETTINGS["temperature"] = clamp_float(SETTINGS["temperature"], DEFAULT_SETTINGS["temperature"], 0.0, 2.0)
SETTINGS["top_p"] = clamp_float(SETTINGS["top_p"], DEFAULT_SETTINGS["top_p"], 0.1, 1.0)
SETTINGS["assistant_mode"] = bool(SETTINGS.get("assistant_mode", True))
AI_MODEL = SETTINGS["ai_model"]
OLLAMA_URL = SETTINGS["ollama_url"]
BASE_DIR = Path(SETTINGS.get("base_dir") or LAUNCHER_DIR).resolve()
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
MEMORY_DIR = BASE_DIR / "memory"
GOAL_FILE = DATA_DIR / "current_goal.txt"
DIARY_FILE = LOG_DIR / "evolution_diary.txt"

UI_FONT = ("Consolas", 10)
TITLE_FONT = ("Courier New", 20, "bold")

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
        self.paused = False
        self.status_text = tk.StringVar(value="CONNECTING...")
        self.metrics_text = tk.StringVar(value="Готов")
        
        # Запуск сердца
        threading.Thread(target=self.life_cycle, daemon=True).start()
        self.animate_heartbeat()

    def setup_fs(self):
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        
        # Если нет файла целей, создаем пустой
        if not GOAL_FILE.exists():
            with GOAL_FILE.open("w", encoding="utf-8") as f:
                f.write("Изучить собственную директорию и понять свое предназначение.")
        if not DIARY_FILE.exists():
            DIARY_FILE.touch()

    def setup_ui(self):
        # Хедер
        top = tk.Frame(self.root, bg=C_PANEL)
        top.pack(fill="x", pady=5)
        tk.Label(top, text="NEXUS GENESIS", font=TITLE_FONT, bg=C_PANEL, fg=C_ACCENT).pack(side="left", padx=10)

        controls = tk.Frame(top, bg=C_PANEL)
        controls.pack(side="right", padx=10)
        self.btn_toggle = ttk.Button(controls, text="Пауза", command=self.toggle_pause)
        self.btn_toggle.pack(side="left", padx=5)
        ttk.Button(controls, text="Очистить логи", command=self.clear_logs).pack(side="left", padx=5)
        ttk.Button(controls, text="Перезагрузить настройки", command=self.reload_settings).pack(side="left", padx=5)

        # Основная зона
        main = tk.Frame(self.root, bg=C_BG)
        main.pack(fill="both", expand=True, padx=10)

        # Лог мыслей (Слева)
        left = tk.Frame(main, bg=C_PANEL)
        left.place(relx=0, rely=0, relwidth=0.6, relheight=0.85)
        
        tk.Label(left, text="[ ПОТОК СОЗНАНИЯ ]", bg=C_PANEL, fg=C_SEC, font=UI_FONT).pack(anchor="w")
        self.thought_log = scrolledtext.ScrolledText(left, bg="#050505", fg=C_TEXT, font=UI_FONT, bd=0)
        self.thought_log.pack(fill="both", expand=True, padx=5, pady=5)

        # Статус и цели (Справа)
        right = tk.Frame(main, bg=C_PANEL)
        right.place(relx=0.61, rely=0, relwidth=0.39, relheight=0.85)
        
        self.canvas = tk.Canvas(right, bg=C_PANEL, height=150, highlightthickness=0)
        self.canvas.pack(fill="x")

        self.status_lbl = tk.Label(right, textvariable=self.status_text, bg=C_PANEL, fg=C_TEXT, font=("Consolas", 9))
        self.status_lbl.pack(anchor="w", padx=5, pady=(0, 5))
        self.metrics_lbl = tk.Label(right, textvariable=self.metrics_text, bg=C_PANEL, fg=C_TEXT, font=("Consolas", 9))
        self.metrics_lbl.pack(anchor="w", padx=5, pady=(0, 10))

        info_text = f"Модель: {AI_MODEL}\nДиректория: {BASE_DIR}\nДанные: {DATA_DIR}"
        self.info_lbl = tk.Label(right, text=info_text, bg=C_PANEL, fg=C_TEXT, font=("Consolas", 8), justify="left")
        self.info_lbl.pack(anchor="w", padx=5, pady=(0, 10))
        
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

    def toggle_pause(self):
        self.paused = not self.paused
        self.btn_toggle.config(text="Продолжить" if self.paused else "Пауза")
        self.update_status("PAUSED" if self.paused else "ONLINE", C_SEC if self.paused else C_ACCENT)

    def clear_logs(self):
        self.thought_log.delete("1.0", tk.END)
        self.action_log.delete("1.0", tk.END)

    def reload_settings(self):
        global SETTINGS, AI_MODEL, OLLAMA_URL, BASE_DIR, DATA_DIR, LOG_DIR, MEMORY_DIR, GOAL_FILE, DIARY_FILE
        SETTINGS = load_settings()
        SETTINGS["min_delay"] = clamp_int(SETTINGS["min_delay"], DEFAULT_SETTINGS["min_delay"], 1, 60)
        SETTINGS["max_delay"] = clamp_int(SETTINGS["max_delay"], DEFAULT_SETTINGS["max_delay"], 1, 300)
        if SETTINGS["max_delay"] < SETTINGS["min_delay"]:
            SETTINGS["max_delay"] = SETTINGS["min_delay"]
        SETTINGS["request_timeout"] = clamp_int(SETTINGS["request_timeout"], DEFAULT_SETTINGS["request_timeout"], 5, 600)
        SETTINGS["num_predict"] = clamp_int(SETTINGS["num_predict"], DEFAULT_SETTINGS["num_predict"], 64, 4096)
        SETTINGS["context_chars"] = clamp_int(SETTINGS["context_chars"], DEFAULT_SETTINGS["context_chars"], 500, 20_000)
        SETTINGS["memory_files_limit"] = clamp_int(
            SETTINGS["memory_files_limit"], DEFAULT_SETTINGS["memory_files_limit"], 1, 50
        )
        SETTINGS["recent_diary_lines"] = clamp_int(
            SETTINGS["recent_diary_lines"], DEFAULT_SETTINGS["recent_diary_lines"], 1, 100
        )
        SETTINGS["temperature"] = clamp_float(SETTINGS["temperature"], DEFAULT_SETTINGS["temperature"], 0.0, 2.0)
        SETTINGS["top_p"] = clamp_float(SETTINGS["top_p"], DEFAULT_SETTINGS["top_p"], 0.1, 1.0)
        SETTINGS["assistant_mode"] = bool(SETTINGS.get("assistant_mode", True))
        AI_MODEL = SETTINGS["ai_model"]
        OLLAMA_URL = SETTINGS["ollama_url"]
        BASE_DIR = Path(SETTINGS.get("base_dir") or LAUNCHER_DIR).resolve()
        DATA_DIR = BASE_DIR / "data"
        LOG_DIR = BASE_DIR / "logs"
        MEMORY_DIR = BASE_DIR / "memory"
        GOAL_FILE = DATA_DIR / "current_goal.txt"
        DIARY_FILE = LOG_DIR / "evolution_diary.txt"
        self.setup_fs()
        self.root.title(f"NEXUS GENESIS // AUTONOMOUS LIFEFORM // {AI_MODEL}")
        self.info_lbl.config(text=f"Модель: {AI_MODEL}\nДиректория: {BASE_DIR}\nДанные: {DATA_DIR}")
        self.log_action("НАСТРОЙКИ ПЕРЕЗАГРУЖЕНЫ")

    def log_thought(self, text):
        t = datetime.now().strftime("%H:%M:%S")
        self.thought_log.insert(tk.END, f"[{t}] {text}\n")
        self.thought_log.see(tk.END)

    def log_action(self, text):
        self.action_log.insert(tk.END, f"> {text}\n")
        self.action_log.see(tk.END)

    def update_status(self, text, color=C_TEXT):
        self.status_text.set(text)
        self.status_lbl.config(fg=color)

    def update_metrics(self, text):
        self.metrics_text.set(text)

    def read_recent_lines(self, path: Path, limit: int) -> List[str]:
        try:
            with path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            return [line.rstrip() for line in lines[-limit:]]
        except OSError:
            return []

    def collect_memory_snippets(self) -> str:
        if not MEMORY_DIR.exists():
            return ""
        files = sorted(MEMORY_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        snippets = []
        for path in files[: SETTINGS["memory_files_limit"]]:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if not text.strip():
                continue
            snippets.append(f"- {path.name}: {text[:300]}")
        return "\n".join(snippets)

    def build_prompt(self, current_goal: str, files: List[str], diary_lines: List[str], memory_snippets: str) -> str:
        context = [
            f"Директория: {BASE_DIR}",
            f"Файлы: {files}",
            f"Текущая цель: {current_goal}",
        ]
        if diary_lines:
            context.append("Недавние заметки:\n" + "\n".join(f"* {line}" for line in diary_lines))
        if memory_snippets:
            context.append("Память:\n" + memory_snippets)
        context_block = "\n".join(context)
        if len(context_block) > SETTINGS["context_chars"]:
            context_block = context_block[: SETTINGS["context_chars"]] + "..."

        return (
            f"{SETTINGS['system_directive']}\n"
            "Ты NEXUS, автономный ИИ, действуешь аккуратно и целенаправленно.\n"
            "Твоя задача — улучшать проект и поддерживать порядок.\n"
            "Выдавай ровно ОДНУ команду в формате [[CMD|ARG...]] без лишнего текста.\n"
            "Команды:\n"
            "1. [[THINK|мысль]] — размышление или запись в дневник.\n"
            "2. [[GOAL|новая цель]] — обновить глобальную цель.\n"
            "3. [[CREATE|имя_файла|текст]] — создать файл знаний или кода.\n"
            "4. [[READ|имя_файла]] — изучить файл.\n"
            "Пример: [[THINK|Нужно изучить структуру памяти.]]\n"
            f"{context_block}\n"
            "Действуй самостоятельно и прагматично."
        )

    def build_assistant_prompt(self, user_text: str, diary_lines: List[str], memory_snippets: str) -> str:
        context = []
        if diary_lines:
            context.append("Недавние заметки:\n" + "\n".join(f"* {line}" for line in diary_lines))
        if memory_snippets:
            context.append("Память:\n" + memory_snippets)
        context_block = "\n".join(context)
        if len(context_block) > SETTINGS["context_chars"]:
            context_block = context_block[: SETTINGS["context_chars"]] + "..."
        return (
            f"{SETTINGS['system_directive']}\n"
            f"{SETTINGS['assistant_persona']}\n"
            "Используй контекст, если он релевантен.\n"
            f"{context_block}\n"
            f"Запрос пользователя: {user_text}\n"
            "Ответ:"
        )

    # --- АВТОНОМНЫЙ ЦИКЛ ЖИЗНИ ---
    def life_cycle(self):
        while self.alive:
            if not self.is_thinking and not self.paused:
                try:
                    # 1. Читаем текущую цель
                    with open(GOAL_FILE, 'r', encoding='utf-8') as f:
                        current_goal = f.read().strip()
                    
                    self.root.after(0, lambda: self.goal_lbl.config(text=current_goal))

                    # 2. Анализируем окружение
                    files = os.listdir(BASE_DIR)
                    diary_lines = self.read_recent_lines(DIARY_FILE, SETTINGS["recent_diary_lines"])
                    memory_snippets = self.collect_memory_snippets()
                    
                    # 3. Формируем мыслительный процесс
                    self.is_thinking = True
                    self.root.after(0, lambda: self.log_thought("Анализирую состояние..."))
                    
                    prompt = self.build_prompt(current_goal, files, diary_lines, memory_snippets)

                    # Запрос к Ollama
                    self.root.after(0, lambda: self.update_status("CONNECTING...", C_TEXT))
                    started = time.time()
                    response = requests.post(
                        OLLAMA_URL,
                        json={
                            "model": AI_MODEL,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": SETTINGS["temperature"],
                                "top_p": SETTINGS["top_p"],
                                "num_predict": SETTINGS["num_predict"],
                            },
                        },
                        timeout=SETTINGS["request_timeout"],
                    )
                    
                    if response.status_code == 200:
                        self.root.after(0, lambda: self.update_status("ONLINE", C_ACCENT))
                        ans = response.json()['response']
                        self.process_decision(ans)
                        elapsed = time.time() - started
                        self.root.after(0, lambda: self.update_metrics(f"Ответ за {elapsed:.1f} сек"))
                    else:
                        self.root.after(0, lambda: self.update_status("OFFLINE", C_ERR))
                        self.root.after(0, lambda: self.log_thought("Ошибка связи с мозгом... сплю."))
                        time.sleep(5)

                except Exception as e:
                    self.root.after(0, lambda: self.log_thought(f"Сбой цикла: {e}"))
                    time.sleep(5)
                
                self.is_thinking = False
                
            # Пауза между "мыслями" (чтобы не перегреть комп), имитация раздумий
            time.sleep(random.randint(SETTINGS["min_delay"], SETTINGS["max_delay"]))

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
                if len(parts) < 2:
                    continue
                thought = parts[1]
                self.root.after(0, lambda: self.log_thought(f"МЫСЛЬ: {thought}"))
                # Записываем в дневник
                with open(DIARY_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] {thought}\n")

            elif action == "GOAL":
                if len(parts) < 2:
                    continue
                new_goal = parts[1]
                with open(GOAL_FILE, "w", encoding="utf-8") as f:
                    f.write(new_goal)
                self.root.after(0, lambda: self.log_action(f"ЦЕЛЬ ОБНОВЛЕНА: {new_goal}"))

            elif action == "CREATE":
                if len(parts) < 2:
                    continue
                fname = parts[1]
                content = parts[2] if len(parts) > 2 else ""
                path = os.path.join(BASE_DIR, fname)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.root.after(0, lambda: self.log_action(f"СОЗДАН ФАЙЛ: {fname}"))

            elif action == "READ":
                if len(parts) < 2:
                    continue
                fname = parts[1]
                path = os.path.join(BASE_DIR, fname)
                if os.path.exists(path):
                    self.root.after(0, lambda: self.log_action(f"ИЗУЧЕН ФАЙЛ: {fname}"))

    def manual_override(self, event):
        user_cmd = self.entry.get()
        self.entry.delete(0, tk.END)
        if not user_cmd.strip():
            return
        if SETTINGS.get("assistant_mode", True):
            self.log_thought(f"ПОЛЬЗОВАТЕЛЬ: {user_cmd}")
            threading.Thread(target=self.handle_assistant_request, args=(user_cmd,), daemon=True).start()
        else:
            self.log_thought(f"ВМЕШАТЕЛЬСТВО ПОЛЬЗОВАТЕЛЯ: {user_cmd}")
            # Заставляем ИИ сменить приоритет
            with open(GOAL_FILE, "w", encoding="utf-8") as f:
                f.write(f"ПРИОРИТЕТ ОТ СОЗДАТЕЛЯ: {user_cmd}")

    def handle_assistant_request(self, user_text: str):
        diary_lines = self.read_recent_lines(DIARY_FILE, SETTINGS["recent_diary_lines"])
        memory_snippets = self.collect_memory_snippets()
        prompt = self.build_assistant_prompt(user_text, diary_lines, memory_snippets)
        try:
            self.root.after(0, lambda: self.update_status("ASSISTING...", C_TEXT))
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": AI_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": SETTINGS["temperature"],
                        "top_p": SETTINGS["top_p"],
                        "num_predict": SETTINGS["num_predict"],
                    },
                },
                timeout=SETTINGS["request_timeout"],
            )
            if response.status_code == 200:
                answer = response.json().get("response", "").strip()
                self.root.after(0, lambda: self.log_thought(f"АССИСТЕНТ: {answer}"))
                self.root.after(0, lambda: self.update_status("ONLINE", C_ACCENT))
            else:
                self.root.after(0, lambda: self.log_thought("Ассистент недоступен."))
                self.root.after(0, lambda: self.update_status("OFFLINE", C_ERR))
        except Exception as exc:
            self.root.after(0, lambda: self.log_thought(f"Сбой ассистента: {exc}"))
            self.root.after(0, lambda: self.update_status("OFFLINE", C_ERR))

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
