from flask import Flask
app = Flask(__name__)
@app.route('/')
def hello_world():
    return 'Hello Flask!'


if __name__ == '__main__':
    app.run(debug=True, port=80, host='0.0.0.0')     # 设置debug=True是为了让代码修改实时生效，而不用每次重启加载
