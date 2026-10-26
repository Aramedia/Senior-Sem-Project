import sqlite3
import json

DB_NAME = 'safeplate.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def compile_ingredients_by_diet():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve all recipes that have been assigned dietary_tags
    rows = cursor.execute("SELECT raw_data, dietary_tags " \
                            "FROM recipe_cache " \
                            "WHERE dietary_tags " \
                            "IS NOT NULL").fetchall()

    # Initialize a dictionary containing a list of ingredients for each diet.
    diet_summary = {
        'Gluten-Free': set(),
        'Dairy-Free': set(),
        'Vegan': set(),
        'Vegetarian': set(),
        'Nut-Free': set(),
        'Soy-Free': set(),
        'Halal': set(),
        'Kosher': set(),
        'Low-Sodium': set()
    }

    for row in rows:
        tags = [t.strip() for t in row['dietary_tags'].split(',') if t.strip()]
        meal = json.loads(row['raw_data'])

        # Get the list of ingredients for this dish
        meal_ingredients = []
        for i in range(1, 21):
            ing = meal.get(f'strIngredient{i}')
            if ing and ing.strip():
                meal_ingredients.append(ing.strip().title())

        # Add ingredients to the respective diets
        for tag in tags:
            if tag in diet_summary:
                diet_summary[tag].update(meal_ingredients)

    # Convert a set() into a sorted list
    output_data = {}
    for diet, ing_set in diet_summary.items():
        output_data[diet] = sorted(list(ing_set))

    # Connect to file JSON
    with open('static/diet_ingredients.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    conn.close()
    print(" The list of ingredients based on the diet has been compiled into a file!")

if __name__ == '__main__':
    compile_ingredients_by_diet()