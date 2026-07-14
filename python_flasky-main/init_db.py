from app import create_app
from extensions import db
from models import User, Category, Product

app = create_app()

with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            full_name="Quản trị viên",
            role="ADMIN"
        )
        admin.set_password("admin123")
        db.session.add(admin)

    if Category.query.count() == 0:
        categories = [
            Category(name="iPhone", description="Điện thoại Apple iPhone"),
            Category(name="Samsung", description="Điện thoại Samsung Galaxy"),
            Category(name="Xiaomi", description="Điện thoại Xiaomi hiệu năng cao"),
            Category(name="OPPO", description="Điện thoại OPPO chụp ảnh đẹp"),
        ]
        db.session.add_all(categories)
        db.session.commit()

    if Product.query.count() == 0:
        iphone = Category.query.filter_by(name="iPhone").first()
        samsung = Category.query.filter_by(name="Samsung").first()
        xiaomi = Category.query.filter_by(name="Xiaomi").first()

        products = [
            Product(
                name="iPhone 15 Pro Max",
                brand="Apple",
                price=28990000,
                old_price=32990000,
                stock=12,
                image_url="https://images.unsplash.com/photo-1695048133142-1a20484d2569",
                short_description="Flagship Apple mạnh mẽ, camera đẹp, pin tốt.",
                description="iPhone 15 Pro Max phù hợp cho người dùng cần hiệu năng cao, quay video đẹp và hệ sinh thái Apple.",
                specs="Chip A17 Pro, RAM 8GB, màn hình 6.7 inch, camera 48MP, pin dùng cả ngày.",
                category=iphone
            ),
            Product(
                name="Samsung Galaxy S24 Ultra",
                brand="Samsung",
                price=25990000,
                old_price=30990000,
                stock=10,
                image_url="https://images.unsplash.com/photo-1610945265064-0e34e5519bbf",
                short_description="Màn hình đẹp, bút S Pen, camera zoom mạnh.",
                description="Galaxy S24 Ultra phù hợp cho công việc, chụp ảnh xa, ghi chú và trải nghiệm Android cao cấp.",
                specs="Snapdragon 8 Gen 3, RAM 12GB, màn hình AMOLED 6.8 inch, camera 200MP.",
                category=samsung
            ),
            Product(
                name="Xiaomi 14T Pro",
                brand="Xiaomi",
                price=14990000,
                old_price=16990000,
                stock=18,
                image_url="https://images.unsplash.com/photo-1598327105666-5b89351aff97",
                short_description="Hiệu năng cao, sạc nhanh, giá tốt.",
                description="Xiaomi 14T Pro phù hợp cho người dùng thích chơi game, sạc nhanh và cấu hình mạnh trong tầm giá.",
                specs="Dimensity cao cấp, RAM 12GB, sạc nhanh, màn hình tần số quét cao.",
                category=xiaomi
            ),
        ]

        db.session.add_all(products)

    db.session.commit()

    print("Database initialized successfully.")
    print("Admin account: admin / admin123")