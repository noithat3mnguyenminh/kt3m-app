from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
app.secret_key = 'noithatnguyenminh_key_bi_mat'

# --- KẾT NỐI KÉT SẮT SUPABASE ---
DATABASE_URL = "postgresql://postgres:Noithatnguyenminh%40123@db.wrixjmydmiglullshmxr.supabase.co:5432/postgres"
engine = create_engine(DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))

# Hàm khởi tạo bảng (chạy 1 lần duy nhất)
def init_db():
    commands = [
        "CREATE TABLE IF NOT EXISTS nhan_vien (id SERIAL PRIMARY KEY, fullname TEXT, cong_viec TEXT, luong_co_ban REAL DEFAULT 0, ngay_chot_luong INTEGER DEFAULT 30, doanh_so REAL DEFAULT 0, tien_ung REAL DEFAULT 0, ghi_chu TEXT, tong_cong REAL DEFAULT 0, luong_tich_luy REAL DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS lich_su_cong (id SERIAL PRIMARY KEY, nhan_vien_id INTEGER, ngay_cham TEXT, he_so_cong REAL, cong_trinh_id INTEGER)",
        "CREATE TABLE IF NOT EXISTS cong_trinh (id SERIAL PRIMARY KEY, ten_ct TEXT, don_gia REAL DEFAULT 0, chi_phi_vat_tu REAL DEFAULT 0, chi_phi_nhan_cong REAL DEFAULT 0, loi_nhuan REAL DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS vat_tu (id SERIAL PRIMARY KEY, ten_vt TEXT UNIQUE, gia_nhap REAL DEFAULT 0, so_luong INTEGER DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS ct_vat_tu (id SERIAL PRIMARY KEY, cong_trinh_id INTEGER, vat_tu_id INTEGER, so_luong_dung INTEGER, thanh_tien REAL)",
        "CREATE TABLE IF NOT EXISTS tai_khoan (username TEXT PRIMARY KEY, password TEXT, role TEXT, nhan_vien_id INTEGER)"
    ]
    for cmd in commands:
        db.execute(text(cmd))
    db.commit()

init_db()

# --- CÁC ROUTE ĐIỀU HƯỚNG ---
@app.route('/')
def index():
    if 'username' not in session: return render_template('index.html', page='login')
    return render_template('index.html', page='main', user={'name': session['username'], 'role': session['role'], 'id': session.get('nhan_vien_id')})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = db.execute(text("SELECT * FROM tai_khoan WHERE username = :u AND password = :p"), {'u': data['username'], 'p': data['password']}).fetchone()
    if user:
        session['username'] = user[0]; session['role'] = user[2]; session['nhan_vien_id'] = user[3]
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Sai tài khoản sếp ơi!'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- CÁC HÀM XỬ LÝ DỮ LIỆU CHÍNH ---
@app.route('/api/admin/them-nhan-vien', methods=['POST'])
def them_nhan_vien():
    data = request.json
    db.execute(text("INSERT INTO nhan_vien (fullname, cong_viec, luong_co_ban, ngay_chot_luong, doanh_so, tien_ung, ghi_chu) VALUES (:f, :c, :l, :n, :d, 0, :g)"), 
               {'f': data['fullname'], 'c': data['cong_viec'], 'l': data['luong_co_ban'], 'n': data['ngay_chot_luong'], 'd': data['doanh_so'], 'g': data['ghi_chu']})
    db.commit()
    return jsonify({'status': 'success', 'message': 'Đã thêm hồ sơ nhân viên!'})

@app.route('/api/admin/danh-sach-thong-ke', methods=['GET'])
def danh_sach_thong_ke():
    rows = db.execute(text("SELECT * FROM nhan_vien")).fetchall()
    result = []
    for r in rows:
        result.append({'id': r[0], 'fullname': r[1], 'cong_viec': r[2], 'luong_co_ban': r[3], 'ngay_chot_luong': r[4], 'doanh_so': r[5], 'tien_ung': r[6], 'ghi_chu': r[7], 'tong_cong': r[8], 'luong_tich_luy': r[9], 'lich_su': []})
    return jsonify(result)

@app.route('/api/admin/cham-cong', methods=['POST'])
def admin_cham_cong():
    data = request.json
    db.execute(text("INSERT INTO lich_su_cong (nhan_vien_id, ngay_cham, he_so_cong) VALUES (:nv, :ngay, :heso)"), 
               {'nv': data['nhan_vien_id'], 'ngay': data['ngay_cham'], 'heso': data['he_so_cong']})
    db.commit()
    return jsonify({'status': 'success', 'message': 'Đã ghi nhận công!'})

@app.route('/api/admin/ung-luong', methods=['POST'])
def ung_luong():
    data = request.json
    db.execute(text("UPDATE nhan_vien SET tien_ung = tien_ung + :t WHERE id = :id"), {'t': float(data['so_tien_ung']), 'id': data['nhan_vien_id']})
    db.commit()
    return jsonify({'status': 'success', 'message': 'Đã duyệt ứng!'})

@app.route('/api/admin/reset-thang', methods=['POST'])
def reset_thang():
    db.execute(text("UPDATE nhan_vien SET tong_cong = 0, luong_tich_luy = 0, doanh_so = 0, tien_ung = 0"))
    db.execute(text("DELETE FROM lich_su_cong"))
    db.commit()
    return jsonify({'status': 'success', 'message': 'Đã reset tháng!'})

if __name__ == '__main__':
    app.run(debug=True)
