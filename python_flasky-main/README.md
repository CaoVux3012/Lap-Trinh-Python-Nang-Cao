# Mobile Store AI

Website bán điện thoại xây dựng bằng Python Flask, có tích hợp chatbot AI hỗ trợ tư vấn sản phẩm.

## Công nghệ sử dụng

- Python Flask
- SQLite
- SQLAlchemy
- Flask-Login
- HTML/CSS/Bootstrap
- OpenAI API
- JavaScript Fetch API

## Chức năng chính

- Xem danh sách sản phẩm
- Tìm kiếm và lọc sản phẩm
- Xem chi tiết sản phẩm
- Giỏ hàng
- Đặt hàng
- Đăng nhập quản trị
- Dashboard quản trị
- Quản lý sản phẩm
- Quản lý đơn hàng
- Chatbot AI tư vấn mua điện thoại

## Cách chạy project

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
python seed.py
python app.py


## Build

## Run code trên Docker
```bash
docker build -t flask-project .
```

## Run

```bash
docker run --env-file ..\.env -p 5000:5000 flask-project
```