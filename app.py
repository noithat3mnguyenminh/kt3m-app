from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import json

app = Flask(__name__)
app.secret_key = 'noithatnguyenminh_key'

# Link Google Sheet của sếp
GS_URL = "https://script.google.com/macros/s/AKfycbyfD0j2J82v8yV-Dq4P32qU4N89NlF6Vw8m4h2jR8S4/exec"

def call_gs(action, table, values=None, id=None, updates=None):
    data = {"action": action, "table": table, "values": values, "id": id, "updates": updates}
    try:
        res = requests.post(GS_URL, data=json.dumps(data), timeout=15)
        return res.json()
    except: return []

# ==================== CÁC ROUTE GIAO DIỆN ====================
@app.route('/')
def index():
    if 'username' not in session: return render_template('index.html', page='login')
    return render_template('index.html', page='main', user={'name': session['username'], 'role': session['role'], 'id': session.get('nhan_vien_id')})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    users = call_gs("read", "tai_khoan")
    user = next((u for u in users if u['username'] == data['username'] and str(u['password']) == str(data['password'])), None)
    if user:
        session['username'] = user['username']
        session['role'] = user['role']
        session['nhan_vien_id'] = user.get('nhan_vien_id')
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Sai tài khoản sếp ơi!'})

# ==================== TÍNH NĂNG CHẤM CÔNG (Ví dụ mẫu) ====================
@app.route('/api/admin/cham-cong', methods=['POST'])
def admin_cham_cong():
    data = request.json
    # Ghi vào bảng lich_su_cong trong Google Sheets
    call_gs("insert", "lich_su_cong", [None, data['nhan_vien_id'], data['ngay_cham'], data['he_so_cong'], data.get('cong_trinh_id')])
    return jsonify({'status': 'success', 'message': 'Đã lưu lên mây thành công!'})

@app.route('/api/admin/danh-sach-thong-ke', methods=['GET'])
def danh_sach_thong_ke():
    # Đọc dữ liệu từ Google Sheets thay vì SQLite
    nv_list = call_gs("read", "nhan_vien")
    return jsonify(nv_list)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
