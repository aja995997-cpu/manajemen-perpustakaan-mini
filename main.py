import customtkinter as ctk
import sqlite3
from datetime import datetime
from tkinter import messagebox, Toplevel

class DatabaseManager:
    def __init__(self, db_name="perpustakaan_final.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()
        self._migrate_tables()

    def _create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS anggota (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama_lengkap TEXT NOT NULL,
                tahun_lahir INTEGER,
                jenis_kelamin TEXT,
                nomor_telepon TEXT,
                alamat TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS buku (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                judul TEXT NOT NULL,
                penulis TEXT NOT NULL,
                kategori TEXT,
                tahun INTEGER,
                status TEXT NOT NULL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS peminjaman (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buku_id INTEGER NOT NULL,
                anggota_id INTEGER NOT NULL,
                tanggal_pinjam DATE NOT NULL,
                tanggal_kembali DATE,
                catatan TEXT,
                FOREIGN KEY (buku_id) REFERENCES buku (id),
                FOREIGN KEY (anggota_id) REFERENCES anggota (id)
            )
        """)
        self.conn.commit()

    def _migrate_tables(self):
        try:
            self.cursor.execute("PRAGMA table_info(peminjaman)")
            columns = [info[1] for info in self.cursor.fetchall()]
            if "catatan" not in columns:
                self.cursor.execute("ALTER TABLE peminjaman ADD COLUMN catatan TEXT")
                self.conn.commit()
        except Exception:
            pass 

    def add_anggota(self, nama, tahun_lahir, jk, telepon, alamat):
        try:
            self.cursor.execute("INSERT INTO anggota (nama_lengkap, tahun_lahir, jenis_kelamin, nomor_telepon, alamat) VALUES (?, ?, ?, ?, ?)",
                                (nama, tahun_lahir, jk, telepon, alamat))
            self.conn.commit()
            return True
        except Exception: return False

    def update_anggota(self, id_anggota, nama, tahun, jk, telp, alamat):
        try:
            self.cursor.execute("""
                UPDATE anggota 
                SET nama_lengkap=?, tahun_lahir=?, jenis_kelamin=?, nomor_telepon=?, alamat=?
                WHERE id=?
            """, (nama, tahun, jk, telp, alamat, id_anggota))
            self.conn.commit()
            return True
        except Exception: return False

    def get_all_anggota(self):
        self.cursor.execute("SELECT * FROM anggota ORDER BY id DESC")
        return self.cursor.fetchall()
    
    def get_anggota_by_id(self, id):
        self.cursor.execute("SELECT * FROM anggota WHERE id=?", (id,))
        return self.cursor.fetchone()

    def get_anggota_for_pinjam(self):
        self.cursor.execute("SELECT id, nama_lengkap FROM anggota ORDER BY nama_lengkap ASC")
        return self.cursor.fetchall()
    
    def search_anggota_for_pinjam(self, term):
        term = f"%{term}%"
        self.cursor.execute("""
            SELECT id, nama_lengkap FROM anggota 
            WHERE nama_lengkap LIKE ? OR CAST(id AS TEXT) LIKE ?
            ORDER BY nama_lengkap ASC
        """, (term, term))
        return self.cursor.fetchall()

    def search_anggota(self, term, sort_by="ID (Terbaru)"):
        term_wildcard = f"%{term}%"
        sort_map = {
            "ID (Terbaru)": "id DESC",
            "Nama (A-Z)": "nama_lengkap ASC",
            "Tahun Lahir (Terlama)": "tahun_lahir ASC",
            "Tahun Lahir (Terbaru)": "tahun_lahir DESC"
        }
        order_clause = sort_map.get(sort_by, "id DESC")
        self.cursor.execute(f"""
            SELECT * FROM anggota 
            WHERE nama_lengkap LIKE ? OR nomor_telepon LIKE ? OR alamat LIKE ? OR CAST(id AS TEXT) LIKE ?
            ORDER BY {order_clause}
        """, (term_wildcard, term_wildcard, term_wildcard, term_wildcard))
        return self.cursor.fetchall()

    def pinjam_buku(self, buku_id, anggota_id):
        try:
            self.cursor.execute("UPDATE buku SET status = 'Dipinjam' WHERE id = ?", (buku_id,))
            tanggal_pinjam = datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("INSERT INTO peminjaman (buku_id, anggota_id, tanggal_pinjam) VALUES (?, ?, ?)",
                                (buku_id, anggota_id, tanggal_pinjam))
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            return False

    def get_peminjaman_by_buku_id(self, buku_id):
        try:
            self.cursor.execute("""
                SELECT T2.nama_lengkap, T1.tanggal_pinjam, T1.anggota_id
                FROM peminjaman T1
                JOIN anggota T2 ON T1.anggota_id = T2.id
                WHERE T1.buku_id = ? AND T1.tanggal_kembali IS NULL
                ORDER BY T1.tanggal_pinjam DESC LIMIT 1
            """, (buku_id,))
            return self.cursor.fetchone() 
        except Exception: return None

    def kembalikan_buku(self, buku_id, catatan=""):
        try:
            self.cursor.execute("UPDATE buku SET status = 'Tersedia' WHERE id = ?", (buku_id,))
            tanggal_kembali = datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("""
                SELECT id FROM peminjaman
                WHERE buku_id = ? AND tanggal_kembali IS NULL
                ORDER BY tanggal_pinjam DESC LIMIT 1
            """, (buku_id,))
            row = self.cursor.fetchone()
            if row:
                peminjaman_id = row[0]
                self.cursor.execute("UPDATE peminjaman SET tanggal_kembali = ?, catatan = ? WHERE id = ?", (tanggal_kembali, catatan, peminjaman_id))
                self.conn.commit()
                return True
            else:
                self.conn.commit()
                return False
        except Exception:
            self.conn.rollback()
            return False

    def add_buku(self, judul, penulis, kategori, tahun):
        try:
            self.cursor.execute("INSERT INTO buku (judul, penulis, kategori, tahun, status) VALUES (?, ?, ?, ?, ?)",
                                (judul, penulis, kategori, tahun, "Tersedia"))
            self.conn.commit()
            return True
        except Exception: return False

    def get_all_buku(self, sort_by="ID (Terbaru)"):
        sort_map = {
            "ID (Terbaru)": "id DESC",
            "ID (Terlama)": "id ASC",
            "Judul (A-Z)": "judul ASC",
            "Penulis (A-Z)": "penulis ASC",
            "Tahun (Terbaru)": "tahun DESC",
            "Tahun (Terlama)": "tahun ASC",
            "Kategori": "kategori ASC",
            "Status": "status ASC"
        }
        order_clause = sort_map.get(sort_by, "id DESC")
        self.cursor.execute(f"SELECT * FROM buku ORDER BY {order_clause}")
        return self.cursor.fetchall()
    
    def update_buku(self, buku_id, judul, penulis, kategori, tahun):
        try:
            self.cursor.execute("UPDATE buku SET judul=?, penulis=?, kategori=?, tahun=? WHERE id=?", 
                                (judul, penulis, kategori, tahun, buku_id))
            self.conn.commit()
            return True
        except Exception: return False

    def get_buku_by_id(self, buku_id):
        self.cursor.execute("SELECT * FROM buku WHERE id = ?", (buku_id,))
        return self.cursor.fetchone()

    def delete_buku(self, buku_id):
        try:
            self.cursor.execute("SELECT status FROM buku WHERE id = ?", (buku_id,))
            status = self.cursor.fetchone()
            if status and status[0] == 'Dipinjam': return "Dipinjam"
            
            self.cursor.execute("DELETE FROM peminjaman WHERE buku_id = ?", (buku_id,))
            self.cursor.execute("DELETE FROM buku WHERE id = ?", (buku_id,))
            self.conn.commit()
            return "Sukses"
        except Exception:
            self.conn.rollback()
            return "Gagal"

    def search_buku(self, term):
        term = f"%{term}%"
        self.cursor.execute("""
            SELECT * FROM buku 
            WHERE judul LIKE ? OR penulis LIKE ? OR kategori LIKE ?
            ORDER BY id DESC
        """, (term, term, term))
        return self.cursor.fetchall()

    def get_history(self, filter_type="Terbaru"):
        query = """
            SELECT p.id, b.judul, a.nama_lengkap, p.tanggal_pinjam, p.tanggal_kembali, p.catatan
            FROM peminjaman p
            JOIN buku b ON p.buku_id = b.id
            JOIN anggota a ON p.anggota_id = a.id
        """
        if filter_type == "Sedang Dipinjam": 
            query += " WHERE p.tanggal_kembali IS NULL ORDER BY p.tanggal_pinjam DESC"
        elif filter_type == "Sudah Kembali": 
            query += " WHERE p.tanggal_kembali IS NOT NULL ORDER BY p.tanggal_kembali DESC"
        elif filter_type == "Terlama": 
            query += " ORDER BY p.tanggal_pinjam ASC" 
        else: 
            query += " ORDER BY p.tanggal_pinjam DESC"
            
        self.cursor.execute(query)
        return self.cursor.fetchall()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.title("📚 Sistem Manajemen Perpustakaan Pro v8.5")
        self.geometry("1100x650") 
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1) 
        
        self.sidebar_frame = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        ctk.CTkLabel(self.sidebar_frame, text="Perpustakaan\nMini v8.5", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))
        
        self.btn_inactive = "gray30" 
        self.btn_active = "#1f6aa5" 

        self.buku_button = ctk.CTkButton(self.sidebar_frame, text="📚  Buku", height=40, fg_color=self.btn_inactive, anchor="w", command=lambda: self.select_frame("buku"))
        self.buku_button.pack(padx=10, pady=5, fill="x")
        
        self.anggota_button = ctk.CTkButton(self.sidebar_frame, text="👥  Anggota", height=40, fg_color=self.btn_inactive, anchor="w", command=lambda: self.select_frame("anggota"))
        self.anggota_button.pack(padx=10, pady=5, fill="x")

        self.history_button = ctk.CTkButton(self.sidebar_frame, text="📜  Riwayat", height=40, fg_color=self.btn_inactive, anchor="w", command=lambda: self.select_frame("history"))
        self.history_button.pack(padx=10, pady=5, fill="x")

        self.main_content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1) 

        self.select_frame("buku")
        
    def select_frame(self, name):
        self.buku_button.configure(fg_color=self.btn_inactive)
        self.anggota_button.configure(fg_color=self.btn_inactive)
        self.history_button.configure(fg_color=self.btn_inactive)

        for widget in self.main_content_frame.winfo_children(): widget.destroy()

        if name == "buku":
            self.buku_button.configure(fg_color=self.btn_active)
            self.create_buku_frame()
        elif name == "anggota":
            self.anggota_button.configure(fg_color=self.btn_active)
            self.create_anggota_frame()
        elif name == "history":
            self.history_button.configure(fg_color=self.btn_active)
            self.create_history_frame()

    def close_win(self, window):
        try:
            window.grab_release()
            window.destroy()
        except: pass

    def limit_text(self, text, max_chars=20):
        s = str(text)
        return s[:max_chars] + ".." if len(s) > max_chars else s

    def create_buku_frame(self):
        self.buku_frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.buku_frame.grid(row=0, column=0, sticky="nsew") 
        
        self.buku_frame.grid_columnconfigure(0, weight=1)
        self.buku_frame.grid_rowconfigure(1, weight=1) 

        ctrl_frame = ctk.CTkFrame(self.buku_frame)
        ctrl_frame.grid(row=0, column=0, padx=0, pady=(0, 10), sticky="ew")
        
        self.search_entry = ctk.CTkEntry(ctrl_frame, placeholder_text="Cari...", width=200)
        self.search_entry.pack(side="left", padx=10, pady=10)
        ctk.CTkButton(ctrl_frame, text="🔍", width=40, command=self.search_buku_ui).pack(side="left", padx=5)
        
        ctk.CTkLabel(ctrl_frame, text="Urutkan:").pack(side="left", padx=(15, 5))
        self.sort_var = ctk.StringVar(value="ID (Terbaru)")
        sort_opts = ["ID (Terbaru)", "ID (Terlama)", "Judul (A-Z)", "Penulis (A-Z)", "Tahun (Terbaru)", "Tahun (Terlama)", "Kategori", "Status"]
        ctk.CTkOptionMenu(ctrl_frame, values=sort_opts, variable=self.sort_var, command=self.load_buku_data, width=130).pack(side="left", padx=5)

        ctk.CTkButton(ctrl_frame, text="➕ Buku Baru", command=self.open_add_buku_window).pack(side="right", padx=10)

        self.buku_list_frame = ctk.CTkScrollableFrame(self.buku_frame, label_text="Daftar Buku")
        self.buku_list_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        
        self.load_buku_data()

    def load_buku_data(self, sort_option=None):
        if not hasattr(self, 'buku_list_frame') or self.buku_list_frame is None: return 
        
        current_sort = sort_option if sort_option else self.sort_var.get()
        data = self.db.get_all_buku(current_sort)
        self.render_rows(data) 

    def render_rows(self, data):
        for widget in self.buku_list_frame.winfo_children(): widget.destroy()

        if not data:
            ctk.CTkLabel(self.buku_list_frame, text="Tidak ada buku yang ditemukan.").pack(pady=10)
            return

        col_widths = [40, 200, 150, 100, 60, 100, 80, 80]
        col_names = ["ID", "Judul", "Penulis", "Kategori", "Tahun", "Status", "Aksi", "Edit"]

        header_frame = ctk.CTkFrame(self.buku_list_frame, fg_color="gray25", height=35)
        header_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        for i, name in enumerate(col_names):
            lbl = ctk.CTkLabel(header_frame, text=name, width=col_widths[i], 
                               text_color="white", font=ctk.CTkFont(weight="bold"))
            lbl.grid(row=0, column=i, padx=2, pady=5)

        for i, buku in enumerate(data):
            row_color = ("gray90", "gray20") if i % 2 == 0 else ("gray85", "gray17")
            row_frame = ctk.CTkFrame(self.buku_list_frame, fg_color=row_color, height=40)
            row_frame.pack(fill="x", padx=5, pady=2)
            
            values = [
                str(buku[0]), 
                self.limit_text(buku[1], 25), 
                self.limit_text(buku[2], 20), 
                self.limit_text(buku[3], 12), 
                str(buku[4]), 
                buku[5]
            ]

            for j, val in enumerate(values):
                lbl_color = "text_color"
                font_style = None
                text_col = None
                if j == 5:
                    text_col = "green" if val == "Tersedia" else "red"
                    font_style = ctk.CTkFont(weight="bold")

                lbl = ctk.CTkLabel(row_frame, text=val, width=col_widths[j], 
                                   anchor="center", text_color=text_col, font=font_style)
                lbl.grid(row=0, column=j, padx=2, pady=5)

            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent", width=col_widths[6], height=30)
            btn_frame.grid(row=0, column=6, padx=2)
            btn_frame.grid_propagate(False)

            if buku[5] == "Tersedia":
                ctk.CTkButton(btn_frame, text="Pinjam", command=lambda id=buku[0]: self.open_pinjam_buku_window(id), 
                              width=col_widths[6]-10, height=25).place(relx=0.5, rely=0.5, anchor="center")
            else:
                ctk.CTkButton(btn_frame, text="Kembali", command=lambda id=buku[0]: self.open_kembali_buku_window(id), 
                              width=col_widths[6]-10, height=25, fg_color="orange").place(relx=0.5, rely=0.5, anchor="center")
            
            opt_frame = ctk.CTkFrame(row_frame, fg_color="transparent", width=col_widths[7], height=30)
            opt_frame.grid(row=0, column=7, padx=2)
            opt_frame.grid_propagate(False)

            opt_var = ctk.StringVar(value="⚙️")
            ctk.CTkOptionMenu(opt_frame, values=["Edit Detail", "Hapus Buku"], 
                              command=lambda c, id=buku[0]: self.handle_buku_action(c, id), 
                              variable=opt_var, width=col_widths[7]-10, height=25).place(relx=0.5, rely=0.5, anchor="center")

    def search_buku_ui(self):
        results = self.db.search_buku(self.search_entry.get().strip())
        self.render_rows(results)

    def open_add_buku_window(self):
        self.add_window = ctk.CTkToplevel(self)
        self.add_window.title("Tambah Buku")
        self.add_window.geometry("350x450")
        self.add_window.grab_set() 

        ctk.CTkLabel(self.add_window, text="Form Buku Baru", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        def create_inp(lbl, ph):
            ctk.CTkLabel(self.add_window, text=lbl).pack(padx=20, pady=(5,0), anchor="w")
            e = ctk.CTkEntry(self.add_window, placeholder_text=ph)
            e.pack(padx=20, pady=(0,10), fill="x")
            return e

        self.e_jud = create_inp("Judul Buku:", "Laskar Pelangi")
        self.e_pen = create_inp("Penulis:", "Andrea Hirata")
        self.e_kat = create_inp("Kategori:", "Novel")
        self.e_thn = create_inp("Tahun:", "2005")

        ctk.CTkButton(self.add_window, text="Simpan", command=self.add_buku_submit).pack(pady=20)
        self.add_window.protocol("WM_DELETE_WINDOW", lambda: self.close_win(self.add_window))

    def add_buku_submit(self):
        vals = [self.e_jud.get(), self.e_pen.get(), self.e_kat.get(), self.e_thn.get()]
        if not all(vals): return messagebox.showerror("Error", "Isi semua data.")
        try:
            if self.db.add_buku(vals[0], vals[1], vals[2], int(vals[3])):
                self.load_buku_data()
                self.close_win(self.add_window)
        except: messagebox.showerror("Error", "Tahun harus angka.")

    def handle_buku_action(self, choice, buku_id):
        if choice == "Edit Detail": self.open_edit_buku_window(buku_id)
        elif choice == "Hapus Buku": 
            if messagebox.askyesno("Hapus", "Yakin hapus buku ini?"):
                res = self.db.delete_buku(buku_id)
                if res == "Sukses": self.load_buku_data(self.sort_var.get())
                else: messagebox.showerror("Gagal", res)

    def open_edit_buku_window(self, buku_id):
        b = self.db.get_buku_by_id(buku_id)
        win = ctk.CTkToplevel(self)
        win.title("Edit Buku")
        win.geometry("300x400")
        win.grab_set()
        
        ctk.CTkLabel(win, text="Edit Detail Buku", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        def mk_e(lbl, val):
            ctk.CTkLabel(win, text=lbl).pack(pady=(5,0))
            e = ctk.CTkEntry(win); e.insert(0, val); e.pack(padx=20, fill="x")
            return e
            
        e1, e2, e3, e4 = mk_e("Judul", b[1]), mk_e("Penulis", b[2]), mk_e("Kategori", b[3]), mk_e("Tahun", str(b[4]))
        
        def save():
            try:
                tahun_int = int(e4.get())
                if self.db.update_buku(buku_id, e1.get(), e2.get(), e3.get(), tahun_int):
                    self.load_buku_data()
                    self.close_win(win)
                    messagebox.showinfo("Sukses", "Data buku diperbarui.")
                else: messagebox.showerror("Error", "Gagal menyimpan.")
            except ValueError:
                messagebox.showerror("Error", "Tahun harus angka.")
        
        ctk.CTkButton(win, text="Update", command=save).pack(pady=20)
        win.protocol("WM_DELETE_WINDOW", lambda: self.close_win(win))

    def create_anggota_frame(self):
        self.anggota_frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.anggota_frame.grid(row=0, column=0, sticky="nsew")
        
        self.anggota_frame.grid_columnconfigure(0, weight=1)
        self.anggota_frame.grid_rowconfigure(1, weight=1) 

        ctrl = ctk.CTkFrame(self.anggota_frame)
        ctrl.grid(row=0, column=0, padx=0, pady=(0, 10), sticky="ew")
        
        self.anggota_search_entry = ctk.CTkEntry(ctrl, placeholder_text="Cari Anggota (Nama/Telp/Alamat)...", width=250)
        self.anggota_search_entry.pack(side="left", padx=10, pady=10)
        ctk.CTkButton(ctrl, text="🔍", width=40, command=self.search_anggota_ui).pack(side="left", padx=5)

        ctk.CTkLabel(ctrl, text="Urutkan:").pack(side="left", padx=(15, 5))
        self.anggota_sort_var = ctk.StringVar(value="ID (Terbaru)")
        sort_opts_ang = ["ID (Terbaru)", "Nama (A-Z)", "Tahun Lahir (Terlama)", "Tahun Lahir (Terbaru)"]
        ctk.CTkOptionMenu(ctrl, values=sort_opts_ang, variable=self.anggota_sort_var, command=lambda s: self.search_anggota_ui(sort_only=True), width=150).pack(side="left", padx=5)
        
        ctk.CTkButton(ctrl, text="➕ Anggota Baru", command=self.open_add_anggota_window).pack(side="right", padx=10)

        self.anggota_list_frame = ctk.CTkScrollableFrame(self.anggota_frame, label_text="List Anggota")
        self.anggota_list_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        
        self.search_anggota_ui() 

    def search_anggota_ui(self, sort_only=False):
        search_term = "" if sort_only else self.anggota_search_entry.get().strip()
        sort_option = self.anggota_sort_var.get()
        data = self.db.search_anggota(search_term, sort_option)
        self.load_anggota_data(data)

    def load_anggota_data(self, data):
        for w in self.anggota_list_frame.winfo_children(): w.destroy()
        if not data: return ctk.CTkLabel(self.anggota_list_frame, text="Tidak ada anggota yang ditemukan.").pack(pady=10)

        col_widths = [40, 180, 50, 70, 110, 180, 80]
        col_names = ["ID", "Nama", "JK", "Tahun", "Telp", "Alamat", "Aksi"]

        hf = ctk.CTkFrame(self.anggota_list_frame, fg_color="gray25")
        hf.pack(fill="x", padx=5, pady=(5,0))
        
        for i, c in enumerate(col_names): 
            ctk.CTkLabel(hf, text=c, width=col_widths[i], text_color="white", font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=2, pady=5)

        for i, row in enumerate(data):
            row_color = ("gray90", "gray20") if i % 2 == 0 else ("gray85", "gray17")
            rf = ctk.CTkFrame(self.anggota_list_frame, fg_color=row_color)
            rf.pack(fill="x", padx=5, pady=2)
            
            vals = [
                str(row[0]), 
                self.limit_text(row[1], 22), 
                row[3], 
                str(row[2]), 
                row[4], 
                self.limit_text(row[5], 22)
            ]

            for j, val in enumerate(vals):
                ctk.CTkLabel(rf, text=val, width=col_widths[j], anchor="center").grid(row=0, column=j, padx=2, pady=5)
            
            btn_frame = ctk.CTkFrame(rf, fg_color="transparent", width=col_widths[6], height=30)
            btn_frame.grid(row=0, column=6, padx=2)
            btn_frame.grid_propagate(False)
            
            ctk.CTkButton(btn_frame, text="Edit", width=col_widths[6]-10, height=25, 
                          command=lambda id=row[0]: self.open_edit_anggota_window(id)).place(relx=0.5, rely=0.5, anchor="center")

    def open_add_anggota_window(self):
        self.win_add_ang = ctk.CTkToplevel(self)
        self.win_add_ang.title("Anggota Baru")
        self.win_add_ang.geometry("350x450")
        self.win_add_ang.grab_set()
        
        def mk(lbl): 
            ctk.CTkLabel(self.win_add_ang, text=lbl).pack(anchor="w", padx=20, pady=(5,0))
            e = ctk.CTkEntry(self.win_add_ang); e.pack(fill="x", padx=20)
            return e
        self.ea1, self.ea2, self.ea3, self.ea4, self.ea5 = mk("Nama"), mk("Tahun Lahir"), mk("JK (P/L)"), mk("Telepon"), mk("Alamat")
        
        def save():
            try:
                tahun_int = int(self.ea2.get())
                if self.db.add_anggota(self.ea1.get(), tahun_int, self.ea3.get(), self.ea4.get(), self.ea5.get()):
                    self.search_anggota_ui() 
                    self.close_win(self.win_add_ang)
                else: messagebox.showerror("Error", "Gagal menyimpan.")
            except ValueError:
                messagebox.showerror("Error", "Tahun Lahir harus angka.")

        ctk.CTkButton(self.win_add_ang, text="Simpan", command=save).pack(pady=20)

    def open_edit_anggota_window(self, id_anggota):
        ang = self.db.get_anggota_by_id(id_anggota)
        if not ang: return messagebox.showerror("Error", "Data anggota tidak ditemukan.")

        win = ctk.CTkToplevel(self)
        win.title(f"Edit Anggota ID: {id_anggota}")
        win.geometry("350x450")
        win.grab_set()

        ctk.CTkLabel(win, text="Edit Data Anggota", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        def mk(lbl, val):
            ctk.CTkLabel(win, text=lbl).pack(anchor="w", padx=20, pady=(5,0))
            e = ctk.CTkEntry(win); e.insert(0, val); e.pack(fill="x", padx=20)
            return e

        e_nm = mk("Nama Lengkap", ang[1])
        e_th = mk("Tahun Lahir", str(ang[2]))
        e_jk = mk("Jenis Kelamin (P/L)", ang[3])
        e_tl = mk("No Telepon", ang[4])
        e_al = mk("Alamat", ang[5])

        def update():
            try:
                tahun_int = int(e_th.get())
                if self.db.update_anggota(id_anggota, e_nm.get(), tahun_int, e_jk.get(), e_tl.get(), e_al.get()):
                    self.search_anggota_ui() 
                    self.close_win(win)
                    messagebox.showinfo("Sukses", "Data anggota diperbarui.")
                else: messagebox.showerror("Gagal", "Error update database.")
            except ValueError:
                messagebox.showerror("Error", "Tahun Lahir harus berupa angka.")

        ctk.CTkButton(win, text="Simpan Perubahan", command=update).pack(pady=20)

    def create_history_frame(self):
        self.hist_frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.hist_frame.grid(row=0, column=0, sticky="nsew")
        
        self.hist_frame.grid_columnconfigure(0, weight=1)
        self.hist_frame.grid_rowconfigure(1, weight=1)

        ctrl = ctk.CTkFrame(self.hist_frame)
        ctrl.grid(row=0, column=0, padx=0, pady=(0, 10), sticky="ew")
        
        self.filt_var = ctk.StringVar(value="Terbaru")
        ctk.CTkOptionMenu(ctrl, values=["Terbaru", "Terlama", "Sedang Dipinjam", "Sudah Kembali"], variable=self.filt_var, command=self.load_history).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(ctrl, text="Refresh", command=lambda: self.load_history(self.filt_var.get()), width=80).pack(side="left")

        self.hist_list = ctk.CTkScrollableFrame(self.hist_frame, label_text="Log Transaksi")
        self.hist_list.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        
        self.load_history("Terbaru")

    def load_history(self, filter_type):
        for w in self.hist_list.winfo_children(): w.destroy()
        data = self.db.get_history(filter_type)
        if not data: return ctk.CTkLabel(self.hist_list, text="Kosong").pack(pady=10)

        col_widths = [40, 150, 150, 100, 100, 120, 100]
        col_names = ["ID", "Buku", "Peminjam", "Pinjam", "Kembali", "Catatan", "Status"]

        hf = ctk.CTkFrame(self.hist_list, fg_color="gray25")
        hf.pack(fill="x", padx=5, pady=(5,0))
        
        for i, c in enumerate(col_names): 
            ctk.CTkLabel(hf, text=c, width=col_widths[i], text_color="white", font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=2, pady=5)

        for i, r in enumerate(data):
            row_color = ("gray90", "gray20") if i % 2 == 0 else ("gray85", "gray17")
            rf = ctk.CTkFrame(self.hist_list, fg_color=row_color)
            rf.pack(fill="x", padx=5, pady=2)
            
            vals = [
                str(r[0]), 
                self.limit_text(r[1], 18), 
                self.limit_text(r[2], 18), 
                r[3], 
                r[4] if r[4] else "-", 
                self.limit_text(r[5], 15) if r[5] else "-"
            ]
            
            for j, v in enumerate(vals): 
                ctk.CTkLabel(rf, text=v, width=col_widths[j], anchor="center").grid(row=0, column=j, padx=2, pady=5)
            
            st_txt = "Kembali" if r[4] else "Dipinjam"
            st_col = "green" if r[4] else "orange"
            ctk.CTkLabel(rf, text=st_txt, width=col_widths[6], text_color=st_col, font=ctk.CTkFont(weight="bold")).grid(row=0, column=6, padx=2, pady=5)

    def open_pinjam_buku_window(self, buku_id):
        if not self.db.get_anggota_for_pinjam(): 
            return messagebox.showwarning("Info", "Daftarkan anggota dulu sebelum meminjam.")

        win = ctk.CTkToplevel(self)
        win.title("Pinjam Buku")
        win.geometry("350x350") 
        win.grab_set()

        ctk.CTkLabel(win, text="Cari Anggota (ID / Nama):", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        
        search_frame = ctk.CTkFrame(win)
        search_frame.pack(fill="x", padx=20)
        
        search_entry = ctk.CTkEntry(search_frame, placeholder_text="Ketik ID atau Nama...", width=200)
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        list_frame = ctk.CTkFrame(win, fg_color="transparent")
        list_frame.pack(fill="x", padx=20, pady=10)
        
        selected_anggota_id = None 
        
        selected_label_text = ctk.StringVar(value="-- Belum ada anggota terpilih --")
        ctk.CTkLabel(list_frame, textvariable=selected_label_text, 
                     font=ctk.CTkFont(weight="bold"), 
                     wraplength=300).pack(pady=5)
                     
        def load_search_results(event=None):
            nonlocal selected_anggota_id
            term = search_entry.get().strip()
            
            for w in list_frame.winfo_children(): w.destroy()
                 
            selected_anggota_id = None
            selected_label_text.set("-- Belum ada anggota terpilih --")
            ctk.CTkLabel(list_frame, textvariable=selected_label_text, font=ctk.CTkFont(weight="bold"), wraplength=300).pack(pady=5)
            
            if len(term) < 1:
                ctk.CTkLabel(list_frame, text="Ketik ID atau Nama.").pack()
                return

            results = self.db.search_anggota_for_pinjam(term)
            if not results:
                ctk.CTkLabel(list_frame, text="Tidak ditemukan.").pack()
                return

            options = [f"{r[0]} - {r[1]}" for r in results]
            var = ctk.StringVar(value=options[0])
            
            def select_anggota(choice):
                nonlocal selected_anggota_id
                try:
                    selected_anggota_id = int(choice.split(' - ')[0])
                    selected_label_text.set(f"✅ Dipilih: {choice}")
                except:
                    selected_anggota_id = None
                    selected_label_text.set("-- Gagal memilih --")

            menu = ctk.CTkOptionMenu(list_frame, values=options, variable=var, command=select_anggota)
            menu.pack(fill="x", pady=5)
            select_anggota(options[0])

        search_entry.bind("<KeyRelease>", load_search_results)
        load_search_results() 
        
        def submit_pinjam():
            if selected_anggota_id is None:
                return messagebox.showerror("Error", "Pilih anggota dari hasil pencarian terlebih dahulu.")
            
            if self.db.pinjam_buku(buku_id, selected_anggota_id):
                self.load_buku_data(self.sort_var.get())
                self.close_win(win)
                messagebox.showinfo("OK", "Buku berhasil dipinjam.")
            else:
                messagebox.showerror("Gagal", "Error saat menyimpan peminjaman.")

        ctk.CTkButton(win, text="Konfirmasi Peminjaman", command=submit_pinjam, fg_color="blue").pack(pady=20)
        win.protocol("WM_DELETE_WINDOW", lambda: self.close_win(win))
        
    def open_kembali_buku_window(self, buku_id):
        trx = self.db.get_peminjaman_by_buku_id(buku_id)
        win = ctk.CTkToplevel(self)
        win.title("Pengembalian Buku")
        win.geometry("350x350")
        win.grab_set()

        if trx:
            nama, tgl, _ = trx
            ctk.CTkLabel(win, text="Konfirmasi Pengembalian", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
            ctk.CTkLabel(win, text=f"Peminjam: {nama}").pack()
            ctk.CTkLabel(win, text=f"Sejak: {tgl}").pack()
            
            ctk.CTkLabel(win, text="Catatan Pengembalian (Opsional):", anchor="w").pack(fill="x", padx=20, pady=(20, 5))
            note_entry = ctk.CTkEntry(win, placeholder_text="Misal: Kondisi aman / Telat bayar denda")
            note_entry.pack(fill="x", padx=20)

            def sub():
                catatan = note_entry.get()
                if self.db.kembalikan_buku(buku_id, catatan):
                    self.load_buku_data(self.sort_var.get())
                    self.close_win(win)
                    messagebox.showinfo("Sukses", "Buku dikembalikan.")
                else: messagebox.showerror("Gagal", "Error saat menyimpan pengembalian.")

            ctk.CTkButton(win, text="Terima Buku & Simpan", command=sub, fg_color="green").pack(pady=20)
            
        else:
            ctk.CTkLabel(win, text="⚠️ Data peminjam aktif tidak ditemukan.", text_color="red").pack(pady=20, padx=10)
            ctk.CTkLabel(win, text="Kemungkinan buku sudah dikembalikan atau terjadi error sinkronisasi.").pack(pady=(0, 10))
            
            def force_reset():
                if messagebox.askyesno("Konfirmasi Reset", "Yakin ingin memaksa status buku menjadi Tersedia?"):
                    self.db.cursor.execute("UPDATE buku SET status='Tersedia' WHERE id=?", (buku_id,))
                    self.db.conn.commit()
                    self.load_buku_data(self.sort_var.get())
                    self.close_win(win)
                    messagebox.showinfo("Reset", "Status buku berhasil direset ke 'Tersedia'.")
                    
            ctk.CTkButton(win, text="Paksa Reset Status Buku", command=force_reset, fg_color="red").pack(pady=10)

        win.protocol("WM_DELETE_WINDOW", lambda: self.close_win(win))


if __name__ == "__main__":
    app = App()
    app.mainloop()
