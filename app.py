from flask import Flask, render_template, request, jsonify, session
import requests, json, os

app = Flask(__name__)
app.secret_key = 'noithatnguyenminh_key'

# Lấy URL từ biến môi trường trên Render
GS_URL = os.environ.get("GS_URL")

def call_gs(action, table, **kwargs):
    if not GS_URL: return []
    try:
        res = requests.post(GS_URL, data=json.dumps({"action": action, "table": table, **kwargs}), timeout=15)
        return res.json()
    except: return []

@app.route('/')
def index():
    # Kiểm tra xem có session không
    if 'username' not in session:
        return render_template('index.html', page='login')
    # Nếu đã đăng nhập, hiển thị trang tương ứng với role
    return render_template('index.html', page='main', user=session)

# Thêm cái này để bảo vệ các trang khác (nếu có)
@app.before_request
def restrict_access():
    if request.endpoint and request.endpoint != 'index' and request.endpoint != 'api_login' and 'username' not in session:
        return render_template('index.html', page='login')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username_input = str(data.get('username', '')).strip().lower()
    password_input = str(data.get('password', '')).strip()
    
    users = call_gs("read", "tai_khoan")
    
    if not isinstance(users, list):
        return jsonify({'status': 'error', 'message': 'Lỗi kết nối'})
        
    found_user = None
    # Duyệt qua danh sách để tìm user
    for u in users:
        u_name = str(u.get('username', '')).strip().lower()
        u_pass = str(u.get('password', '')).strip()
        
        # Chỉ xét dòng có dữ liệu (bỏ qua dòng trống)
        if u_name and u_name == username_input and u_pass == password_input:
            # Ưu tiên lấy dòng có role admin
            if str(u.get('role', '')).strip().lower() == 'admin':
                found_user = u
                break
            else:
                found_user = u # Lưu thợ lại để tạm, nhưng vẫn tìm tiếp xem có admin không
            
    if found_user:
        session['username'] = found_user.get('username')
        session['role'] = found_user.get('role', 'tho')
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Sai tài khoản hoặc mật khẩu!'})

@app.route('/api/debug_data', methods=['GET'])
def debug_data():
    users = call_gs("read", "tai_khoan")
    return jsonify({'data': users})

if __name__ == '__main__':
    app.run()
