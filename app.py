from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'kt3m_bi_mat_xuong_nguyen_minh_2026'

DB_FILE = 'quan_ly_xuong.db'

def ket_noi_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def khoi_tao_database():
    conn = ket_noi_db()
    cursor = conn.cursor()
    
    # 1. Bảng Tài khoản nhân viên
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS TaiKhoan (
            ten_dang_nhap TEXT PRIMARY KEY,
            mat_khau TEXT NOT NULL,
            ten_nguoi_dung TEXT NOT NULL,
            quyen TEXT NOT NULL,           
            luong_theo_gio REAL DEFAULT 0  
        )
    ''')
    
    # 2. Bảng Danh mục Vật tư tổng kho
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS VatTu (
            ma_vt TEXT PRIMARY KEY,
            ten_vt TEXT NOT NULL,
            dvt TEXT,
            sl_ton REAL DEFAULT 0,
            ton_toi_thieu REAL DEFAULT 5,
            don_gia_nhap REAL DEFAULT 0,    
            ma_barcode TEXT UNIQUE
        )
    ''')
    
    # 3. Bảng Quản lý Công việc / Công trình
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS CongViec (
            ma_cv TEXT PRIMARY KEY,
            ten_cv TEXT NOT NULL,           
            ngay_bat_dau TEXT,
            ngay_ket_thuc TEXT,
            tong_thu_nhap REAL DEFAULT 0,  
            trang_thai TEXT DEFAULT 'ĐANG CHẠY' 
        )
    ''')

    # 4. Bảng Chấm công Hệ số Ngày công thực tế
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ChamCong (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ten_dang_nhap TEXT,
            ngay TEXT,
            gio_vao TEXT,                  
            gio_ra TEXT,
            hinh_thuc TEXT,                
            so_gio_lam REAL DEFAULT 0,     
            ma_cv TEXT,                    
            FOREIGN KEY(ten_dang_nhap) REFERENCES TaiKhoan(ten_dang_nhap),
            FOREIGN KEY(ma_cv) REFERENCES CongViec(ma_cv)
        )
    ''')

    # 5. Bảng Vật tư tiêu hao bốc tách cho từng Công việc
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS VatTuCongViec (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_cv TEXT,
            ma_vt TEXT,
            so_luong_dung REAL DEFAULT 0,
            FOREIGN KEY(ma_cv) REFERENCES CongViec(ma_cv),
            FOREIGN KEY(ma_vt) REFERENCES VatTu(ma_vt)
        )
    ''')

    # Tạo mặc định tài khoản admin tối cao
    cursor.execute("SELECT * FROM TaiKhoan WHERE ten_dang_nhap = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO TaiKhoan VALUES ('admin', '123456', 'Sếp Nguyễn Khắc Minh', 'ADMIN', 0)")
        
        # Thêm vật tư mẫu ban đầu
        cursor.execute("INSERT OR IGNORE INTO VatTu VALUES ('GOMDF_17_C', 'Gỗ MDF chống ẩm 17mm phủ Melamine', 'Tấm', 120, 5, 340000, '8931112223334')")
        cursor.execute("INSERT OR IGNORE INTO VatTu VALUES ('NHUARONG_15', 'Tấm nhựa rỗng cao cấp 15mm', 'Tấm', 80, 5, 220000, '8934445556667')")
        cursor.execute("INSERT OR IGNORE INTO VatTu VALUES ('BANLE_INOX', 'Bản lề giảm chấn Inox 304', 'Cái', 500, 20, 15000, '8937778889991')")
        
    conn.commit()
    conn.close()

# ĐIỀU HƯỚNG GIAO DIỆN
@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = ket_noi_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TaiKhoan WHERE ten_dang_nhap = ? AND mat_khau = ?", (username, password))
        account = cursor.fetchone()
        conn.close()
        
        if account:
            session['user'] = {
                'username': account['ten_dang_nhap'], 
                'name': account['ten_nguoi_dung'], 
                'role': account['quyen']
            }
            return redirect(url_for('index'))
        else:
            return "<script>alert('Sai tài khoản hoặc mật khẩu!'); window.location.href='/login';</script>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/kho')
def giao_dien_kho():
    if 'user' not in session or session['user']['role'] != 'ADMIN': 
        return "Từ chối quyền truy cập! Chỉ tài khoản ADMIN mới có thể vào tổng kho.", 403
    return render_template('kho.html', user=session['user'])

@app.route('/cong-viec')
def giao_dien_cong_viec():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('cong_viec.html', user=session['user'])

# CÁC API HỆ THỐNG
@app.route('/api/admin/danh-sach-tai-khoan')
def admin_danh_sach_tai_khoan():
    if 'user' not in session or session['user']['role'] != 'ADMIN': return jsonify({'status': 'error'}), 403
    conn = ket_noi_db()
    cursor = conn.cursor()
    cursor.execute("SELECT ten_dang_nhap, ten_nguoi_dung, quyen, luong_theo_gio FROM TaiKhoan")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# API TẠO TÀI KHOẢN (Đồng bộ chuẩn biến với Frontend)
@app.route('/api/admin/tao-tai-khoan', methods=['POST'])
def admin_tao_tai_khoan():
    if 'user' not in session or session['user']['role'] != 'ADMIN':
        return jsonify({'status': 'error', 'message': 'Từ chối quyền truy cập!'}), 403
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    fullname = data.get('fullname')
    role = data.get('role', 'THO')
    luong_gio = float(data.get('luong_theo_gio', 0) if data.get('luong_theo_gio') else 0)
    
    if not username or not password or not fullname:
        return jsonify({'status': 'error', 'message': 'Vui lòng nhập đầy đủ các trường thông tin bắt buộc!'})
        
    conn = ket_noi_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO TaiKhoan VALUES (?, ?, ?, ?, ?)", (username, password, fullname, role, luong_gio))
        conn.commit()
        return jsonify({'status': 'success', 'message': f'Hệ thống đã kích hoạt tài khoản thợ: {fullname}'})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Tên tài khoản đăng nhập này đã tồn tại!'})
    finally:
        conn.close()

@app.route('/api/cong-viec/danh-sach')
def danh_sach_cong_viec():
    if 'user' not in session: return jsonify([]), 401
    conn = ket_noi_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM CongViec ORDER BY ngay_bat_dau DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# API THÊM CÔNG TRÌNH MỚI (Đồng bộ chuẩn biến với Frontend)
@app.route('/api/admin/them-cong-viec', methods=['POST'])
def admin_them_cong_viec():
    if 'user' not in session or session['user']['role'] != 'ADMIN': return jsonify({'status': 'error'}), 403
    data = request.json
    ma_cv = data.get('ma_cv')
    ten_cv = data.get('ten_cv')
    ngay_bd = data.get('ngay_bat_dau')
    ngay_kt = data.get('ngay_ket_thuc')
    tong_thu = float(data.get('tong_thu_nhap', 0) if data.get('tong_thu_nhap') else 0)
    
    if not ma_cv or not ten_cv:
        return jsonify({'status': 'error', 'message': 'Mã và Tên dự án công trình không được bỏ trống!'})
        
    conn = ket_noi_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO CongViec VALUES (?, ?, ?, ?, ?, 'ĐANG CHẠY')", (ma_cv, ten_cv, ngay_bd, ngay_kt, tong_thu))
        conn.commit()
        return jsonify({'status': 'success', 'message': f'Đã thêm công trình thành công: {ten_cv}'})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Mã công trình/đơn hàng này đã tồn tại!'})
    finally:
        conn.close()

# API CHẤM CÔNG THEO NGÀY CÔNG 1 HOẶC 1/2 NGÀY
@app.route('/api/tho/cham-cong', methods=['POST'])
def tho_cham_cong():
    if 'user' not in session: return jsonify({'status': 'error', 'message': 'Chưa xác thực đăng nhập!'}), 401
    data = request.json
    username = session['user']['username']
    ma_cv = data.get('ma_cv')
    he_so_cong = float(data.get('he_so_cong', 1.0))
    
    ngay_hien_tai = datetime.now().strftime('%Y-%m-%d')
    gio_hien_tai = datetime.now().strftime('%H:%M:%S')
    
    if not ma_cv:
        return jsonify({'status': 'error', 'message': 'Vui lòng chọn công trình trước!'})
        
    conn = ket_noi_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM ChamCong WHERE ten_dang_nhap = ? AND ngay = ? AND ma_cv = ?", (username, ngay_hien_tai, ma_cv))
    if cursor.fetchone():
        conn.close()
        return jsonify({'status': 'warning', 'message': 'Hôm nay bạn đã chấm công cho công trình này rồi!'})
    
    so_gio_quy_doi = he_so_cong * 8.0
    chuoi_hinh_thuc = f"Chấm {he_so_cong} công"
    
    cursor.execute('''
        INSERT INTO ChamCong (ten_dang_nhap, ngay, gio_vao, gio_ra, hinh_thuc, so_gio_lam, ma_cv) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (username, ngay_hien_tai, gio_hien_tai, gio_hien_tai, chuoi_hinh_thuc, so_gio_quy_doi, ma_cv))
    
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': f'Ghi nhận thành công {he_so_cong} ngày công!'})

@app.route('/api/kho/danh-sach')
def danh_sach_kho():
    conn = ket_noi_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM VatTu")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/kho/them-san-pham', methods=['POST'])
def admin_them_san_pham_kho():
    if 'user' not in session or session['user']['role'] != 'ADMIN': return jsonify({'status': 'error'}), 403
    data = request.json
    ma_vt = data.get('ma_vt')
    ten_vt = data.get('ten_vt')
    dvt = data.get('dvt')
    sl_ton = float(data.get('sl_ton', 0))
    gia_nhap = float(data.get('don_gia_nhap', 0))
    barcode = data.get('ma_barcode')
    
    conn = ket_noi_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO VatTu VALUES (?, ?, ?, ?, 5, ?, ?)", (ma_vt, ten_vt, dvt, sl_ton, gia_nhap, barcode))
        conn.commit()
        return jsonify({'status': 'success', 'message': f'Đã thêm vật tư vào kho.'})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Mã vật tư hoặc Barcode bị trùng!'})
    finally:
        conn.close()

@app.route('/api/admin/add-vat-tu-cong-viec', methods=['POST'])
def admin_add_vattu_cv():
    if 'user' not in session or session['user']['role'] != 'ADMIN': return jsonify({'status': 'error'}), 403
    data = request.json
    ma_cv = data.get('ma_cv')
    ma_vt = data.get('ma_vt')
    sl_dung = float(data.get('so_luong_dung', 0))
    
    conn = ket_noi_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT sl_ton FROM VatTu WHERE ma_vt = ?", (ma_vt,))
    vt = cursor.fetchone()
    if not vt or vt['sl_ton'] < sl_dung:
        conn.close()
        return jsonify({'status': 'error', 'message': f'Vật tư [{ma_vt}] không đủ hàng tồn kho!'})
        
    cursor.execute("UPDATE VatTu SET sl_ton = sl_ton - ? WHERE ma_vt = ?", (sl_dung, ma_vt))
    cursor.execute("INSERT INTO VatTuCongViec (ma_cv, ma_vt, so_luong_dung) VALUES (?, ?, ?)", (ma_cv, ma_vt, sl_dung))
    
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Xuất kho vật tư thành công!'})

@app.route('/api/admin/bao-cao-loi-nhuan/<ma_cv>')
def admin_bao_cao_loi_nhuan(ma_cv):
    if 'user' not in session or session['user']['role'] != 'ADMIN': return jsonify({'status': 'error'}), 403
    
    conn = ket_noi_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM CongViec WHERE ma_cv = ?", (ma_cv,))
    cv = cursor.fetchone()
    if not cv:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Mã công trình không hợp lệ!'})
        
    tong_thu_hop_dong = cv['tong_thu_nhap']
    
    cursor.execute('''
        SELECT SUM(VTCV.so_luong_dung * VT.don_gia_nhap) as cp_vat_tu
        FROM VatTuCongViec VTCV
        JOIN VatTu VT ON VTCV.ma_vt = VT.ma_vt
        WHERE VTCV.ma_cv = ?
    ''', (ma_cv,))
    row_vt = cursor.fetchone()
    chi_phi_vattu = row_vt['cp_vat_tu'] if row_vt['cp_vat_tu'] else 0
    
    cursor.execute('''
        SELECT SUM(CC.so_gio_lam * TK.luong_theo_gio) as cp_nhan_cong, SUM(CC.so_gio_lam) as tong_gio_lam
        FROM ChamCong CC
        JOIN TaiKhoan TK ON CC.ten_dang_nhap = TK.ten_dang_nhap
        WHERE CC.ma_cv = ?
    ''', (ma_cv,))
    row_cc = cursor.fetchone()
    chi_phi_nhan_cong = row_cc['cp_nhan_cong'] if row_cc['cp_nhan_cong'] else 0
    tong_ngay_cong_quy_doi = round((row_cc['tong_gio_lam'] / 8.0), 1) if row_cc['tong_gio_lam'] else 0
    
    loi_nhuan_thuan = tong_thu_hop_dong - chi_phi_vattu - chi_phi_nhan_cong
    
    conn.close()
    return jsonify({
        'ma_cv': cv['ma_cv'],
        'ten_cv': cv['ten_cv'],
        'ngay_bat_dau': cv['ngay_bat_dau'],
        'ngay_ket_thuc': cv['ngay_ket_thuc'],
        'tong_thu_nhap': tong_thu_hop_dong,
        'tong_cong_tho': tong_ngay_cong_quy_doi,
        'chi_phi_vattu': chi_phi_vattu,
        'chi_phi_nhan_cong': chi_phi_nhan_cong,
        'loi_nhuan_thuan': loi_nhuan_thuan
    })

if __name__ == '__main__':
    khoi_tao_database()
    app.run(host='0.0.0.0', port=5000, debug=True)