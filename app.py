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

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Bảng hồ sơ nhân viên
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nhan_vien (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            cong_viec TEXT,
            luong_co_ban REAL DEFAULT 0,
            ngay_chot_luong INTEGER DEFAULT 30,
            doanh_so REAL DEFAULT 0,
            tien_ung REAL DEFAULT 0,
            ghi_chu TEXT,
            tong_cong REAL DEFAULT 0,
            luong_tich_luy REAL DEFAULT 0
        )
    ''')
    
    # 2. Bảng lịch sử chấm công (Cập nhật định dạng NGÀY CHUẨN YYYY-MM-DD để đổ lên lịch tháng)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lich_su_cong (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nhan_vien_id INTEGER,
            ngay_cham TEXT, -- Định dạng chuẩn: YYYY-MM-DD
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
    
    # 4. Bảng kho vật tư sỉ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vat_tu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ten_vt TEXT NOT NULL UNIQUE,
            gia_nhap REAL DEFAULT 0,
            so_luong INTEGER DEFAULT 0
        )
    ''')
    
    # 5. Bảng liên kết vật tư tiêu thụ
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
    
    # 6. Bảng tài khoản
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tai_khoan (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            nhan_vien_id INTEGER,
            FOREIGN KEY(nhan_vien_id) REFERENCES nhan_vien(id)
        )
    ''')
    
    try:
        cursor.execute("INSERT INTO tai_khoan (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'ADMIN'))
    except sqlite3.IntegrityError: pass
    
    conn.commit()
    conn.close()

init_db()

# ==================== ROUTE ĐIỀU HƯỚNG ====================
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

# ==================== TÍNH NĂNG CHẤM CÔNG & SỬA CÔNG NÂNG CAO ====================
@app.route('/api/admin/them-nhan-vien', methods=['POST'])
def them_nhan_vien():
    data = request.json
    conn = get_db_connection()
    conn.execute('''INSERT INTO nhan_vien (fullname, cong_viec, luong_co_ban, ngay_chot_luong, doanh_so, tien_ung, ghi_chu) 
                    VALUES (?, ?, ?, ?, ?, 0, ?)''', 
                 (data['fullname'], data['cong_viec'], data['luong_co_ban'], data['ngay_chot_luong'], data['doanh_so'], data['ghi_chu']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Đã thêm hồ sơ nhân viên thành công!'})

@app.route('/api/admin/danh-sach-thong-ke', methods=['GET'])
def danh_sach_thong_ke():
    conn = get_db_connection()
    if session.get('role') == 'USER':
        rows = conn.execute("SELECT * FROM nhan_vien WHERE id = ?", (session.get('nhan_vien_id'),)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM nhan_vien").fetchall()
    
    result = []
    for r in rows:
        # Lấy lịch sử công sắp xếp theo ngày
        lich_su = conn.execute('''SELECT lich_su_cong.id, ngay_cham, he_so_cong, ten_ct FROM lich_su_cong 
                                  LEFT JOIN cong_trinh ON lich_su_cong.cong_trinh_id = cong_trinh.id 
                                  WHERE nhan_vien_id = ? ORDER BY ngay_cham ASC''', (r['id'],)).fetchall()
        
        ls_list = [{'id': l['id'], 'ngay': l['ngay_cham'], 'he_so': l['he_so_cong'], 'cong_trinh': l['ten_ct'] or 'Việc xưởng'} for l in lich_su]
        
        result.append({
            'id': r['id'], 'fullname': r['fullname'], 'cong_viec': r['cong_viec'],
            'luong_co_ban': r['luong_co_ban'], 'ngay_chot_luong': r['ngay_chot_luong'],
            'doanh_so': r['doanh_so'], 'tien_ung': r['tien_ung'], 'ghi_chu': r['ghi_chu'], 
            'tong_cong': r['tong_cong'], 'luong_tich_luy': r['luong_tich_luy'], 'lich_su': ls_list
        })
    conn.close()
    return jsonify(result)

# LỆNH THAY ĐỔI / CHẤM CÔNG THEO NGÀY (NẾU TRÙNG NGÀY THÌ TỰ ĐỘNG CẬP NHẬT SỬA CÔNG)
@app.route('/api/admin/cham-cong', methods=['POST'])
def admin_cham_cong():
    data = request.json
    conn = get_db_connection()
    
    nv = conn.execute("SELECT * FROM nhan_vien WHERE id = ?", (data['nhan_vien_id'],)).fetchone()
    if not nv: return jsonify({'status': 'error', 'message': 'Không tìm thấy nhân viên!'})
    
    # Lấy ngày được chọn từ giao diện lịch (Định dạng YYYY-MM-DD)
    ngay_chon = data['ngay_cham'] 
    he_so_moi = float(data['he_so_cong'])
    
    # Kiểm tra xem ngày đó nhân viên này đã được chấm công chưa
    cong_cu = conn.execute("SELECT * FROM lich_su_cong WHERE nhan_vien_id = ? AND ngay_cham = ?", (nv['id'], ngay_chon)).fetchone()
    
    if cong_cu:
        # SẾP CHẤM ĐÈ / SỬA CÔNG: Trừ tiền cũ đi, cộng tiền mới vào hệ thống
        he_so_cu = cong_cu['he_so_cong']
        tien_cu = he_so_cu * nv['luong_co_ban']
        tien_moi = he_so_moi * nv['luong_co_ban']
        
        # 1. Hoàn trả/Cập nhật bảng nhân viên
        conn.execute('''UPDATE nhan_vien SET tong_cong = tong_cong - ? + ?, 
                        luong_tich_luy = luong_tich_luy - ? + ? WHERE id = ?''',
                     (he_so_cu, he_so_moi, tien_cu, tien_moi, nv['id']))
        
        # 2. Cập nhật hệ số công mới vào ngày chấm đó
        conn.execute("UPDATE lich_su_cong SET he_so_cong = ?, cong_trinh_id = ? WHERE id = ?", 
                     (he_so_moi, data.get('cong_trinh_id'), cong_cu['id']))
        msg = f"Đã sửa công ngày {ngay_chon} thành {he_so_moi} công!"
    else:
        # CHẤM CÔNG MỚI TINH
        tien_them = he_so_moi * nv['luong_co_ban']
        conn.execute("UPDATE nhan_vien SET tong_cong = tong_cong + ?, luong_tich_luy = luong_tich_luy + ? WHERE id = ?", 
                     (he_so_moi, tien_them, nv['id']))
        conn.execute("INSERT INTO lich_su_cong (nhan_vien_id, ngay_cham, he_so_cong, cong_trinh_id) VALUES (?, ?, ?, ?)",
                     (nv['id'], ngay_chon, he_so_moi, data.get('cong_trinh_id')))
        msg = f"Đã ghi nhận {he_so_moi} công cho ngày {ngay_chon}!"
        
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': msg})

# ==================== ĐỒNG BỘ CÁC ROUTE CÒN LẠI CỦA GIAI ĐOẠN 1 ====================
@app.route('/api/admin/ung-luong', methods=['POST'])
def ung_luong():
    data = request.json
    conn = get_db_connection()
    conn.execute("UPDATE nhan_vien SET tien_ung = tien_ung + ? WHERE id = ?", (float(data['so_tien_ung']), data['nhan_vien_id']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Ghi nhận khoản tiền ứng thành công!'})

@app.route('/api/admin/reset-thang', methods=['POST'])
def reset_thang():
    conn = get_db_connection()
    conn.execute("UPDATE nhan_vien SET tong_cong = 0, luong_tich_luy = 0, doanh_so = 0, tien_ung = 0")
    conn.execute("DELETE FROM lich_su_cong")
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Đã chốt lương và xóa trắng dữ liệu tháng cũ!'})

@app.route('/api/admin/them-cong-trinh', methods=['POST'])
def api_them_cong_trinh():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO cong_trinh (ten_ct, don_gia, chi_phi_vat_tu, chi_phi_nhan_cong, loi_nhuan) VALUES (?, ?, 0, 0, ?)", (data['ten_ct'], data['don_gia'], data['don_gia']))
    ct_id = cursor.lastrowid
    tong_tien_vt = 0
    for item in data.get('vat_tu_list', []):
        vt = conn.execute("SELECT * FROM vat_tu WHERE id = ?", (item['vat_tu_id'],)).fetchone()
        if vt and vt['so_luong'] >= int(item['so_luong_dung']):
            thanh_tien = int(item['so_luong_dung']) * vt['gia_nhap']
            tong_tien_vt += thanh_tien
            conn.execute("UPDATE vat_tu SET so_luong = so_luong - ? WHERE id = ?", (item['so_luong_dung'], vt['id']))
            conn.execute("INSERT INTO ct_vat_tu (cong_trinh_id, vat_tu_id, so_luong_dung, thanh_tien) VALUES (?, ?, ?, ?)", (ct_id, vt['id'], item['so_luong_dung'], thanh_tien))
    conn.execute("UPDATE cong_trinh SET chi_phi_vat_tu = ?, loi_nhuan = don_gia - ? WHERE id = ?", (tong_tien_vt, tong_tien_vt, ct_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Khởi tạo công trình thành công!'})

@app.route('/api/admin/danh-sach-cong-trinh', methods=['GET'])
def danh_sach_cong_trinh():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM cong_trinh").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/phieu-xuat-kho/<int:ct_id>', methods=['GET'])
def phieu_xuat_kho(ct_id):
    conn = get_db_connection()
    ct = conn.execute("SELECT * FROM cong_trinh WHERE id = ?", (ct_id,)).fetchone()
    vattu = conn.execute('SELECT ten_vt, so_luong_dung FROM ct_vat_tu JOIN vat_tu ON ct_vat_tu.vat_tu_id = vat_tu.id WHERE cong_trinh_id = ?', (ct_id,)).fetchall()
    conn.close()
    items_html = "".join([f"<tr><td>{v['ten_vt']}</td><td>{v['so_luong_dung']}</td></tr>" for v in vattu])
    return f"<html><body><h3>PHIẾU XUẤT KHO: {ct['ten_ct']}</h3><table border='1'>{items_html}</table><script>window.print()</script></body></html>"

@app.route('/api/admin/xoa-cong-trinh/<int:id>', methods=['DELETE'])
def xoa_cong_trinh(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM cong_trinh WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Đã xóa công trình!'})

@app.route('/api/admin/them-vat-tu', methods=['POST'])
def api_them_vat_tu():
    data = request.json
    conn = get_db_connection()
    conn.execute("INSERT INTO vat_tu (ten_vt, gia_nhap, so_luong) VALUES (?, ?, ?) ON CONFLICT(ten_vt) DO UPDATE SET so_luong = so_luong + excluded.so_luong", (data['ten_vt'], data['gia_nhap'], data['so_luong']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Cập nhật kho thành công!'})

@app.route('/api/admin/danh-sach-vat-tu', methods=['GET'])
def danh_sach_vat_tu():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM vat_tu").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/tao-tai-khoan-tho', methods=['POST'])
def tao_tai_khoan_tho():
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO tai_khoan (username, password, role, nhan_vien_id) VALUES (?, ?, 'USER', ?)", (data['username'], data['password'], data['nhan_vien_id']))
        conn.commit()
        res = {'status': 'success', 'message': 'Đã tạo tài khoản thợ!'}
    except: res = {'status': 'error', 'message': 'Trùng tài khoản!'}
    conn.close()
    return jsonify(res)

@app.route('/api/admin/danh-sach-nhan-vien-chua-co-tk', methods=['GET'])
def nv_chua_co_tk():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, fullname FROM nhan_vien WHERE id NOT IN (SELECT nhan_vien_id FROM tai_khoan WHERE nhan_vien_id IS NOT NULL)").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
# API XÓA NHÂN VIÊN VÀ CÁC DỮ LIỆU LIÊN QUAN TRÁNH RÁC DATABASE
@app.route('/api/admin/xoa-nhan-vien/<int:nv_id>', methods=['DELETE'])
def xoa_nhan_vien(nv_id):
    conn = get_db_connection()
    # 1. Xóa lịch sử công của thợ này trước
    conn.execute("DELETE FROM lich_su_cong WHERE nhan_vien_id = ?", (nv_id,))
    # 2. Xóa tài khoản đăng nhập liên kết với thợ này (nếu có)
    conn.execute("DELETE FROM tai_khoan WHERE nhan_vien_id = ?", (nv_id,))
    # 3. Xóa hồ sơ thợ
    conn.execute("DELETE FROM nhan_vien WHERE id = ?", (nv_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Đã xóa sạch hồ sơ và dữ liệu liên quan của thợ!'})
if __name__ == '__main__':
    app.run(debug=True)
