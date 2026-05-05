import tkinter as tk
from tkinter import messagebox, Listbox, MULTIPLE, END
import requests
import json
import os
import threading
from urllib.parse import quote

class GitHubUserFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub User Finder")
        self.root.geometry("700x500")
        self.root.resizable(True, True)

        # Данные
        self.favorites = []          # список словарей {"login": ..., "id": ...}
        self.current_results = []    # временный список результатов поиска (словари)

        # Загрузка избранных из файла
        self.favorites_file = "favorites.json"
        self.load_favorites()

        # GUI элементы
        self.create_widgets()

    def create_widgets(self):
        # Верхняя панель поиска
        search_frame = tk.Frame(self.root)
        search_frame.pack(pady=10, padx=10, fill=tk.X)

        tk.Label(search_frame, text="Поиск пользователя GitHub:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = tk.Entry(search_frame, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_btn = tk.Button(search_frame, text="Найти", command=self.search_user)
        self.search_btn.pack(side=tk.LEFT, padx=5)

        # Основная область: список результатов и избранное
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Результаты поиска
        results_frame = tk.LabelFrame(main_frame, text="Результаты поиска")
        results_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.results_listbox = Listbox(results_frame, width=40, height=20)
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar = tk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_listbox.yview)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_listbox.config(yscrollcommand=results_scrollbar.set)

        # Избранное
        favorites_frame = tk.LabelFrame(main_frame, text="Избранное")
        favorites_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.favorites_listbox = Listbox(favorites_frame, width=40, height=20)
        self.favorites_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fav_scrollbar = tk.Scrollbar(favorites_frame, orient=tk.VERTICAL, command=self.favorites_listbox.yview)
        fav_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.favorites_listbox.config(yscrollcommand=fav_scrollbar.set)

        # Кнопки управления
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.add_btn = tk.Button(btn_frame, text="➡ Добавить в избранное", command=self.add_to_favorites)
        self.add_btn.pack(side=tk.LEFT, padx=5)

        self.remove_btn = tk.Button(btn_frame, text="❌ Удалить из избранного", command=self.remove_from_favorites)
        self.remove_btn.pack(side=tk.LEFT, padx=5)

        # Статусная строка
        self.status_label = tk.Label(self.root, text="Готов", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Обновление отображения избранных
        self.update_favorites_display()

    def search_user(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Предупреждение", "Поле поиска не может быть пустым!")
            return

        self.status_label.config(text="Поиск...")
        self.search_btn.config(state=tk.DISABLED)

        # Запуск запроса в отдельном потоке
        thread = threading.Thread(target=self._search_api, args=(query,))
        thread.daemon = True
        thread.start()

    def _search_api(self, query):
        try:
            url = f"https://api.github.com/search/users?q={quote(query)}&per_page=30"
            headers = {"Accept": "application/vnd.github.v3+json"}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                self.current_results = [{"login": u["login"], "id": u["id"]} for u in items]

                # Обновление GUI в основном потоке
                self.root.after(0, self._display_results)
                self.root.after(0, lambda: self.status_label.config(text=f"Найдено пользователей: {len(items)}"))
            else:
                error_msg = f"Ошибка API: {response.status_code}"
                self.root.after(0, lambda: messagebox.showerror("Ошибка", error_msg))
                self.root.after(0, lambda: self.status_label.config(text="Ошибка запроса"))
        except requests.exceptions.RequestException as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка сети", str(e)))
            self.root.after(0, lambda: self.status_label.config(text="Ошибка сети"))
        finally:
            self.root.after(0, lambda: self.search_btn.config(state=tk.NORMAL))

    def _display_results(self):
        self.results_listbox.delete(0, END)
        for user in self.current_results:
            self.results_listbox.insert(END, f"{user['login']} (id: {user['id']})")

    def add_to_favorites(self):
        selected = self.results_listbox.curselection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите пользователя из результатов поиска")
            return

        index = selected[0]
        user = self.current_results[index]

        # Проверка, не добавлен ли уже
        if any(fav["id"] == user["id"] for fav in self.favorites):
            messagebox.showinfo("Информация", f"Пользователь {user['login']} уже в избранном")
            return

        self.favorites.append(user)
        self.save_favorites()
        self.update_favorites_display()
        self.status_label.config(text=f"Добавлен {user['login']} в избранное")

    def remove_from_favorites(self):
        selected = self.favorites_listbox.curselection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите пользователя в списке избранного")
            return

        index = selected[0]
        removed_user = self.favorites.pop(index)
        self.save_favorites()
        self.update_favorites_display()
        self.status_label.config(text=f"Удалён {removed_user['login']} из избранного")

    def update_favorites_display(self):
        self.favorites_listbox.delete(0, END)
        for user in self.favorites:
            self.favorites_listbox.insert(END, f"{user['login']} (id: {user['id']})")

    def load_favorites(self):
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, "r", encoding="utf-8") as f:
                    self.favorites = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.favorites = []
        else:
            self.favorites = []

    def save_favorites(self):
        with open(self.favorites_file, "w", encoding="utf-8") as f:
            json.dump(self.favorites, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubUserFinder(root)
    root.mainloop()