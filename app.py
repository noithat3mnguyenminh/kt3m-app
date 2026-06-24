from flask import Flask, render_template, request, jsonify, session
import requests, json

app = Flask(__name__)
app.secret_key = 'noithatnguyenminh_key'
GS_URL = "https://script.google.com/macros/s/AKfycbym60J9k8DNFUkaxY_yf5VewVPGr2Y-P-aVkwaJmWFEkrfBsHOyIVZJOZySjfV9WHTT/exec"

def call_gs(action, table, **kwargs):
    try:
        res = requests.post(GS_URL, data=json.dumps({"action": action, "table": table, **kwargs}), timeout=15)
        return res.json()
    except: return []

@app.route('/')
def index():
    if 'username' not in session: return render_template('index.html', page='login')
    return render_template('index.html', page='main', user=session)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    users = call_gs("read", "tai_khoan")
    
    # In ra tất cả danh sách user để sếp kiểm tra trong Logs
    print(f"Danh sách từ Sheet: {users}") 
    
    # So sánh kỹ hơn
    user = None
    for u in users:
        # Ép tất cả về dạng chữ (str) để so sánh cho chắc chắn
        if str(u.get('username', '')).strip().lower() == str(data.get('username', '')).strip().lower() and \
           str(u.get('password', '')).strip() == str(data.get('password', '')).strip():
            user = u
            break
            
    if user:
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Không tìm thấy tài khoản này trong hệ thống!'})
def debug_login():
    data = request.json
    users = call_gs("read", "tai_khoan")
    return jsonify({'dữ_liệu_lấy_được': users, 'sếp_nhập_vào': data})
if __name__ == '__main__':
    app.run()
