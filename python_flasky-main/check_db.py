from app import create_app
from models import User, Category, Product

app = create_app()

with app.app_context():
    print("Users:", User.query.count())
    print("Categories:", Category.query.count())
    print("Products:", Product.query.count())

    for product in Product.query.all():
        print(product.name, product.price)