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

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username_input = str(data.get('username', '')).strip().lower()
    password_input = str(data.get('password', '')).strip()
    
    users = call_gs("read", "tai_khoan")
    
    if not isinstance(users, list):
        return jsonify({'status': 'error', 'message': 'Lỗi kết nối'})
        
    found_user = None
    for u in users:
        u_name = str(u.get('username', '')).strip().lower()
        u_pass = str(u.get('password', '')).strip()
        
        # Chỉ xét những dòng có username (bỏ qua dòng trống)
        if u_name and u_name == username_input and u_pass == password_input:
            found_user = u
            break # Tìm thấy là chốt ngay
            
    if found_user:
        session['username'] = found_user.get('username')
        session['role'] = found_user.get('role', 'tho')
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Sai tài khoản hoặc mật khẩu!'})
def api_login():
    data = request.json
    username_input = str(data.get('username', '')).strip().lower()
    password_input = str(data.get('password', '')).strip()
    
    users = call_gs("read", "tai_khoan")
    
    if not isinstance(users, list):
        return jsonify({'status': 'error', 'message': 'Lỗi kết nối dữ liệu từ Sheet'})
        
    found_user = None
    # Ưu tiên tìm tài khoản có role là admin nếu trùng lặp username
    for u in users:
        u_name = str(u.get('username', '')).strip().lower()
        u_pass = str(u.get('password', '')).strip()
        
        if u_name == username_input and u_pass == password_input:
            # Nếu là admin thì nhận ngay, không cần tìm tiếp
            if str(u.get('role', '')).strip().lower() == 'admin':
                found_user = u
                break
            else:
                found_user = u # Lưu lại thợ, nhưng tiếp tục tìm xem có dòng nào là admin không
            
    if found_user:
        session['username'] = found_user.get('username')
        session['role'] = found_user.get('role', 'tho')
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Sai tài khoản hoặc mật khẩu!'})

# Đường dẫn debug: Dán link này vào trình duyệt để xem dữ liệu web đang lấy được gì
@app.route('/api/debug_data', methods=['GET'])
def debug_data():
    users = call_gs("read", "tai_khoan")
    return jsonify({'data': users})

if __name__ == '__main__':
    app.run()
