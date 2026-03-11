import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json
import os
import re

# ===================== 加载题库数据 =====================
def load_question_bank():
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "question_bank.json")
    if not os.path.exists(json_path):
        return {"chapter_name": "题库", "chapter_desc": ""}, []
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["chapter_info"], data["question_bank"]


def save_question_bank(ch_info, questions):
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "question_bank.json")
    data = {"chapter_info": ch_info, "question_bank": questions}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ===================== 进度记录功能 =====================
def load_user_progress():
    progress_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_progress.json")
    if not os.path.exists(progress_path):
        return []
    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_user_progress(completed_ids):
    progress_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_progress.json")
    with open(progress_path, "w", encoding="utf-8") as f:
        json.dump(completed_ids, f, ensure_ascii=False, indent=2)


def parse_md_questions(md_content):
    """从 Markdown 内容中提取 ```json 代码块，解析为题目列表。
    支持两种格式：
    1. 代码块内直接是数组 [...]
    2. 代码块内是对象 {...}，从中提取 question_bank 字段
    同时尝试提取 chapter_info（如果有的话）。
    """
    pattern = r'```json\s*\n(.*?)```'
    blocks = re.findall(pattern, md_content, re.DOTALL)
    if not blocks:
        raise ValueError("未在 Markdown 文件中找到 ```json 代码块")

    all_questions = []
    ch_info = None

    for block in blocks:
        block = block.strip()
        parsed = json.loads(block)
        if isinstance(parsed, list):
            all_questions.extend(parsed)
        elif isinstance(parsed, dict):
            if "question_bank" in parsed:
                all_questions.extend(parsed["question_bank"])
            if "chapter_info" in parsed:
                ch_info = parsed["chapter_info"]
            # 单个题目对象
            if "question" in parsed and "answer" in parsed:
                all_questions.append(parsed)

    if not all_questions:
        raise ValueError("JSON 代码块中未找到有效的题目数据")

    # 校验必要字段
    for i, q in enumerate(all_questions):
        if "question" not in q or "answer" not in q:
            raise ValueError(f"第 {i+1} 道题目缺少必要字段 (question/answer)")

    return ch_info, all_questions

chapter_info, question_bank = load_question_bank()

# ===================== 刷题软件核心类 =====================
class GaoxiangExamApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"高项备考填空刷题 - {chapter_info['chapter_name']}")
        self.root.geometry("820x680")

        # 初始化变量
        self.current_question_idx = 0
        self.wrong_questions = []
        self.correct_count = 0
        self.completed_ids = load_user_progress()
        self.all_questions = question_bank
        # 过滤已完成的题目
        self.question_list = [q for q in self.all_questions if q.get("id") not in self.completed_ids]

        self.create_widgets()
        self.load_question()

    def create_widgets(self):
        # 1. 标题栏
        tk.Label(self.root, text=f"{chapter_info['chapter_name']} 填空刷题",
                 font=("微软雅黑", 16, "bold")).pack(pady=8)
        tk.Label(self.root, text=chapter_info["chapter_desc"],
                 font=("微软雅黑", 9), fg="gray").pack()

        # 2. 模块标签
        self.module_label = tk.Label(self.root, text="", font=("微软雅黑", 10, "bold"), fg="#2266aa")
        self.module_label.pack(pady=(10, 0))

        # 3. 题目展示
        self.question_label = tk.Label(self.root, text="", font=("微软雅黑", 12),
                                       wraplength=720, justify="left")
        self.question_label.pack(pady=15)

        # 4. 作答输入
        answer_frame = tk.Frame(self.root)
        answer_frame.pack(pady=8)
        tk.Label(answer_frame, text="你的答案：", font=("微软雅黑", 11)).grid(row=0, column=0, padx=5)
        self.answer_entry = tk.Entry(answer_frame, font=("微软雅黑", 11), width=50)
        self.answer_entry.grid(row=0, column=1, padx=5)
        self.answer_entry.bind("<Return>", lambda e: self.on_enter_key())

        # 5. 按钮区域
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=12)
        self.submit_btn = tk.Button(btn_frame, text="提交答案", font=("微软雅黑", 11),
                                     command=self.check_answer, width=10)
        self.submit_btn.grid(row=0, column=0, padx=10)
        self.next_btn = tk.Button(btn_frame, text="下一题", font=("微软雅黑", 11),
                                   command=self.next_question, state=tk.DISABLED, width=10)
        self.next_btn.grid(row=0, column=1, padx=10)
        self.wrong_btn = tk.Button(btn_frame, text="查看错题本", font=("微软雅黑", 11),
                                    command=self.show_wrong_questions, width=10)
        self.wrong_btn.grid(row=0, column=2, padx=10)
        
        # 导入功能下拉菜单
        self.import_btn = ttk.Menubutton(btn_frame, text="导入题库", width=10)
        self.import_menu = tk.Menu(self.import_btn, tearoff=0)
        self.import_menu.add_command(label="导入 Markdown (.md)", command=self.import_md_file)
        self.import_menu.add_command(label="导入 JSON (.json)", command=self.import_json_file)
        self.import_btn["menu"] = self.import_menu
        self.import_btn.grid(row=0, column=3, padx=10)

        self.reset_btn = tk.Button(btn_frame, text="重置进度", font=("微软雅黑", 11),
                                    command=self.reset_user_progress, width=10, fg="#cc0000")
        self.reset_btn.grid(row=0, column=4, padx=10)

        # 6. 解析区域
        tk.Label(self.root, text="解析：", font=("微软雅黑", 11, "bold")).pack(anchor="w", padx=50)
        self.analysis_text = tk.Text(self.root, font=("微软雅黑", 11), width=80, height=7,
                                      state=tk.DISABLED, wrap=tk.WORD)
        self.analysis_text.pack(pady=8, padx=50)

        # 7. 进度与统计
        stat_frame = tk.Frame(self.root)
        stat_frame.pack(pady=5)
        self.progress_label = tk.Label(stat_frame, text="", font=("微软雅黑", 10))
        self.progress_label.grid(row=0, column=0, padx=20)
        self.stat_label = tk.Label(stat_frame, text="", font=("微软雅黑", 10), fg="green")
        self.stat_label.grid(row=0, column=1, padx=20)

    def load_question(self):
        if self.current_question_idx < len(self.question_list):
            q = self.question_list[self.current_question_idx]
            self.module_label.config(text=f"[{q.get('module', '')}]")
            self.question_label.config(text=f"第{q['id']}题：{q['question']}")
            self.answer_entry.delete(0, tk.END)
            self.answer_entry.config(state=tk.NORMAL)
            self.analysis_text.config(state=tk.NORMAL)
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.config(state=tk.DISABLED)
            self.submit_btn.config(state=tk.NORMAL)
            self.next_btn.config(state=tk.DISABLED)
            self.progress_label.config(
                text=f"进度：{self.current_question_idx + 1}/{len(self.question_list)}")
            self.update_stat()
            self.answer_entry.focus_set()
        else:
            total = len(self.question_list)
            wrong = len(self.wrong_questions)
            self.module_label.config(text="")
            self.question_label.config(
                text=f"所有 {total} 道题目已完成！正确 {self.correct_count} 题，错误 {wrong} 题。\n可查看错题本巩固考点。")
            self.answer_entry.config(state=tk.DISABLED)
            self.submit_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)

    def update_stat(self):
        answered = self.current_question_idx
        if answered > 0:
            rate = self.correct_count / answered * 100
            self.stat_label.config(text=f"正确率：{rate:.0f}% ({self.correct_count}/{answered})")
        else:
            self.stat_label.config(text="")

    def match_answer(self, user_answer, correct_answer):
        """支持 / 分隔的多答案匹配，用户输入任一均算正确"""
        user = user_answer.strip().lower().replace(" ", "")
        candidates = [a.strip().lower().replace(" ", "") for a in correct_answer.split("/")]
        # 完整答案也算对
        full = correct_answer.strip().lower().replace(" ", "").replace("/", "")
        return user in candidates or user == full or user == correct_answer.strip().lower().replace(" ", "")

    def check_answer(self):
        q = self.question_list[self.current_question_idx]
        user_answer = self.answer_entry.get().strip()
        correct_answer = q["answer"]

        if self.match_answer(user_answer, correct_answer):
            messagebox.showinfo("结果", f"回答正确！\n正确答案：{correct_answer}")
            self.correct_count += 1
        else:
            messagebox.showwarning("结果", f"回答错误！\n正确答案：{correct_answer}")
            if q not in self.wrong_questions:
                self.wrong_questions.append(q)

        # 记录进度：无论对错，只要做了就算完成
        if q["id"] not in self.completed_ids:
            self.completed_ids.append(q["id"])
            save_user_progress(self.completed_ids)

        self.analysis_text.config(state=tk.NORMAL)
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, q["analysis"])
        self.analysis_text.config(state=tk.DISABLED)

        self.submit_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL)
        self.next_btn.focus_set()

    def on_enter_key(self):
        if self.submit_btn["state"] == tk.NORMAL or str(self.submit_btn["state"]) == "normal":
            self.check_answer()
        elif self.next_btn["state"] == tk.NORMAL or str(self.next_btn["state"]) == "normal":
            self.next_question()

    def next_question(self):
        self.current_question_idx += 1
        self.load_question()

    def import_md_file(self):
        """选择 Markdown 文件并导入题目到题库"""
        file_path = filedialog.askopenfilename(
            title="选择 Markdown 题库文件",
            filetypes=[("Markdown 文件", "*.md"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                md_content = f.read()
        except Exception as e:
            messagebox.showerror("读取失败", f"无法读取文件：\n{e}")
            return

        try:
            new_ch_info, new_questions = parse_md_questions(md_content)
        except (ValueError, json.JSONDecodeError) as e:
            messagebox.showerror("解析失败", f"Markdown 文件解析错误：\n{e}")
            return

        self.handle_import(new_ch_info, new_questions)

    def import_json_file(self):
        """选择 JSON 文件并导入题目到题库"""
        file_path = filedialog.askopenfilename(
            title="选择 JSON 题库文件",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    new_questions = data
                    new_ch_info = None
                elif isinstance(data, dict):
                    new_questions = data.get("question_bank", [])
                    new_ch_info = data.get("chapter_info")
                else:
                    raise ValueError("JSON 格式不正确，应为数组或包含 question_bank 的对象")
        except Exception as e:
            messagebox.showerror("导入失败", f"无法解析 JSON 文件：\n{e}")
            return

        if not new_questions:
            messagebox.showwarning("警告", "JSON 文件中未找到有效的题目数据")
            return

        self.handle_import(new_ch_info, new_questions)

    def handle_import(self, new_ch_info, new_questions):
        """统一处理导入逻辑"""
        choice = messagebox.askyesnocancel(
            "导入方式",
            f"解析到 {len(new_questions)} 道题目。\n\n"
            f"点击 [是] = 追加到现有题库\n"
            f"点击 [否] = 替换现有题库\n"
            f"点击 [取消] = 取消导入"
        )
        if choice is None:
            return

        global chapter_info, question_bank

        if choice:  # 追加
            existing_ids = {q["id"] for q in self.all_questions if "id" in q}
            max_id = max(existing_ids) if existing_ids else 0
            for q in new_questions:
                if "id" not in q or q["id"] in existing_ids:
                    max_id += 1
                    q["id"] = max_id
                existing_ids.add(q["id"])
            self.all_questions.extend(new_questions)
            if new_ch_info:
                chapter_info.update(new_ch_info)
        else:  # 替换
            if new_ch_info:
                chapter_info = new_ch_info
            self.all_questions = new_questions
            # 确保有 id
            for i, q in enumerate(self.all_questions):
                if "id" not in q:
                    q["id"] = i + 1

        # 更新全局变量
        question_bank = self.all_questions
        
        # 保存到 JSON
        save_question_bank(chapter_info, question_bank)

        # 重置刷题状态并应用记忆过滤
        self.question_list = [q for q in self.all_questions if q.get("id") not in self.completed_ids]
        self.current_question_idx = 0
        self.wrong_questions.clear()
        self.correct_count = 0
        self.answer_entry.config(state=tk.NORMAL)

        # 更新标题
        self.root.title(f"高项备考填空刷题 - {chapter_info['chapter_name']}")

        self.load_question()
        messagebox.showinfo("导入成功", f"题库已更新，当前剩余可练题目 {len(self.question_list)} 道。")

    def reset_user_progress(self):
        """重置用户进度"""
        if not messagebox.askyesno("确认重置", "确定要清除所有刷题记录吗？这会让所有题目重新出现。"):
            return
        
        self.completed_ids = []
        save_user_progress(self.completed_ids)
        
        # 重新应用过滤（实际上就是显示全部）
        self.question_list = self.all_questions.copy()
        self.current_question_idx = 0
        self.wrong_questions.clear()
        self.correct_count = 0
        
        self.load_question()
        messagebox.showinfo("重置成功", "进度已清除，可以重新开始刷题了！")

    def show_wrong_questions(self):
        wrong_window = tk.Toplevel(self.root)
        wrong_window.title(f"错题本 - {chapter_info['chapter_name']}")
        wrong_window.geometry("820x550")

        tk.Label(wrong_window, text=f"错题本（共{len(self.wrong_questions)}道）",
                 font=("微软雅黑", 14, "bold")).pack(pady=10)

        container = tk.Frame(wrong_window)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        scrollbar = ttk.Scrollbar(container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        wrong_text = tk.Text(container, font=("微软雅黑", 11), wrap=tk.WORD,
                             yscrollcommand=scrollbar.set)
        wrong_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=wrong_text.yview)

        if not self.wrong_questions:
            wrong_text.insert(tk.END, "暂无错题，继续保持！")
        else:
            for idx, q in enumerate(self.wrong_questions, 1):
                wrong_text.insert(tk.END,
                    f"【错题{idx}】[{q.get('module', '')}]\n"
                    f"题目：{q['question']}\n"
                    f"正确答案：{q['answer']}\n"
                    f"解析：{q['analysis']}\n\n"
                    f"{'-' * 60}\n\n")
        wrong_text.config(state=tk.DISABLED)

# ===================== 运行软件 =====================
if __name__ == "__main__":
    root = tk.Tk()
    app = GaoxiangExamApp(root)
    root.mainloop()
