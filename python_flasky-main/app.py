import re
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from config import Config
from extensions import db, login_manager
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Product, Category, Order, OrderItem
from ai_service import ask_ai_assistant

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "admin_login"
    login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route("/")
    def home():
        featured_products = Product.query.filter_by(is_active=True).limit(3).all()
        categories = Category.query.all()
        return render_template(
            "home.html",
            featured_products=featured_products,
            categories=categories
        )

    @app.route("/products")
    def products():
        keyword = request.args.get("keyword", "").strip()
        brand = request.args.get("brand", "").strip()
        category_id = request.args.get("category_id", "").strip()

        query = Product.query.filter_by(is_active=True)

        if keyword:
            query = query.filter(Product.name.ilike(f"%{keyword}%"))

        if brand:
            query = query.filter(Product.brand == brand)

        if category_id:
            query = query.filter(Product.category_id == int(category_id))

        products = query.order_by(Product.created_at.desc()).all()
        categories = Category.query.all()

        brands = [
            row[0] for row in db.session.query(Product.brand)
            .filter_by(is_active=True)
            .distinct()
            .all()
        ]

        return render_template(
            "products.html",
            products=products,
            categories=categories,
            brands=brands,
            keyword=keyword,
            selected_brand=brand,
            selected_category_id=category_id
        )

    @app.route("/products/<int:product_id>")
    def product_detail(product_id):
        product = Product.query.get_or_404(product_id)
        related_products = Product.query.filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.is_active == True
        ).limit(3).all()

        return render_template(
            "product_detail.html",
            product=product,
            related_products=related_products
        )


    def get_cart_items():
        cart_data = session.get("cart", {})
        cart_items = []
        total_amount = 0

        for product_id, quantity in cart_data.items():
            product = Product.query.get(int(product_id))

            if product and product.is_active:
                item_total = product.price * quantity
                total_amount += item_total

                cart_items.append({
                    "product": product,
                    "quantity": quantity,
                    "item_total": item_total
                })

        return cart_items, total_amount
    @app.route("/cart")
    def cart():
        cart_items, total_amount = get_cart_items()

        return render_template(
            "cart.html",
            cart_items=cart_items,
            total_amount=total_amount
        )

    @app.route("/cart/add/<int:product_id>")
    def add_to_cart(product_id):
        product = Product.query.get_or_404(product_id)

        if not product.is_active:
            flash("Sản phẩm hiện không khả dụng.", "warning")
            return redirect(url_for("products"))

        cart_data = session.get("cart", {})
        product_key = str(product_id)

        if product_key in cart_data:
            cart_data[product_key] += 1
        else:
            cart_data[product_key] = 1

        session["cart"] = cart_data
        session.modified = True

        flash(f"Đã thêm {product.name} vào giỏ hàng.", "success")
        return redirect(url_for("cart"))

    @app.route("/cart/update/<int:product_id>", methods=["POST"])
    def update_cart(product_id):
        quantity = int(request.form.get("quantity", 1))
        cart_data = session.get("cart", {})
        product_key = str(product_id)

        if quantity <= 0:
            cart_data.pop(product_key, None)
        else:
            cart_data[product_key] = quantity

        session["cart"] = cart_data
        session.modified = True

        flash("Giỏ hàng đã được cập nhật.", "success")
        return redirect(url_for("cart"))

    @app.route("/cart/remove/<int:product_id>")
    def remove_from_cart(product_id):
        cart_data = session.get("cart", {})
        product_key = str(product_id)

        cart_data.pop(product_key, None)

        session["cart"] = cart_data
        session.modified = True

        flash("Đã xóa sản phẩm khỏi giỏ hàng.", "success")
        return redirect(url_for("cart"))

    @app.route("/cart/clear")
    def clear_cart():
        session.pop("cart", None)
        flash("Đã xóa toàn bộ giỏ hàng.", "success")
        return redirect(url_for("cart"))
    
    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        cart_items, total_amount = get_cart_items()

        if not cart_items:
            flash("Giỏ hàng đang trống, vui lòng chọn sản phẩm trước khi đặt hàng.", "warning")
            return redirect(url_for("products"))

        if request.method == "POST":
            customer_name = request.form.get("customer_name", "").strip()
            customer_phone = request.form.get("customer_phone", "").strip()
            customer_email = request.form.get("customer_email", "").strip()
            customer_address = request.form.get("customer_address", "").strip()
            note = request.form.get("note", "").strip()

            if not customer_name or not customer_phone or not customer_address:
                flash("Vui lòng nhập đầy đủ họ tên, số điện thoại và địa chỉ nhận hàng.", "danger")
                return redirect(url_for("checkout"))

            order = Order(
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_email=customer_email,
                customer_address=customer_address,
                note=note,
                total_amount=total_amount,
                status="PENDING",
                payment_method="COD"
            )

            db.session.add(order)
            db.session.flush()

            for item in cart_items:
                product = item["product"]
                quantity = item["quantity"]

                if quantity > product.stock:
                    db.session.rollback()
                    flash(f"Sản phẩm {product.name} không đủ tồn kho.", "danger")
                    return redirect(url_for("cart"))

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    price=product.price
                )

                product.stock -= quantity
                db.session.add(order_item)

            db.session.commit()
            session.pop("cart", None)

            flash("Đặt hàng thành công! Cảm ơn bạn đã mua hàng.", "success")
            return redirect(url_for("order_success", order_id=order.id))

        return render_template(
            "checkout.html",
            cart_items=cart_items,
            total_amount=total_amount
        )

    @app.route("/order-success/<int:order_id>")
    def order_success(order_id):
        order = Order.query.get_or_404(order_id)
        return render_template("order_success.html", order=order)

    # Route xử lý đăng ký tài khoản cho User với đầy đủ các ràng buộc
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("home"))

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("username", "").strip()
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "")

            # 1. Kiểm tra định dạng Gmail (Có dấu @ và cấu trúc email hợp lệ)
            if not re.match(r"[^@]+@[^@]+\.[^@]+", username):
                flash("Gmail không đúng định dạng và bắt buộc phải chứa ký tự '@'.", "danger")
                return render_template("register.html")

            # 2. Kiểm tra định dạng số điện thoại (Phải bao gồm đúng 10 số)
            if not re.match(r"^[0-9]{10}$", phone):
                flash("Số điện thoại không hợp lệ. Vui lòng nhập đúng 10 chữ số.", "danger")
                return render_template("register.html")

            # 3. Kiểm tra định dạng mật khẩu (Ký tự đầu tiên phải viết hoa, và có tối thiểu 1 con số)
            if not password or not password[0].isupper() or not any(char.isdigit() for char in password):
                flash("Mật khẩu phải viết hoa chữ cái đầu tiên và có ít nhất 1 chữ số.", "danger")
                return render_template("register.html")

            # 4. Kiểm tra xem Gmail tài khoản này đã tồn tại hay chưa
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Gmail này đã được đăng ký sử dụng cho tài khoản khác.", "danger")
                return render_template("register.html")

            # 5. Khởi tạo thực thể User mới với quyền vai trò mặc định là USER
            user = User(
                username=username,
                full_name=full_name,
                role="USER"
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("Đăng ký tài khoản thành công! Vui lòng đăng nhập.", "success")
            return redirect(url_for("admin_login"))

        return render_template("register.html")
    
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if current_user.is_authenticated:
            return redirect(url_for("admin_dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user)
                flash("Đăng nhập admin thành công.", "success")
                return redirect(url_for("admin_dashboard"))

            flash("Tên đăng nhập hoặc mật khẩu không đúng.", "danger")
            return redirect(url_for("admin_login"))

        return render_template("admin_login.html")
    @app.route("/admin/logout")
    @login_required
    def admin_logout():
        logout_user()
        flash("Bạn đã đăng xuất.", "success")
        return redirect(url_for("home"))
    
    @app.route("/admin")
    @login_required
    def admin_dashboard():
        total_products = Product.query.count()
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status="PENDING").count()

        revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0

        latest_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        low_stock_products = Product.query.filter(Product.stock <= 5).limit(5).all()

        return render_template(
            "admin_dashboard.html",
            total_products=total_products,
            total_orders=total_orders,
            pending_orders=pending_orders,
            revenue=revenue,
            latest_orders=latest_orders,
            low_stock_products=low_stock_products
        )
    @app.route("/admin/products")
    @login_required
    def admin_products():
        products = Product.query.order_by(Product.created_at.desc()).all()

        return render_template(
            "admin_products.html",
            products=products
        )
    @app.route("/admin/products/create", methods=["GET", "POST"])
    @login_required
    def admin_product_create():
        categories = Category.query.all()

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            brand = request.form.get("brand", "").strip()
            price = int(request.form.get("price", 0))
            old_price = request.form.get("old_price", "").strip()
            stock = int(request.form.get("stock", 0))
            image_url = request.form.get("image_url", "").strip()
            short_description = request.form.get("short_description", "").strip()
            description = request.form.get("description", "").strip()
            specs = request.form.get("specs", "").strip()
            category_id = int(request.form.get("category_id"))

            if not name or not brand or price <= 0:
                flash("Vui lòng nhập tên, thương hiệu và giá hợp lệ.", "danger")
                return redirect(url_for("admin_product_create"))

            product = Product(
                name=name,
                brand=brand,
                price=price,
                old_price=int(old_price) if old_price else None,
                stock=stock,
                image_url=image_url,
                short_description=short_description,
                description=description,
                specs=specs,
                category_id=category_id,
                is_active=True
            )

            db.session.add(product)
            db.session.commit()

            flash("Đã thêm sản phẩm mới.", "success")
            return redirect(url_for("admin_products"))

        return render_template(
            "admin_product_form.html",
            product=None,
            categories=categories,
            form_title="Thêm sản phẩm"
        )
    @app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
    @login_required
    def admin_product_edit(product_id):
        product = Product.query.get_or_404(product_id)
        categories = Category.query.all()

        if request.method == "POST":
            product.name = request.form.get("name", "").strip()
            product.brand = request.form.get("brand", "").strip()
            product.price = int(request.form.get("price", 0))

            old_price = request.form.get("old_price", "").strip()
            product.old_price = int(old_price) if old_price else None

            product.stock = int(request.form.get("stock", 0))
            product.image_url = request.form.get("image_url", "").strip()
            product.short_description = request.form.get("short_description", "").strip()
            product.description = request.form.get("description", "").strip()
            product.specs = request.form.get("specs", "").strip()
            product.category_id = int(request.form.get("category_id"))
            product.is_active = request.form.get("is_active") == "on"

            db.session.commit()

            flash("Đã cập nhật sản phẩm.", "success")
            return redirect(url_for("admin_products"))

        return render_template(
            "admin_product_form.html",
            product=product,
            categories=categories,
            form_title="Cập nhật sản phẩm"
        )
    @app.route("/admin/products/delete/<int:product_id>")
    @login_required
    def admin_product_delete(product_id):
        product = Product.query.get_or_404(product_id)
        product.is_active = False
        db.session.commit()

        flash("Đã ẩn sản phẩm khỏi website.", "success")
        return redirect(url_for("admin_products"))
    
    @app.route("/admin/orders")
    @login_required
    def admin_orders():
        status = request.args.get("status", "").strip()

        query = Order.query

        if status:
            query = query.filter_by(status=status)

        orders = query.order_by(Order.created_at.desc()).all()

        return render_template(
            "admin_orders.html",
            orders=orders,
            selected_status=status
        )


    @app.route("/admin/orders/<int:order_id>")
    @login_required
    def admin_order_detail(order_id):
        order = Order.query.get_or_404(order_id)

        return render_template(
            "admin_order_detail.html",
            order=order
        )


    @app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
    @login_required
    def admin_order_update_status(order_id):
        order = Order.query.get_or_404(order_id)
        new_status = request.form.get("status", "PENDING")

        allowed_statuses = ["PENDING", "CONFIRMED", "SHIPPING", "COMPLETED", "CANCELLED"]

        if new_status not in allowed_statuses:
            flash("Trạng thái đơn hàng không hợp lệ.", "danger")
            return redirect(url_for("admin_order_detail", order_id=order.id))

        order.status = new_status
        db.session.commit()

        flash("Đã cập nhật trạng thái đơn hàng.", "success")
        return redirect(url_for("admin_order_detail", order_id=order.id))
    @app.route("/api/chatbot", methods=["POST"])
    def chatbot_api():
        data = request.get_json() or {}
        message = data.get("message", "").strip()

        if not message:
            return jsonify({
                "success": False,
                "answer": "Vui lòng nhập nội dung cần tư vấn."
            }), 400

        answer = ask_ai_assistant(message)

        return jsonify({
            "success": True,
            "answer": answer
        })
            
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)