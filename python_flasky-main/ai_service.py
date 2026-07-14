import os
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask_ai_assistant(user_message):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("CHUA NHAN OPENAI_API_KEY")
        return fallback_answer(user_message)

    try:
        print("DANG GOI OPENAI THAT")

        products_context = get_products_context()

        response = client.chat.completions.create(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    messages=[
        {
            "role": "system",
            "content": f"""
Bạn là trợ lý AI tư vấn mua điện thoại cho website Mobile Store AI.
Trả lời bằng tiếng Việt, ngắn gọn, thân thiện.
Chỉ tư vấn dựa trên danh sách sản phẩm sau:

{products_context}
"""
        },
        {
            "role": "user",
            "content": user_message
        }
    ],
    max_completion_tokens=350
)

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("LOI OPENAI:", e)

        error_text = str(e).lower()

        if "insufficient_quota" in error_text or "429" in error_text:
            print("OPENAI HET QUOTA - DUNG FALLBACK NOI BO")
            return fallback_answer(user_message)

        return fallback_answer(user_message)


def get_products_context():
    try:
        from models import Product

        products = Product.query.filter_by(is_active=True).all()

        if not products:
            return "Hiện chưa có sản phẩm nào trong hệ thống."

        lines = []

        for product in products:
            lines.append(
                f"- {product.name} | Hãng: {product.brand} | "
                f"Giá: {format_price(product.price)} | "
                f"Mô tả: {product.short_description} | "
                f"Tồn kho: {product.stock}"
            )

        return "\n".join(lines)

    except Exception as e:
        print("LOI LAY SAN PHAM CHO AI:", e)
        return "Không lấy được danh sách sản phẩm."


def fallback_answer(user_message):
    try:
        from models import Product

        message = normalize_text(user_message)
        budget = extract_budget(message)
        products = Product.query.filter_by(is_active=True).all()

        if not products:
            return "Hiện cửa hàng chưa có sản phẩm để tư vấn. Bạn quay lại sau nhé."
        if "chup anh" in message or "camera" in message or "dep ko" in message or "dep khong" in message:
            products = Product.query.filter_by(is_active=True).all()

        camera_keywords = ["iphone", "pro max", "samsung", "ultra", "camera"]
        camera_products = []

        for product in products:
            product_text = normalize_text(
                f"{product.name} {product.brand} {product.short_description}"
            )

            if any(keyword in product_text for keyword in camera_keywords):
                camera_products.append(product)

        if camera_products:
            best_product = max(camera_products, key=lambda product: product.price)

            return (
                f"Có, {best_product.name} chụp ảnh khá đẹp trong các sản phẩm hiện có. "
                f"Máy phù hợp nếu bạn ưu tiên camera, ảnh sắc nét và quay video ổn định. "
                f"Giá hiện tại là {format_price(best_product.price)}. "
                f"Nếu bạn muốn tiết kiệm hơn, mình có thể gợi ý thêm mẫu giá thấp hơn."
            )

        products = Product.query.filter_by(is_active=True).all()

        if not products:
            return "Hiện cửa hàng chưa có sản phẩm để tư vấn. Bạn quay lại sau nhé."

        suitable_products = products

        if budget:
            suitable_products = [
                product for product in products
                if product.price <= budget
            ]

        if not suitable_products:
            cheapest_product = min(products, key=lambda product: product.price)

            return (
                f"Với ngân sách hiện tại, sản phẩm gần phù hợp nhất là "
                f"{cheapest_product.name} giá {format_price(cheapest_product.price)}. "
                f"Nếu bạn có thể tăng ngân sách thêm một chút, mình sẽ tư vấn được lựa chọn tốt hơn."
            )

        scored_products = []

        for product in suitable_products:
            score = calculate_score(product, message)
            scored_products.append((score, product))

        scored_products.sort(key=lambda item: item[0], reverse=True)
        best_product = scored_products[0][1]

        reason = build_reason(best_product, message, budget)

        return (
            f"Mình gợi ý bạn chọn {best_product.name} "
            f"giá {format_price(best_product.price)}. "
            f"{reason} "
            f"Sản phẩm này phù hợp để bạn cân nhắc trong tầm nhu cầu hiện tại."
        )

    except Exception as e:
        print("LOI FALLBACK:", e)
        return (
            "Bạn có thể cho mình biết rõ hơn ngân sách và nhu cầu chính không? "
            "Ví dụ: chơi game, chụp ảnh, pin trâu, dùng iPhone hay Android. "
            "Mình sẽ gợi ý sản phẩm phù hợp hơn."
        )


def calculate_score(product, message):
    text = normalize_text(
        f"{product.name} {product.brand} {product.short_description}"
    )

    score = 0

    if "chup anh" in message or "camera" in message:
        if any(word in text for word in ["camera", "chup anh", "iphone", "samsung", "ultra", "pro max"]):
            score += 4

    if "pin" in message or "pin tot" in message or "pin trau" in message:
        if any(word in text for word in ["pin", "dung ca ngay", "xiaomi", "samsung"]):
            score += 4

    if "game" in message or "choi game" in message:
        if any(word in text for word in ["hieu nang", "gaming", "snapdragon", "ultra", "pro"]):
            score += 4

    if "iphone" in message or "apple" in message:
        if "iphone" in text or "apple" in text:
            score += 5

    if "samsung" in message:
        if "samsung" in text:
            score += 5

    if "xiaomi" in message:
        if "xiaomi" in text:
            score += 5

    score += product.price / 1_000_000

    return score


def build_reason(product, message, budget):
    reasons = []

    product_text = normalize_text(
        f"{product.name} {product.brand} {product.short_description}"
    )

    if budget:
        reasons.append(f"Máy nằm trong ngân sách khoảng {format_price(budget)} của bạn.")

    if "chup anh" in message or "camera" in message:
        reasons.append("Nhu cầu chụp ảnh của bạn khá hợp với mẫu này.")

    if "pin" in message:
        reasons.append("Máy cũng phù hợp nếu bạn ưu tiên pin và dùng ổn định hằng ngày.")

    if "game" in message:
        reasons.append("Hiệu năng của máy đủ tốt cho nhu cầu chơi game.")

    if "iphone" in product_text or "apple" in product_text:
        reasons.append("Nếu bạn thích hệ sinh thái Apple thì đây là lựa chọn đáng cân nhắc.")

    if "samsung" in product_text:
        reasons.append("Samsung có màn hình đẹp, camera ổn và trải nghiệm Android cao cấp.")

    if "xiaomi" in product_text:
        reasons.append("Xiaomi thường mạnh về hiệu năng và giá tốt trong cùng phân khúc.")

    if not reasons:
        reasons.append("Máy có mức giá và cấu hình khá cân bằng.")

    return " ".join(reasons)


def extract_budget(message):
    message = normalize_text(message)

    patterns = [
        r"(\d+)\s*trieu",
        r"(\d+)\s*tr",
        r"(\d+)\s*million",
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return int(match.group(1)) * 1_000_000

    money_match = re.search(r"(\d{7,})", message)
    if money_match:
        return int(money_match.group(1))

    return None


def normalize_text(text):
    text = text.lower()

    replacements = {
        "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a",
        "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
        "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
        "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "í": "i", "ì": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ó": "o", "ò": "o", "ỏ": "o", "õ": "o", "ọ": "o",
        "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
        "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ú": "u", "ù": "u", "ủ": "u", "ũ": "u", "ụ": "u",
        "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ý": "y", "ỳ": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
        "đ": "d",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def format_price(price):
    return f"{price:,.0f}đ"