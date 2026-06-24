@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    users = call_gs("read", "tai_khoan")
    
    if not isinstance(users, list):
        return jsonify({'status': 'error', 'message': 'Lỗi kết nối dữ liệu'})
        
    user = None
    # Sửa logic: Tìm ưu tiên dòng nào có role là 'admin' trước
    for u in users:
        if str(u.get('username', '')).strip().lower() == str(data.get('username', '')).strip().lower() and \
           str(u.get('password', '')).strip() == str(data.get('password', '')).strip():
            # Nếu tìm thấy user, kiểm tra role
            if str(u.get('role', '')).strip().lower() == 'admin':
                user = u
                break # Ưu tiên admin thì dừng luôn
            else:
                user = u # Nếu là thợ thì lưu lại nhưng chưa dừng (để xem có dòng admin nào khác không)
            
    if user:
        session['username'] = user['username']
        session['role'] = user.get('role', 'tho') # Mặc định là thợ nếu không có cột role
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Sai tài khoản hoặc mật khẩu!'})
