import os
import sys
import queue
import sounddevice as sd
import vosk
import json
import threading
import tkinter as tk
from tkinter import font, ttk, messagebox
from deep_translator import GoogleTranslator
from collections import deque
import time
import requests

# --- CONFIGURATION ---
MODEL_SMALL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_MEDIUM_URL = "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22-lgraph.zip"
MODEL_LARGE_URL = "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"

BASE_MODELS_DIR = "models"
BUNDLED_MODEL_DIR = "bundled_model"
INFO_FILE = "model_info.txt"

audio_queue = queue.Queue()
translation_queue = queue.Queue()
gui_queue = queue.Queue()

def get_bundled_model_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, BUNDLED_MODEL_DIR)

def get_model_dir(model_type):
    return os.path.join(BASE_MODELS_DIR, model_type)

def is_model_installed(model_type):
    path = get_model_dir(model_type)
    if os.path.exists(path):
        if os.path.exists(os.path.join(path, "conf")): return True
        for d in os.listdir(path):
            if os.path.isdir(os.path.join(path, d)) and os.path.exists(os.path.join(path, d, "conf")):
                return True
    return False

# --- GUI: HELP & GUIDE ---
class HelpGUI:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("راهنما و سوالات متداول")
        self.window.geometry("600x500")
        
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # کاراکتر جادویی برای راست‌چین کردن اجباری
        self.RLE = '\u202B'

        # --- TAB 1: SETUP GUIDE ---
        frame_setup = ttk.Frame(notebook)
        notebook.add(frame_setup, text="آموزش تنظیم صدا")
        
        txt_setup = tk.Text(frame_setup, wrap='word', font=("Tahoma", 10), padx=10, pady=10)
        txt_setup.pack(fill='both', expand=True)
        
        setup_raw = """
راهنمای دریافت صدای سیستم (ویندوز)

برای اینکه برنامه بتواند صدای فیلم، بازی یا کلاس‌های آنلاین را بشنود و ترجمه کند، باید تنظیمات صدای ویندوز را کمی تغییر دهید.

روش ۱: استفاده از کابل مجازی (پیشنهادی - بهترین کیفیت)
۱. نرم‌افزار رایگان "VB-CABLE Driver" را دانلود و نصب کنید (سپس ویندوز را ریستارت کنید).
۲. در تنظیمات ویندوز (System > Sound)، بخش خروجی (Output) را روی "CABLE Input" قرار دهید.
   (با این کار صدای اسپیکر قطع می‌شود و به کابل می‌رود).
۳. حال در همین برنامه مترجم، گزینه "CABLE Output" را انتخاب کنید.

* نکته مهم: چگونه همزمان صدا را بشنویم؟
برای اینکه هم خودتان صدا را بشنوید و هم برنامه:
۱. در ویندوز "Control Panel" را باز کنید و به بخش "Sound" بروید.
۲. به تب "Recording" بروید.
۳. روی "CABLE Output" راست کلیک کرده و "Properties" را بزنید.
۴. در تب "Listen"، تیک گزینه "Listen to this device" را بزنید.
۵. از لیست پایین آن، اسپیکر اصلی خود را انتخاب کنید و OK را بزنید.

روش ۲: استفاده از Stereo Mix (بدون نصب برنامه)
۱. در Control Panel > Sound به تب "Recording" بروید.
۲. در فضای خالی راست کلیک کنید و "Show Disabled Devices" را بزنید.
۳. گزینه "Stereo Mix" ظاهر می‌شود. روی آن راست کلیک و Enable کنید.
۴. حالا در برنامه مترجم، گزینه "Stereo Mix" را انتخاب کنید.
        """
        # Apply RLE to every line
        setup_content = "\n".join([self.RLE + line for line in setup_raw.split('\n')])
        
        txt_setup.insert('1.0', setup_content)
        txt_setup.tag_configure("right", justify='right')
        txt_setup.tag_add("right", "1.0", "end")
        txt_setup.config(state='disabled')

        # --- TAB 2: FAQ ---
        frame_faq = ttk.Frame(notebook)
        notebook.add(frame_faq, text="سوالات متداول")
        
        txt_faq = tk.Text(frame_faq, wrap='word', font=("Tahoma", 10), padx=10, pady=10)
        txt_faq.pack(fill='both', expand=True)
        
        faq_raw = """
سوالات متداول (FAQ)

س: چرا هیچ متنی نمایش داده نمی‌شود؟
ج: احتمالاً میکروفون اشتباهی را انتخاب کرده‌اید (مثلاً \u200Eمیکروفون لپتاپ\u200E) که صدایی دریافت نمی‌کند. طبق راهنمای تب قبل، باید \u200EStereo Mix\u200E یا \u200ECable Output\u200E را تنظیم و انتخاب کنید.

س: صدای کامپیوتر من قطع شده است!
ج: اگر از روش \u200EVB-Cable\u200E استفاده می‌کنید، این طبیعی است چون صدا به کابل هدایت شده. برای شنیدن صدا، بخش "نکته مهم" در راهنمای تنظیم صدا را بخوانید.

س: چرا ترجمه فارسی با تاخیر می‌آید؟
ج: تشخیص صدای انگلیسی به صورت آفلاین و آنی انجام می‌شود، اما ترجمه به فارسی نیاز به اینترنت دارد و بسته به سرعت اینترنت شما ممکن است کمی تاخیر داشته باشد.

س: چگونه پنجره زیرنویس را جابجا کنم؟
ج: روی هر قسمت مشکی رنگ کادر کلیک کنید و نگه دارید، سپس موس را حرکت دهید.

س: چگونه سایز کادر را تغییر دهم؟
ج: در گوشه پایین-راست کادر، یک علامت \u200E⇲\u200E وجود دارد. آن را بگیرید و بکشید.

س: متن انگلیسی روی متن فارسی را می‌گیرد.
ج: روی کادر راست کلیک کنید و گزینه "\u200EShow English Text\u200E" را یکبار خاموش و روشن کنید تا چیدمان درست شود.
        """
        # Apply RLE to every line
        faq_content = "\n".join([self.RLE + line for line in faq_raw.split('\n')])

        txt_faq.insert('1.0', faq_content)
        txt_faq.tag_configure("right", justify='right')
        txt_faq.tag_add("right", "1.0", "end")
        txt_faq.config(state='disabled')

# --- GUI: MODEL SELECTION ---
class ModelSelectorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Voice Translator Setup")
        self.root.geometry("500x420")
        self.root.eval('tk::PlaceWindow . center')
        
        style = ttk.Style()
        style.configure('TButton', font=('Segoe UI', 10), padding=10)
        style.configure('TLabel', font=('Segoe UI', 11))

        tk.Label(self.root, text="Select Recognition Model", font=("Segoe UI", 14, "bold")).pack(pady=15)

        self.choice = None

        # 1. Small
        status_small = " (Ready)" if is_model_installed("small") else ""
        ttk.Button(self.root, text=f"Small Model (~50 MB){status_small}\n(Fastest, Low RAM, Lower Accuracy)", 
                   command=self.select_small).pack(fill='x', padx=50, pady=5)

        # 2. Medium
        status_med = " (Ready)" if is_model_installed("medium") else ""
        ttk.Button(self.root, text=f"Medium Model 'lgraph' (~128 MB){status_med}\n(Best Balance: Good Accuracy, Medium RAM)", 
                   command=self.select_medium).pack(fill='x', padx=50, pady=5)

        # 3. Large
        status_large = " (Ready)" if is_model_installed("large") else ""
        ttk.Button(self.root, text=f"Large Model (~1.8 GB){status_large}\n(Max Accuracy, High RAM Usage ~5GB)", 
                   command=self.select_large).pack(fill='x', padx=50, pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def select_small(self):
        self.choice = 'small'
        self.root.destroy()

    def select_medium(self):
        self.choice = 'medium'
        self.root.destroy()

    def select_large(self):
        self.choice = 'large'
        self.root.destroy()

    def on_close(self):
        sys.exit(0)

# --- GUI: DOWNLOAD PROGRESS ---
class DownloadGUI:
    def __init__(self, url, model_type):
        self.root = tk.Tk()
        self.root.title(f"Downloading {model_type.capitalize()} Model...")
        self.root.geometry("400x150")
        self.root.eval('tk::PlaceWindow . center')
        
        self.url = url
        self.model_type = model_type
        self.target_dir = get_model_dir(model_type)
        self.download_complete = False

        self.lbl_info = tk.Label(self.root, text="Initializing...", font=("Segoe UI", 10))
        self.lbl_info.pack(pady=15)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)

        self.lbl_size = tk.Label(self.root, text="0 MB / 0 MB", font=("Segoe UI", 8))
        self.lbl_size.pack(pady=5)

        threading.Thread(target=self.run_download, daemon=True).start()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        if not self.download_complete:
            if messagebox.askokcancel("Quit", "Cancel download?"):
                sys.exit(0)
        else:
            self.root.destroy()

    def run_download(self):
        try:
            # Create target directory
            os.makedirs(self.target_dir, exist_ok=True)
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            session = requests.Session()
            
            zip_path = "model_temp.zip"
            mode = 'wb'
            initial_pos = 0
            resume_header = headers.copy()

            if os.path.exists(zip_path):
                initial_pos = os.path.getsize(zip_path)
                if initial_pos > 0:
                    resume_header['Range'] = f'bytes={initial_pos}-'
                    mode = 'ab'

            # 1. Connect
            self.update_label("Connecting...")
            response = session.get(self.url, stream=True, timeout=20, headers=resume_header)
            
            total_size = int(response.headers.get('content-length', 0)) + initial_pos
            
            if response.status_code == 416: 
                total_size = initial_pos
            elif response.status_code == 200 and initial_pos > 0:
                initial_pos = 0
                mode = 'wb'
                total_size = int(response.headers.get('content-length', 0))

            downloaded = initial_pos

            # 2. Download
            self.update_label("Downloading...")
            with open(zip_path, mode) as file:
                for data in response.iter_content(chunk_size=1024*1024):
                    if data:
                        size = file.write(data)
                        downloaded += size
                        perc = (downloaded / total_size) * 100
                        self.root.after(0, self.update_progress, perc, downloaded, total_size)

            # 3. Extract
            self.update_label("Extracting... (Do not close)")
            import zipfile
            import shutil
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("temp_extract")
                extracted_root = zip_ref.namelist()[0].split('/')[0]
                source = os.path.join("temp_extract", extracted_root)
                if os.path.exists(self.target_dir):
                    shutil.rmtree(self.target_dir)
                os.rename(source, self.target_dir)
                shutil.rmtree("temp_extract")
            
            # Write Info File
            with open(os.path.join(self.target_dir, INFO_FILE), "w") as f:
                f.write(self.model_type)

            os.remove(zip_path)
            self.download_complete = True
            self.root.after(0, self.root.destroy)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, sys.exit)

    def update_progress(self, perc, current, total):
        self.progress['value'] = perc
        self.lbl_size.config(text=f"{current/(1024*1024):.1f} MB / {total/(1024*1024):.1f} MB")

    def update_label(self, text):
        self.root.after(0, lambda: self.lbl_info.config(text=text))

# --- GUI: AUDIO SELECTION ---
class AudioSelectorGUI:
    def __init__(self):
        self.device_id = None
        self.root = tk.Tk()
        self.root.title("Select Audio Source")
        self.root.geometry("500x450")
        self.root.eval('tk::PlaceWindow . center')
        
        tk.Label(self.root, text="Select Audio Source (Cable Output / Stereo Mix):", font=("Segoe UI", 10, "bold")).pack(pady=10)
        
        frame = tk.Frame(self.root)
        frame.pack(fill='both', expand=True, padx=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side='right', fill='y')
        
        self.listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Consolas", 9))
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.listbox.yview)

        self.devices = sd.query_devices()
        for i, dev in enumerate(self.devices):
            if dev['max_input_channels'] > 0:
                self.listbox.insert(tk.END, f"[{i}] {dev['name']}")

        # BUTTONS FRAME
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Start Translator", command=self.confirm).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Help & Setup Guide (راهنما)", command=self.show_help).pack(side='left', padx=5)
        
        self.root.mainloop()

    def confirm(self):
        selection = self.listbox.curselection()
        if selection:
            text = self.listbox.get(selection[0])
            self.device_id = int(text.split(']')[0].replace('[', ''))
            self.root.destroy()
        else:
            messagebox.showwarning("Warning", "Select a device.")

    def show_help(self):
        HelpGUI(self.root)

# --- MAIN APP ---
class SubtitleOverlay:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-Time Translator")
        self.root.geometry("800x200+100+700")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.8)
        self.root.configure(bg='black')

        self.show_english = tk.BooleanVar(value=True)
        self.opacity = tk.DoubleVar(value=0.8)
        self.en_font_size = tk.IntVar(value=10)
        self.fa_font_size = tk.IntVar(value=16)

        self.history_en = deque(maxlen=2)
        self.history_fa = deque(maxlen=2)
        self.current_en = ""

        self.update_fonts()
        self.container = tk.Frame(root, bg='black')
        self.container.pack(fill='both', expand=True, padx=10, pady=5)
        self.spacer = tk.Frame(self.container, bg='black')
        self.lbl_en = tk.Label(self.container, text="", font=self.font_en, fg='#aaaaaa', bg='black', 
                               justify="center", height=3, anchor='s', wraplength=780)
        self.lbl_fa = tk.Label(self.container, text="...Listening...", font=self.font_fa, fg='white', bg='black', 
                               justify="right", anchor='se', wraplength=780) 
        self.refresh_layout()

        self.grip = tk.Label(self.root, text="⇲", bg="#444444", fg="white", cursor="sizing", font=("Arial", 12))
        self.grip.place(relx=1.0, rely=1.0, x=-20, y=-20, width=20, height=20)
        self.grip.bind("<Button-1>", self.start_resize)
        self.grip.bind("<B1-Motion>", self.do_resize)
        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.do_move)
        
        self.create_context_menu()
        self.root.bind("<Button-3>", self.show_context_menu)
        self.lbl_en.bind("<Button-3>", self.show_context_menu)
        self.lbl_fa.bind("<Button-3>", self.show_context_menu)
        self.container.bind("<Button-3>", self.show_context_menu)

        self.update_gui_loop()

    def refresh_layout(self):
        self.lbl_en.pack_forget()
        self.lbl_fa.pack_forget()
        self.spacer.pack_forget()
        if self.show_english.get(): self.lbl_en.pack(side='top', fill='x')
        self.lbl_fa.pack(side='bottom', fill='both', expand=False, pady=(0, 10))
        self.spacer.pack(side='top', fill='both', expand=True)

    def update_fonts(self):
        self.font_en = font.Font(family="Segoe UI", size=self.en_font_size.get())
        self.font_fa = font.Font(family="Tahoma", size=self.fa_font_size.get(), weight="bold")
        if hasattr(self, 'lbl_en'):
            self.lbl_en.configure(font=self.font_en)
            self.lbl_fa.configure(font=self.font_fa)
    
    def update_wraplength(self, width):
        wrap = width - 40 
        self.lbl_en.config(wraplength=wrap)
        self.lbl_fa.config(wraplength=wrap)

    def update_display(self):
        full_en = "\n".join(list(self.history_en) + [self.current_en]).strip()
        full_fa = "\n".join(list(self.history_fa)).strip()
        if not full_fa and self.current_en: full_fa = "..."
        self.lbl_en.config(text=full_en)
        self.lbl_fa.config(text=full_fa)

    def update_gui_loop(self):
        try:
            while True:
                msg = gui_queue.get_nowait()
                if msg[0] == "partial_en": self.current_en = msg[1]
                elif msg[0] == "final_en":
                    if msg[1].strip(): 
                        self.history_en.append(msg[1])
                        self.current_en = ""
                elif msg[0] == "final_fa": self.history_fa.append(msg[1])
                self.update_display()
        except queue.Empty: pass
        self.root.after(20, self.update_gui_loop)

    def start_resize(self, event):
        self.start_x = event.x_root; self.start_y = event.y_root
        self.start_w = self.root.winfo_width(); self.start_h = self.root.winfo_height()
        return "break"
    def do_resize(self, event):
        dx = event.x_root - self.start_x; dy = event.y_root - self.start_y
        new_w = max(300, self.start_w + dx); new_h = max(100, self.start_h + dy)
        self.root.geometry(f"{new_w}x{new_h}+{self.root.winfo_x()}+{self.root.winfo_y()}")
        self.update_wraplength(new_w)
        return "break"
    def start_move(self, event):
        self.x = event.x; self.y = event.y
    def do_move(self, event):
        dx = event.x - self.x; dy = event.y - self.y
        self.root.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_x()+dx}+{self.root.winfo_y()+dy}")

    def create_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_checkbutton(label="Show English Text", onvalue=True, offvalue=False, variable=self.show_english, command=self.refresh_layout)
        self.size_menu_en = tk.Menu(self.menu, tearoff=0); self.menu.add_cascade(label="English Font Size", menu=self.size_menu_en)
        for s in [8,10,12,14,18]: 
            self.size_menu_en.add_radiobutton(label=str(s), variable=self.en_font_size, value=s, command=self.update_fonts)
            
        self.size_menu_fa = tk.Menu(self.menu, tearoff=0); self.menu.add_cascade(label="Persian Font Size", menu=self.size_menu_fa)
        for s in [12,14,16,20,24,28,32]: 
            self.size_menu_fa.add_radiobutton(label=str(s), variable=self.fa_font_size, value=s, command=self.update_fonts)
            
        self.menu.add_separator()
        
        self.opacity_menu = tk.Menu(self.menu, tearoff=0); self.menu.add_cascade(label="Opacity", menu=self.opacity_menu)
        for op in [0.2,0.4,0.6,0.8,1.0]: 
            self.opacity_menu.add_radiobutton(label=f"{int(op*100)}%", variable=self.opacity, value=op, command=lambda: self.root.attributes('-alpha', self.opacity.get()))
            
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self.root.destroy)

    def show_context_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

# --- WORKER THREADS ---
def vosk_thread(device_id, samplerate, model_path):
    try:
        final_model_path = model_path
        if not os.path.exists(os.path.join(model_path, "conf")):
            if os.path.exists(model_path):
                subdirs = [d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d))]
                for d in subdirs:
                    if os.path.exists(os.path.join(model_path, d, "conf")): final_model_path = os.path.join(model_path, d); break
        
        model = vosk.Model(final_model_path)
        rec = vosk.KaldiRecognizer(model, samplerate)
        with sd.RawInputStream(samplerate=samplerate, blocksize=4000, device=device_id, dtype='int16', channels=1, callback=lambda i,f,t,s: audio_queue.put(bytes(i))):
            while True:
                data = audio_queue.get()
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    if res.get("text"): 
                        gui_queue.put(("final_en", res["text"]))
                        translation_queue.put(res["text"])
                else:
                    part = json.loads(rec.PartialResult())
                    if part.get("partial"): gui_queue.put(("partial_en", part["partial"]))
    except Exception as e:
        gui_queue.put(("final_en", f"Error: {str(e)}"))

def translation_thread():
    translator = GoogleTranslator(source='en', target='fa')
    while True:
        try:
            txt = translation_queue.get()
            trans = translator.translate(txt)
            gui_queue.put(("final_fa", trans))
        except: time.sleep(1)

def main():
    selector = ModelSelectorGUI()
    if not selector.choice: return 
    
    selected_model_path = get_model_dir(selector.choice)

    if selector.choice == 'small':
        bundled = get_bundled_model_path()
        if os.path.exists(bundled):
            selected_model_path = bundled
        elif not is_model_installed('small'):
             DownloadGUI(MODEL_SMALL_URL, 'small')
            
    elif selector.choice == 'medium':
        if not is_model_installed('medium'):
            DownloadGUI(MODEL_MEDIUM_URL, 'medium')
        
    elif selector.choice == 'large':
        if not is_model_installed('large'):
            DownloadGUI(MODEL_LARGE_URL, 'large')

    if not os.path.exists(selected_model_path) and selector.choice != 'small': return

    audio_sel = AudioSelectorGUI()
    if audio_sel.device_id is None: return

    device_info = sd.query_devices(audio_sel.device_id, 'input')
    samplerate = int(device_info['default_samplerate'])
    
    t1 = threading.Thread(target=vosk_thread, args=(audio_sel.device_id, samplerate, selected_model_path), daemon=True)
    t1.start()
    t2 = threading.Thread(target=translation_thread, daemon=True)
    t2.start()

    root = tk.Tk()
    SubtitleOverlay(root)
    root.mainloop()

if __name__ == "__main__":
    main()
