import os
import glob
import threading
import uuid
import hashlib
from datetime import datetime, timezone

import customtkinter as ctk
import requests
from client_crypto import RNTClientCrypto
from ai_engine import RNTAIEngine

# ПОДКЛЮЧАЕМ НАШ НОВЫЙ ФАЙЛ ГРАФА
from graph_viewer import show_neural_graph

# --- Конфигурация системы ---
BASE_URL = "http://127.0.0.1:8000"
MASTER_PASSWORD = "StrictPassword2026!"
USERNAME = "rnt_admin"
VAULT_DIR = "RNT_Vault"

# --- Визуальная архитектура ---
BG_COLOR = "#000000"
PANEL_COLOR = "#070709"
ACCENT_COLOR = "#00D4FF"
TEXT_COLOR = "#FFFFFF"
MUTED_TEXT = "#5A5A66"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class RNTNotesApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RNT Notes Core - Local-First ZK Client")
        self.geometry("1200x750")
        self.configure(fg_color=BG_COLOR)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.crypto = RNTClientCrypto(master_password=MASTER_PASSWORD)
        self.ai = RNTAIEngine(vault_path=VAULT_DIR)
        self.token = None
        self.current_file_path = None
        
        self._ensure_vault_exists()

        self._build_sidebar()
        self._build_editor()

        self._load_local_vault()
        
        threading.Thread(target=self._initialize_e2e_session, daemon=True).start()

        # Бинд для SpaceX терминала
        self.bind("<Control-k>", self._toggle_terminal)
        self.terminal_frame = None

    def _ensure_vault_exists(self):
        if not os.path.exists(VAULT_DIR):
            os.makedirs(VAULT_DIR)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=PANEL_COLOR, corner_radius=0, width=280)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Сдвигаем список заметок на 4 строку, чтобы освободить место для кнопки
        self.sidebar.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar, text="RNT NOTES", 
            font=ctk.CTkFont(family="Consolas", size=26, weight="bold"), 
            text_color=ACCENT_COLOR
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 15), sticky="w")

        self.add_btn = ctk.CTkButton(
            self.sidebar, text="+ Новый файл", 
            fg_color=ACCENT_COLOR, text_color=BG_COLOR, 
            font=ctk.CTkFont(weight="bold", size=14),
            hover_color="#00A3CC", corner_radius=6, height=36,
            command=self.create_new_note
        )
        self.add_btn.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="ew")

        # --- НАША НОВАЯ КНОПКА ГРАФА ---
        self.graph_btn = ctk.CTkButton(
            self.sidebar, text="🕸️ Neural Graph", 
            fg_color="transparent", border_width=1, border_color=ACCENT_COLOR,
            text_color=ACCENT_COLOR, hover_color="#05151D",
            font=ctk.CTkFont(weight="bold", size=13),
            corner_radius=6, height=32,
            command=lambda: threading.Thread(target=show_neural_graph, daemon=True).start()
        )
        self.graph_btn.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.search_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.search_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.search_frame, placeholder_text="AI Поиск по смыслу...", 
            font=ctk.CTkFont(size=12), border_color=MUTED_TEXT, text_color=TEXT_COLOR
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<Return>", self._start_ai_search)

        self.notes_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.notes_list.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)

    def _build_editor(self):
        self.editor_frame = ctk.CTkFrame(self, fg_color=BG_COLOR, corner_radius=0)
        self.editor_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.editor_frame.grid_columnconfigure(0, weight=1)
        self.editor_frame.grid_rowconfigure(1, weight=1)

        self.header_frame = ctk.CTkFrame(self.editor_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.note_title = ctk.CTkEntry(
            self.header_frame, placeholder_text="Название файла...", 
            font=ctk.CTkFont(size=32, weight="bold"),
            fg_color="transparent", border_width=0, text_color=TEXT_COLOR
        )
        self.note_title.grid(row=0, column=0, sticky="ew")
        self.note_title.bind("<FocusOut>", lambda e: self.save_local())

        self.note_editor = ctk.CTkTextbox(
            self.editor_frame, font=ctk.CTkFont(family="Consolas", size=16),
            fg_color=PANEL_COLOR, text_color=TEXT_COLOR, corner_radius=10,
            border_width=1, border_color="#15151A", wrap="word"
        )
        self.note_editor.grid(row=1, column=0, sticky="nsew")
        self.note_editor.bind("<FocusOut>", lambda e: self.save_local())

        self.action_frame = ctk.CTkFrame(self.editor_frame, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        self.action_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.action_frame, text="● Локальный режим (Offline)", 
            text_color=MUTED_TEXT, font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self.sync_btn = ctk.CTkButton(
            self.action_frame, text="Зашифровать и Отправить", 
            fg_color="transparent", border_width=1.5, border_color=ACCENT_COLOR,
            text_color=ACCENT_COLOR, hover_color="#05151D", corner_radius=6,
            command=self.trigger_crypto_sync
        )
        self.sync_btn.grid(row=0, column=1, sticky="e")

    # --- AI Поиск с безопасной многопоточностью ---

    def _start_ai_search(self, event=None):
        query = self.search_entry.get().strip()
        if not query:
            self._load_local_vault()
            return
        self.status_label.configure(text="● AI обрабатывает запрос...", text_color=ACCENT_COLOR)
        threading.Thread(target=self._async_perform_ai_search, args=(query,), daemon=True).start()

    def _async_perform_ai_search(self, query):
        if not self.ai.embeddings_db:
            self.ai.build_index()

        results = self.ai.search(query)
        self.after(0, lambda: self._render_search_results(results))
        self.after(0, lambda: self.status_label.configure(text="● AI поиск завершен", text_color=MUTED_TEXT))

    def _render_search_results(self, results):
        for widget in self.notes_list.winfo_children():
            widget.destroy()
            
        if not results:
            lbl = ctk.CTkLabel(self.notes_list, text="Совпадений нет", text_color=MUTED_TEXT)
            lbl.pack(pady=20)
            return

        for file_path, score in results:
            if score < 0.3: continue 
            filename = os.path.basename(file_path).replace(".md", "")
            btn = ctk.CTkButton(
                self.notes_list, text=f"{filename} ({score:.2f})", anchor="w",
                fg_color="transparent", text_color=TEXT_COLOR,
                hover_color="#15151A", corner_radius=6, font=ctk.CTkFont(size=14),
                command=lambda p=file_path: self._load_file_to_editor(p)
            )
            btn.pack(fill="x", pady=2)

    # --- Локальная логика (Obsidian Core + Smart Edges) ---

    def _load_local_vault(self):
        for widget in self.notes_list.winfo_children():
            widget.destroy()
            
        md_files = glob.glob(os.path.join(VAULT_DIR, "*.md"))
        
        for file_path in md_files:
            filename = os.path.basename(file_path).replace(".md", "")
            active = (file_path == self.current_file_path)
            color = TEXT_COLOR if active else MUTED_TEXT
            hover = "#15151A"
            
            btn = ctk.CTkButton(
                self.notes_list, text=filename, anchor="w",
                fg_color=hover if active else "transparent", text_color=color,
                hover_color=hover, corner_radius=6, font=ctk.CTkFont(size=14),
                command=lambda p=file_path: self._load_file_to_editor(p)
            )
            btn.pack(fill="x", pady=2)

    def _load_file_to_editor(self, file_path):
        self.save_local(trigger_ai=False)
        self.current_file_path = file_path
        
        title = os.path.basename(file_path).replace(".md", "")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.note_title.delete(0, 'end')
        self.note_title.insert(0, title)
        
        self.note_editor.delete("1.0", 'end')
        self.note_editor.insert("1.0", content)
        
        self.status_label.configure(text="● Открыт локальный файл", text_color=MUTED_TEXT)
        self._load_local_vault() 

    def create_new_note(self):
        self.save_local(trigger_ai=False)
        self.current_file_path = None
        self.note_title.delete(0, 'end')
        self.note_editor.delete("1.0", 'end')
        
        self.note_title.insert(0, "Без названия")
        self.status_label.configure(text="● Ожидание ввода...", text_color=MUTED_TEXT)
        self._load_local_vault()

    def save_local(self, trigger_ai=True):
        title = self.note_title.get().strip()
        content = self.note_editor.get("1.0", 'end-1c')
        
        if not title:
            return
            
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_title:
            safe_title = "Без названия"

        new_file_path = os.path.join(VAULT_DIR, f"{safe_title}.md")
        
        if self.current_file_path and self.current_file_path != new_file_path and os.path.exists(self.current_file_path):
            os.remove(self.current_file_path)

        with open(new_file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        self.current_file_path = new_file_path
        
        if trigger_ai and content.strip():
            threading.Thread(target=self._generate_smart_edges, args=(new_file_path, content), daemon=True).start()

        self._load_local_vault()

    def _generate_smart_edges(self, file_path, content):
        if not self.ai.embeddings_db:
            self.ai.build_index()
            
        related = self.ai.find_related_notes(content, file_path, threshold=0.85)
        
        if related:
            new_links = [f"[[{name}]]" for name in related if f"[[{name}]]" not in content]
            
            if new_links:
                links_str = ", ".join(new_links)
                append_text = f"\n\n> 🔗 AI Связи: {links_str}\n"
                
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(append_text)
                
                if self.current_file_path == file_path:
                    self.after(0, lambda: self.note_editor.insert("end", append_text))
                    self.after(0, lambda: self.status_label.configure(text="● AI обнаружил и добавил связи", text_color="#00FF9D"))
                    
                self.ai.build_index()

    # --- Облачная логика E2E ---

    def _initialize_e2e_session(self):
        auth_data = {"username": USERNAME, "password": MASTER_PASSWORD, "public_key": "dummy"}
        try:
            r = requests.post(f"{BASE_URL}/api/v1/auth/register", json=auth_data)
            if r.status_code == 400:
                r = requests.post(f"{BASE_URL}/api/v1/auth/login", data=auth_data)
            
            self.token = r.json().get("access_token")
            if self.token:
                self.after(0, lambda: self.status_label.configure(text="● E2E Сессия Активна", text_color=ACCENT_COLOR))
        except Exception:
            pass 

    def trigger_crypto_sync(self):
        self.save_local(trigger_ai=False)
        
        if not self.token:
            self.status_label.configure(text="[!] Ошибка сети. Файл сохранен только локально.", text_color="#FF4444")
            return

        title = self.note_title.get()
        content = self.note_editor.get("1.0", 'end-1c')
        self.status_label.configure(text="● Шифрование (AES-256-GCM)...", text_color=ACCENT_COLOR)
        
        threading.Thread(target=self._async_sync_worker, args=(title, content), daemon=True).start()
        
    def _async_sync_worker(self, title, content):
        full_plaintext = f"{title}|||{content}"
        encrypted_payload, nonce = self.crypto.encrypt_note(full_plaintext)
        
        note_id = str(uuid.UUID(hashlib.md5(title.encode()).hexdigest()))
        sync_payload = {
            "last_sync_time": datetime.now(timezone.utc).isoformat(),
            "notes": [{
                "id": note_id,
                "encrypted_payload": encrypted_payload,
                "nonce": nonce,
                "encrypted_embedding": None,
                "version": 1
            }],
            "edges": []
        }
        
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            r = requests.post(f"{BASE_URL}/api/v1/sync", json=sync_payload, headers=headers)
            if r.status_code == 200:
                self.after(0, lambda: self.status_label.configure(text="● Зашифровано и в облаке (Zero-Knowledge)", text_color="#00FF9D"))
        except Exception:
            self.after(0, lambda: self.status_label.configure(text="[!] Сервер недоступен", text_color="#FF4444"))

    # --- RNT Terminal (SpaceX Style) ---

    def _toggle_terminal(self, event=None):
        if self.terminal_frame and self.terminal_frame.winfo_ismapped():
            self.terminal_frame.place_forget()
        else:
            self._show_terminal()

    def _show_terminal(self):
        if not self.terminal_frame:
            self.terminal_frame = ctk.CTkFrame(
                self, fg_color="#0D0D12", corner_radius=12, 
                border_width=2, border_color=ACCENT_COLOR
            )
            
            self.term_entry = ctk.CTkEntry(
                self.terminal_frame, placeholder_text="Ask RNT Co-Pilot (e.g. 'Сделай саммари архитектуры')...",
                font=ctk.CTkFont(family="Consolas", size=16),
                fg_color="transparent", border_width=0, text_color=ACCENT_COLOR
            )
            self.term_entry.pack(fill="x", padx=15, pady=10)
            self.term_entry.bind("<Return>", self._process_terminal_command)
            
            self.term_output = ctk.CTkTextbox(
                self.terminal_frame, font=ctk.CTkFont(family="Consolas", size=14),
                fg_color="transparent", text_color=TEXT_COLOR, wrap="word", height=200
            )
            self.term_output.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.terminal_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.6)
        self.term_entry.focus()
        
    def _process_terminal_command(self, event=None):
        query = self.term_entry.get().strip()
        if not query:
            return
            
        self.term_entry.delete(0, 'end')
        self.term_output.delete("1.0", 'end')
        self.term_output.insert("1.0", f"> {query}\n[SYSTEM] Сканирование графа и генерация ответа...\n")
        self.update_idletasks()
        
        threading.Thread(target=self._run_rag_worker, args=(query,), daemon=True).start()

    def _run_rag_worker(self, query):
        if not self.ai.embeddings_db:
            self.ai.build_index()
            
        results = self.ai.search(query, top_k=3)
        answer = self.ai.ask_copilot(query, results)
        
        self.after(0, lambda: self.term_output.insert("end", f"\n[RNT CO-PILOT]:\n{answer}\n"))

if __name__ == "__main__":
    app = RNTNotesApp()
    app.mainloop()