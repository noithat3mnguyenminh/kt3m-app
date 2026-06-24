from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'noithatnguyenminh_key_bi_mat'
DB_FILE = 'quan_ly_xuong.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# HÀM KHỞI TẠO HỆ THỐNG MỚI ĐÉT - XÓA BẢN CŨ TẠO BẢN MỚI
def init_db():
    # Nếu sếp muốn xóa sạch dữ liệu cũ hoàn toàn, bỏ comment dòng dưới:
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Bảng hồ sơ nhân viên/thợ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nhan_vien (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            cong_viec TEXT,
            luong_co_ban REAL DEFAULT 0,
            ngay_chot_luong INTEGER DEFAULT 30,
            doanh_so REAL DEFAULT 0,
            ghi_chu TEXT,
            tong_cong REAL DEFAULT 0,
            luong_tich_luy REAL DEFAULT 0
        )
    ''')
    
    # 2. Bảng lịch sử chấm công chi tiết từng ngày
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lich_su_cong (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nhan_vien_id INTEGER,
            ngay_cham TEXT,
            he_so_cong REAL,
            cong_trinh_id INTEGER,
            FOREIGN KEY(nhan_vien_id) REFERENCES nhan_vien(id)
        )
    ''')
    
    # 3. Bảng danh sách công trình
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cong_trinh (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ten_ct TEXT NOT NULL,
            don_gia REAL DEFAULT 0,
            chi_phi_vat_tu REAL DEFAULT 0,
            chi_phi_nhan_cong REAL DEFAULT 0,
            loi_nhuan REAL DEFAULT 0
        )
    ''')
    
    # 4. Bảng kho vật tư sỉ của xưởng
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vat_tu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ten_vt TEXT NOT NULL UNIQUE,
            gia_nhap REAL DEFAULT 0,
            so_luong INTEGER DEFAULT 0
        )
    ''')
    
    # 5. Bảng liên kết vật tư tiêu thụ của từng công trình (để tính cơ chế hoàn kho)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ct_vat_tu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cong_trinh_id INTEGER,
            vat_tu_id INTEGER,
            so_luong_dung INTEGER,
            thanh_tien REAL,
            FOREIGN KEY(cong_trinh_id) REFERENCES cong_trinh(id),
            FOREIGN KEY(vat_tu_id) REFERENCES vat_tu(id)
        )
    ''')
    
    # 6. Bảng tài khoản đăng nhập phân quyền công nghệ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tai_khoan (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL, -- 'ADMIN' hoặc 'USER'
            nhan_vien_id INTEGER, -- Liên kết với bảng nhan_vien (nếu là thợ)
            FOREIGN KEY(nhan_vien_id) REFERENCES nhan_vien(id)
        )
    ''')
    
    # Tự động tạo tài khoản Admin tối cao ban đầu cho Sếp Minh nếu chưa có
    try:
        cursor.execute("INSERT INTO tai_khoan (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'ADMIN'))
    except sqlite3.IntegrityError: pass
    
    conn.commit()
    conn.close()

init_db()

# ==================== ĐIỀU HƯỚNG ROUTE & ĐĂNG NHẬP ====================
@app.route('/')
def index():
    if 'username' not in session: return render_template('index.html', page='login')
    return render_template('index.html', page='main', user={'name': session['username'], 'role': session['role'], 'id': session.get('nhan_vien_id')})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM tai_khoan WHERE username = ? AND password = ?", (data['username'], data['password'])).fetchone()
    conn.close()
    if user:
        session['username'] = user['username']
        session['role'] = user['role']
        session['nhan_vien_id'] = user['nhan_vien_id']
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Sai tài khoản hoặc mật khẩu sếp ơi!'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==================== TÍNH NĂNG 1: QUẢN LÝ CHẤM CÔNG VÀ THỢ ====================
@app.route('/api/admin/them-nhan-vien', methods=['POST'])
def them_nhan_vien():
    data = request.json
    conn = get_db_connection()
    conn.execute('''INSERT INTO nhan_vien (fullname, cong_viec, luong_co_ban, ngay_chot_luong, doanh_so, ghi_chu) 
                    VALUES (?, ?, ?, ?, ?, ?)''', 
                 (data['fullname'], data['cong_viec'], data['luong_co_ban'], data['ngay_chot_luong'], data['doanh_so'], data['ghi_chu']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Đã thêm hồ sơ nhân viên thành công!'})

@app.route('/api/admin/danh-sach-thong-ke', methods=['GET'])
def danh_sach_thong_ke():
    conn = get_db_connection()
    # Nếu là thợ, chỉ lấy đúng hồ sơ của thợ đó để bảo mật lương
    if session.get('role') == 'USER':
        rows = conn.execute("SELECT * FROM nhan_vien WHERE id = ?", (session.get('nhan_vien_id'),)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM nhan_vien").fetchall()
    
    result = []
    for r in rows:
        lich_su = conn.execute('''SELECT ngay_cham, he_so_cong, ten_ct FROM lich_su_cong 
                                  LEFT JOIN cong_trinh ON lich_su_cong.cong_trinh_id = cong_trinh.id 
                                  WHERE nhan_vien_id = ? ORDER BY ngay_cham DESC''', (r['id'],)).fetchall()
        ls_list = [{'ngay': l['ngay_cham'], 'he_so': l['he_so_cong'], 'cong_trinh': l['ten_ct'] or 'Việc xưởng'} for l in lich_su]
        
        result.append({
            'id': r['id'], 'fullname': r['fullname'], 'cong_viec': r['cong_viec'],
            'luong_co_ban': r['luong_co_ban'], 'ngay_chot_luong': r['ngay_chot_luong'],
            'doanh_so': r['doanh_so'], 'ghi_chu': r['ghi_chu'], 'tong_cong': r['tong_cong'],
            'luong_tich_luy': r['luong_tich_luy'], 'lich_su': ls_list
        })
    conn.close()
    return jsonify(result)

@app.route('/api/admin/cham-cong', methods=['POST'])
def admin_cham_cong():
    data = request.json
    conn = get_db_connection()
    nv = conn.execute("SELECT * FROM nhan_vien WHERE id = ?", (data['nhan_vien_id'],)).fetchone()
    if not nv: return jsonify({'status': 'error', 'message': 'Không tìm thấy nhân viên!'})
    
    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
    he_so = float(data['he_so_cong'])
    tien_cong_them = he_so * nv['luong_co_ban']
    
    # 1. Cập nhật tích lũy lương thợ
    conn.execute("UPDATE nhan_vien SET tong_cong = tong_cong + ?, luong_tich_luy = luong_tich_luy + ? WHERE id = ?", 
                 (he_so, tien_cong_them, nv['id']))
    # 2. Ghi nhật ký lịch sử chấm công
    conn.execute("INSERT INTO lich_su_cong (nhan_vien_id, ngay_cham, he_so_cong, cong_trinh_id) VALUES (?, ?, ?, ?)",
                 (nv['id'], ngay_hien_tai, he_so, data.get('cong_trinh_id')))
    
    # 3. TỰ ĐỘNG HÓA NHÂN CÔNG: Nếu chấm công chỉ định cho công trình, cộng dồn thẳng vào chi phí nhân công dự án
    if data.get('cong_trinh_id'):
        conn.execute('''UPDATE cong_trinh SET chi_phi_nhan_cong = chi_phi_nhan_cong + ?, 
                        loi_nhuan = don_gia - (chi_phi_vat_tu + chi_phi_nhan_cong + ?) WHERE id = ?''',
                     (tien_cong_them, tien_cong_them, data['cong_trinh_id']))
                     
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': f'Đã chấm {he_so} công và tự động tính hạch toán dự án!'})

@app.route('/api/admin/reset-thang', methods=['POST'])
def reset_thang():
    conn = get_db_connection()
    # Chốt sổ: đưa toàn bộ ngày công và doanh số tháng này về 0 để tính chu kỳ mới
    conn.execute("UPDATE nhan_vien SET tong_cong = 0, luong_tich_luy = 0, doanh_so = 0")
    conn.execute("DELETE FROM lich_su_cong") # Xóa nhật ký tháng cũ để tránh nặng máy
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Đã hoàn tất chốt lương và thiết lập chu kỳ tháng mới!'})

# ==================== TÍNH NĂNG 2: QUẢN LÝ CÔNG TRÌNH VÀ TRỪ KHO TỰ ĐỘNG ====================
@app.route('/api/admin/them-cong-trinh', methods=['POST'])
def api_them_cong_trinh():
    data = request.json
    conn = get_db_connection()
    
    # Tạo công trình trống trước
    cursor = conn.cursor()
    cursor.execute("INSERT INTO cong_trinh (ten_ct, don_gia, chi_phi_vat_tu, chi_phi_nhan_cong, loi_nhuan) VALUES (?, ?, 0, 0, ?)", 
                 (data['ten_ct'], data['don_gia'], data['don_gia']))
    ct_id = cursor.lastrowid
    
    # Duyệt qua danh sách vật tư sếp chọn để tính toán tiền và TRỪ KHO GỐC
    tong_tien_vt = 0
    for item in data.get('vat_tu_list', []):
        vt = conn.execute("SELECT * FROM vat_tu WHERE id = ?", (item['vat_tu_id'],)).fetchone()
        if vt:
            # KIỂM TRA CHẶN LỖI ÂM KHO
            if vt['so_luong'] < int(item['so_luong_dung']):
                conn.rollback()
                conn.close()
                return jsonify({'status': 'error', 'message': f"Vật tư [{vt['ten_vt']}] trong kho chỉ còn {vt['so_luong']} tấm, không đủ cấp phát!"})
            
            thanh_tien = int(item['so_luong_dung']) * vt['gia_nhap']
            tong_tien_vt += thanh_tien
            
            # Trừ kho gốc
            conn.execute("UPDATE vat_tu SET so_luong = so_luong - ? WHERE id = ?", (item['so_luong_dung'], vt['id']))
            # Ghi lại bảng tiêu thụ để chuẩn bị cho cơ chế hoàn kho
            conn.execute("INSERT INTO ct_vat_tu (cong_trinh_id, vat_tu_id, so_luong_dung, thanh_tien) VALUES (?, ?, ?, ?)",
                         (ct_id, vt['id'], item['so_luong_dung'], thanh_tien))
            
    # Cập nhật lại số tiền vật tư và tính lợi nhuận ròng thực tế cho công trình
    conn.execute("UPDATE cong_trinh SET chi_phi_vat_tu = ?, loi_nhuan = don_gia - ? WHERE id = ?", (tong_tien_vt, tong_tien_vt, ct_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Khởi tạo công trình và tự động khấu trừ kho thành công!'})

@app.route('/api/admin/danh-sach-cong-trinh', methods=['GET'])
def danh_sach_cong_trinh():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM cong_trinh").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/xoa-cong-trinh/<int:id>', methods=['DELETE'])
def xoa_cong_trinh(id):
    conn = get_db_connection()
    # CƠ CHẾ HOÀN KHO THÔNG MINH: Lấy lại vật tư đã tiêu thụ đem trả về kho gốc
    tieu_thu = conn.execute("SELECT * FROM ct_vat_tu WHERE cong_trinh_id = ?", (id,)).fetchall()
    for tt in tieu_thu:
        conn.execute("UPDATE vat_tu SET so_luong = so_luong + ? WHERE id = ?", (tt['so_luong_dung'], tt['vat_tu_id']))
    
    conn.execute("DELETE FROM ct_vat_tu WHERE cong_trinh_id = ?", (id,))
    conn.execute("DELETE FROM cong_trinh WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Đã xóa dự án và hoàn trả toàn bộ phôi vật tư về kho sỉ!'})

# ==================== TÍNH NĂNG 3: QUẢN LÝ KHO VẬT TƯ ====================
@app.route('/api/admin/them-vat-tu', methods=['POST'])
def api_them_vat_tu():
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO vat_tu (ten_vt, gia_nhap, so_luong) VALUES (?, ?, ?) ON CONFLICT(ten_vt) DO UPDATE SET so_luong = so_luong + excluded.so_luong, gia_nhap = excluded.gia_nhap", 
                     (data['ten_vt'], data['gia_nhap'], data['so_luong']))
        conn.commit()
        msg = "Đã nhập thêm hàng vào kho vật tư!"
    except Exception as e: msg = "Lỗi nhập kho!"
    conn.close()
    return jsonify({'status': 'success', 'message': msg})

@app.route('/api/admin/danh-sach-vat-tu', methods=['GET'])
def danh_sach_vat_tu():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM vat_tu").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ==================== TÍNH NĂNG 4: CẤP TÀI KHOẢN XEM LƯƠNG BẢO MẬT CHỐN XEM LÉN ====================
@app.route('/api/admin/tao-tai-khoan-tho', methods=['POST'])
def tao_tai_khoan_tho():
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO tai_khoan (username, password, role, nhan_vien_id) VALUES (?, ?, 'USER', ?)",
                     (data['username'], data['password'], data['nhan_vien_id']))
        conn.commit()
        res = {'status': 'success', 'message': 'Đã kích hoạt tài khoản mở khóa xem lương cá nhân cho thợ!'}
    except sqlite3.IntegrityError:
        res = {'status': 'error', 'message': 'Tên tài khoản này đã có người sử dụng rồi sếp!'}
    conn.close()
    return jsonify(res)

@app.route('/api/admin/danh-sach-nhan-vien-chua-co-tk', methods=['GET'])
def nv_chua_co_tk():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, fullname FROM nhan_vien WHERE id NOT IN (SELECT nhan_vien_id FROM tai_khoan WHERE nhan_vien_id IS NOT NULL)").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == '__main__':
    app.run(debug=True)
