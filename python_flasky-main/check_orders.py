from app import create_app
from models import Order

app = create_app()

with app.app_context():
    orders = Order.query.all()

    print("Total orders:", len(orders))

    for order in orders:
        print(order.id, order.customer_name, order.total_amount, order.status)
        for item in order.items:
            print(" -", item.product.name, item.quantity, item.price)