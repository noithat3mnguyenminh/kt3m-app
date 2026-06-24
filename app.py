from flask import Flask, render_template, request, jsonify, session
import requests, json

app = Flask(__name__)
app.secret_key = 'noithatnguyenminh_key'
GS_URL = "https://script.google.com/macros/s/AKfycbzdjH_A1B7l0dbWqmB5X1wfGYiPxWwV9LFeorxyWEZEfyTZzjub6cR4DyFKj0RkV3OT/exec"

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
    user = next((u for u in users if str(u.get('username')).strip() == str(data.get('username')).strip() 
                 and str(u.get('password')).strip() == str(data.get('password')).strip()), None)
    if user:
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Sai tài khoản hoặc mật khẩu!'})

if __name__ == '__main__':
    app.run()
