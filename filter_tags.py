import sqlite3
import json

DB_NAME = 'safeplate.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def check_dietary_labels(meal):
    """Classify diets based on a list of ingredients."""
    ingredients = []
    for i in range(1, 21):
        ing = meal.get(f'strIngredient{i}')
        if ing and ing.strip():
            ingredients.append(ing.strip().lower())

    ing_text = " ".join(ingredients)
    category = (meal.get('strCategory') or '').lower()
    
    labels = []

    # 1. Vegetarian
    meat_keywords = ['chicken', 'beef', 'pork', 'lamb', 'bacon', 'fish', 'prawn', 'salmon', 'tuna', 'turkey', 'duck', 'meat', 'sausage', 'prosciutto']
    if not any(k in ing_text for k in meat_keywords) and category not in ['beef', 'chicken', 'pork', 'lamb', 'seafood']:
        labels.append('Vegetarian')

    # 2. Vegan
    non_vegan = meat_keywords + ['egg', 'milk', 'butter', 'cheese', 'cream', 'yogurt', 'honey', 'mayonnaise', 'ghee']
    if not any(k in ing_text for k in non_vegan) and category not in ['beef', 'chicken', 'pork', 'lamb', 'seafood']:
        labels.append('Vegan')

    # 3. Dairy-Free
    dairy_keywords = ['milk', 'butter', 'cheese', 'cream', 'yogurt', 'ghee', 'parmesan', 'mozzarella', 'cheddar', 'feta']
    if not any(k in ing_text for k in dairy_keywords):
        labels.append('Dairy-Free')

    # 4. Gluten-Free
    gluten_keywords = ['flour', 'wheat', 'spaghetti', 'pasta', 'bread', 'noodle', 'soy sauce', 'semolina', 'barley', 'rye']
    if not any(k in ing_text for k in gluten_keywords):
        labels.append('Gluten-Free')

    # 5. Nut-Free
    nut_keywords = ['peanut', 'almond', 'cashew', 'walnut', 'hazelnut', 'pecan', 'pistachio', 'macadamia', 'nut']
    if not any(k in ing_text for k in nut_keywords):
        labels.append('Nut-Free')

    # 6. Soy-Free
    soy_keywords = ['soy', 'soya', 'tofu', 'edamame', 'tamari', 'miso']
    if not any(k in ing_text for k in soy_keywords):
        labels.append('Soy-Free')

    # 7. Halal
    haram_keywords = ['pork', 'bacon', 'ham', 'wine', 'beer', 'cider', 'rum', 'brandy', 'mirin', 'sake', 'alcohol']
    if not any(k in ing_text for k in haram_keywords) and category != 'pork':
        labels.append('Halal')

    # 8. Kosher
    non_kosher = ['pork', 'bacon', 'ham', 'shrimp', 'prawn', 'crab', 'lobster', 'mussel', 'squid', 'oyster']
    if not any(k in ing_text for k in non_kosher) and category != 'pork':
        labels.append('Kosher')

    # 9. Low-Sodium
    high_sodium_keywords = ['salt', 'soy sauce', 'fish sauce', 'oyster sauce', 'bouillon', 'stock', 'cube', 'teriyaki', 'msg', 'bacon', 'ham', 'parmesan', 'cheddar', 'pickle']
    if not any(k in ing_text for k in high_sodium_keywords):
        labels.append('Low-Sodium')

    return ",".join(labels)  # Chuỗi dạng: "Vegetarian,Gluten-Free,Halal"

def process_and_update_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Add dietary_tags if CSDL don't have
    try:
        cursor.execute("ALTER TABLE recipe_cache ADD COLUMN dietary_tags TEXT;")
        print("-> Added 'dietary_tags' column to recipe_cache table.")
    except sqlite3.OperationalError:
        print("-> Column 'dietary_tags' already exists.")

    # 2. Read all the recipes from CSDL
    rows = cursor.execute("SELECT meal_id, raw_data FROM recipe_cache").fetchall()
    
    count = 0
    for row in rows:
        meal_id = row['meal_id']
        meal = json.loads(row['raw_data'])
        
        tags = check_dietary_labels(meal)
        
        # Update to safeplate.db
        cursor.execute(
            "UPDATE recipe_cache SET dietary_tags = ? WHERE meal_id = ?",
            (tags, meal_id)
        )
        count += 1

    conn.commit()
    conn.close()
    print(f" DONE! Successfully updated dietary tags for {count} recipes in safeplate.db.")

if __name__ == '__main__':
    process_and_update_db()