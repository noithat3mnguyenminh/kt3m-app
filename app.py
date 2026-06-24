from flask import Flask, render_template, request, jsonify, session
import requests, json

app = Flask(__name__)
app.secret_key = 'noithatnguyenminh_key'
GS_URL = "https://script.google.com/macros/s/AKfycbxhInRrtKUm0gLwDuAjOIPwOUQbfkPLe9vkzo6358aaopKy1a7VokHG2HksJm6nyS7f/exec"

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
    
    # Kiểm tra xem users có phải là list không
    if not isinstance(users, list):
        print(f"DEBUG: Dữ liệu trả về không phải list: {users}")
        return jsonify({'status': 'error', 'message': 'Lỗi kết nối dữ liệu'})
        
    user = None
    for u in users:
        # Kiểm tra u phải là dictionary
        if isinstance(u, dict):
            if str(u.get('username', '')).strip().lower() == str(data.get('username', '')).strip().lower() and \
               str(u.get('password', '')).strip() == str(data.get('password', '')).strip():
                user = u
                break
            
    if user:
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Sai tài khoản hoặc mật khẩu!'})
def debug_login():
    data = request.json
    users = call_gs("read", "tai_khoan")
    return jsonify({'dữ_liệu_lấy_được': users, 'sếp_nhập_vào': data})
if __name__ == '__main__':
    app.run()
