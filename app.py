import sqlite3
from urllib import response
import random
import os
import json
import re
from flask import Flask, flash, redirect, render_template, request, url_for
from concurrent.futures import ThreadPoolExecutor
import requests
from flask_login import (
    LoginManager,
    UserMixin,
    login_required,
    login_user,
    logout_user,
    current_user
)

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secure-master-key-safeplate'

DB_NAME = 'safeplate.db'

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Function to get a connection to the SQLite3 database
def get_db_connection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    # Help convert query results to dictionary-like objects
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create database tables if they do not exist."""
    conn = get_db_connection()

    # Existing user table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Dietary profile table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS dietary_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            restrictions TEXT,
            FOREIGN KEY (user_id) REFERENCES user(id)
        )
    ''')

    try:
        with open('database.sql', 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
    except Exception as e:
        print(f"Note: Error or notice while executing database.sql: {e}")

    conn.commit()
    conn.close()


# User Information Table in the Database
class User(UserMixin):
    def __init__(self, id, email, password):
        self.id = id
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
  """Download a user by ID from the database using SQLite connection."""
  conn = get_db_connection()
  user = conn.execute('SELECT * FROM user WHERE id = ?', (int (user_id),)).fetchone()
  conn.close()

  if user:
      return User(id=user['id'], 
                  email=user['email'], 
                  password=user['password'])
  return None           

# Rank for recipes based on their tags
def get_cooking_label(instructions_input):
    """
    Automatically determine the length/complexity label based on the total word count of the instructions. 
    The input can be the raw text string or a list of cleaned step sentences.
    """
    if isinstance(instructions_input, list):
        full_text = " ".join(instructions_input)
    else:
        full_text = str(instructions_input or '')

    # Count the number of words in the full text
    word_count = len(full_text.split())

    if word_count < 60:
        return "Quick and Easy"
    elif word_count <= 100:
        return "Standard Cooking"
    else:
        return "Home cooked Special (Longer Recipe)"

# Rank for recipes based on their ingredients
def get_prep_label(meal_or_ingredients):
    """
    Determine the preparation level based on the ingredient count. 
    The input can be a 'meal' dictionary from an API or a list of ingredients.
    """
    if isinstance(meal_or_ingredients, list):
        count = len(meal_or_ingredients)
    elif isinstance(meal_or_ingredients, dict):
        count = 0
        for i in range(1, 21):
            ing = meal_or_ingredients.get(f'strIngredient{i}')
            if ing and ing.strip():
                count += 1
    else:
        count = 0

    if count <= 6:
        return "Easy to prepare"
    elif count <= 11:
        return "Standard to prepare"
    else:
        return "Hard to prepare"
    

def get_flag_emoji(country_code):
    """ Change code name of countries 'VN', 'IE' become flag Emoji ."""
    if not country_code or len(country_code) != 2:
        return "🌐"
    return chr(127397 + ord(country_code[0].upper())) + chr(127397 + ord(country_code[1].upper()))

# Take the list of country from safeplate.DB
def get_countries_from_db():
    """Retrieve a list of countries, including flag information, from the 'areas_cache' table in SQLite."""
    conn = get_db_connection()
    try:
    # Take a list of all area have a meal, avoid country don't have meals
        rows = conn.execute('SELECT * FROM available_countries_view').fetchall() 
    except Exception as e:
        print(f"Error executing view: {e}")
        rows = []   
    conn.close()

    countries = {}
    for row in rows:
        countries[row['area_name']] = {
            'code': row['country_code'],
            'name': row['country_name'],
            'flag_url': row['flag_url'],
            'emoji': get_flag_emoji(row['country_code']) 
        }
    return countries

# Main route for the home page

# 1. main.html
@app.route('/')
def home():
    recipes = []
    try:
        conn = get_db_connection()
        # Take 8 random recipes from SQLite database
        rows = conn.execute('SELECT raw_data FROM recipe_cache ORDER BY RANDOM() LIMIT 8').fetchall()
        conn.close()

        for row in rows:
            meal = json.loads(row['raw_data'])
            raw_tags = meal.get('strTags')
            tags_list = raw_tags.split(',') if raw_tags else [meal.get('strCategory', 'SAFE')]
            raw_instructions = meal.get('strInstructions', '')

            recipes.append({
                'id': meal.get('idMeal'),
                'idMeal': meal.get('idMeal'),
                'name': meal.get('strMeal'),
                'category': meal.get('strCategory'),
                'area': meal.get('strArea'),
                'image': meal.get('strMealThumb'),
                'cooktime': get_cooking_label(raw_instructions),
                'prep_label': get_prep_label(meal),
                'tags': tags_list
            })
    except Exception as e:
        print(f"Error loading home recipes: {e}")

    return render_template('main.html', recipes=recipes)


# 2. Processing Register
@app.route('/register', methods=['GET', 'POST'])
def register():
  if request.method == 'POST':
    email = request.form.get('email')
    password = request.form.get('password')

    conn = get_db_connection()

    # Check if email already exists
    user_exists = conn.execute(
       'SELECT * FROM user WHERE email = ?', (email,)
       ).fetchone()
    if user_exists:
      conn.close()
      return 'Email this has already been used!'

    # Encrypt the password and save it to the database.
    hashed_password = generate_password_hash(password, method='scrypt')
    conn.execute(
       'INSERT INTO user (email, password) VALUES (?, ?)', 
                 (email, hashed_password))
    conn.commit()
    conn.close()

    return redirect(url_for('login'))

  return render_template('register.html')


# 3. Processing Login
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    email = request.form.get('email')
    password = request.form.get('password')

    conn = get_db_connection()
    user = conn.execute(
       'SELECT * FROM user WHERE email = ?', (email,)
       ).fetchone()
    conn.close()

    # Check users and password
    if user and check_password_hash(user['password'], password):
      user_obj = User(
         id=user['id'], 
         email=user['email'], 
         password=user['password']
         )
      login_user(user_obj)
      return redirect(url_for('home'))
    else:
      return 'Invalid email or password!'

  return render_template('login.html')

# 4. Forgot Password
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        return f'Sent password reset instructions to email: {email}'
    return render_template('forgot_password.html')

# 5. Log out
@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('home'))

# TheMealDB API: https://www.themealdb.com/api.php
@app.route('/recipes', methods=['GET'])
def search_recipes():
    keyword = request.args.get('keyword', '').strip()   # 🌟 Đã sửa lấy từ GET
    diet_filter = request.args.get('diet', '').strip()  # Gluten-Free, Vegan, Dairy-Free...
    prep_filter = request.args.get('prep', '').strip()  # minimal, standard, complex
    type_filter = request.args.get('type', '').strip()  # quick, standard, detailed
    category_filter = request.args.get('category', '').strip()
    page = int(request.args.get('page', 1))              # Supports "Load More"
    limit = 15

    # Lấy số lượng món tương ứng với trang hiện tại
    fetch_limit = page * limit
    offset = 0

    conn = get_db_connection()
    total_count = 0

    # 1) Filter directly using SQL based on keyword and dietary_tags
    if keyword:
        if diet_filter and diet_filter.lower() != 'all':
            total_count = conn.execute('''
                SELECT COUNT(*) FROM recipe_cache 
                WHERE name LIKE ? AND dietary_tags LIKE ?
            ''', (f'%{keyword}%', f'%{diet_filter}%')).fetchone()[0]

            query = '''SELECT raw_data, dietary_tags 
                    FROM recipe_cache 
                    WHERE name LIKE ? 
                    AND dietary_tags LIKE ? 
                    LIMIT ? OFFSET ?'''
            rows = conn.execute(query, (f'%{keyword}%', f'%{diet_filter}%', fetch_limit + 1, offset)).fetchall()
        else:
            total_count = conn.execute('''
                SELECT COUNT(*) FROM recipe_cache WHERE name LIKE ?
            ''', (f'%{keyword}%',)).fetchone()[0]

            query = '''SELECT raw_data, dietary_tags  
                    FROM recipe_cache 
                    WHERE name LIKE ? 
                    LIMIT ? OFFSET ?'''
            rows = conn.execute(query, (f'%{keyword}%', fetch_limit + 1, offset)).fetchall()

    elif category_filter:
        if diet_filter and diet_filter.lower() != 'all':
            total_count = conn.execute('''
                SELECT COUNT(*) FROM recipe_cache 
                WHERE category = ? AND dietary_tags LIKE ?
            ''', (category_filter, f'%{diet_filter}%')).fetchone()[0]

            query = '''SELECT raw_data, dietary_tags 
                    FROM recipe_cache 
                    WHERE category = ? AND dietary_tags LIKE ? 
                    LIMIT ? OFFSET ?'''
            rows = conn.execute(query, (category_filter, f'%{diet_filter}%', fetch_limit + 1, offset)).fetchall()
        else:
            total_count = conn.execute('''
                SELECT COUNT(*) FROM recipe_cache WHERE category = ?
            ''', (category_filter,)).fetchone()[0]

            query = '''SELECT raw_data, dietary_tags
                    FROM recipe_cache 
                    WHERE category = ? 
                    LIMIT ? OFFSET ?'''
            rows = conn.execute(query, (category_filter, fetch_limit + 1, offset)).fetchall()

    elif diet_filter and diet_filter.lower() != 'all':
        total_count = conn.execute('''
            SELECT COUNT(*) FROM recipe_cache WHERE dietary_tags LIKE ?
        ''', (f'%{diet_filter}%',)).fetchone()[0]

        query = '''SELECT raw_data, dietary_tags  
                FROM recipe_cache 
                WHERE dietary_tags LIKE ? 
                LIMIT ? OFFSET ?'''
        rows = conn.execute(query, (f'%{diet_filter}%', fetch_limit + 1, offset)).fetchall()

    else:
        total_count = conn.execute('SELECT COUNT(*) FROM recipe_cache').fetchone()[0]
        rows = conn.execute('''
            SELECT raw_data, dietary_tags 
            FROM recipe_cache 
            LIMIT ? OFFSET ?''', (fetch_limit + 1, offset)).fetchall()

    conn.close()

    # 2) Read out the data and assign secondary labels
    has_more = len(rows) > fetch_limit
    display_rows = rows[:fetch_limit]
    meals = []

    for row in display_rows:
        meal = json.loads(row['raw_data'])
        cook_label = get_cooking_label(meal.get('strInstructions', ''))
        prep_label = get_prep_label(meal)

        diet_tags_str = row['dietary_tags'] if 'dietary_tags' in row.keys() and row['dietary_tags'] else ''
        meal['diet_labels'] = diet_tags_str.split(',') if diet_tags_str else []

        # Prep Filter
        if prep_filter == 'minimal' and prep_label != 'Easy to prepare': continue
        if prep_filter == 'standard' and prep_label != 'Standard to prepare': continue
        if prep_filter == 'complex' and prep_label != 'Hard to prepare': continue

        # Type Filter
        if type_filter == 'quick' and cook_label != 'Quick and Easy': continue
        if type_filter == 'standard' and cook_label != 'Standard Cooking': continue
        if type_filter == 'detailed' and cook_label != 'Home cooked Special (Longer Recipe)': continue

        meal['cook_label'] = cook_label
        meal['prep_label'] = prep_label
        meals.append(meal)

    countries = get_countries_from_db()

    return render_template(
        'recipes.html', 
        meals=meals, 
        countries=countries, 
        selected_diet=diet_filter,
        page=page,
        has_more=has_more,
        total_count=total_count
    )

# Route to display details of a specific dish based on its ID.
@app.route('/recipe/<meal_id>')
def recipe_detail(meal_id):
    try:
        # Call TheMealDB API to fetch details by meal ID
        conn = get_db_connection()
        row = conn.execute('SELECT raw_data FROM recipe_cache WHERE meal_id = ?', (meal_id,)).fetchone()
        conn.close()
        
        if not row:
            return redirect(url_for('search_recipes'))

        meal = json.loads(row['raw_data'])

        # 1) Process ingredients first
        ingredients = []
        for i in range(1, 21):
            ingredient = meal.get(f'strIngredient{i}')
            measure = meal.get(f'strMeasure{i}')
            if ingredient and ingredient.strip():
                ingredients.append({
                    'name': ingredient.strip(),
                    'measure': measure.strip() if measure else ''
                })

        # 2) Process instructions OUTSIDE of the ingredient loop
        raw_instructions = meal.get('strInstructions', '')
        lines = raw_instructions.split('\r\n') if '\r\n' in raw_instructions else raw_instructions.split('\n')
        cleaned_steps = []
        pro_tips = []
        is_tip_section = False

        for line in lines:
            text = line.strip()
            if not text:
                continue

            if re.match(r'^(pro\s*tips?:?|notes?:?|tips?:?)$', text, re.IGNORECASE):
                is_tip_section = True
                continue

            if is_tip_section:
                cleaned_tip = re.sub(r'^[\*\-\d\.]+\s*', '', text).strip()
                if cleaned_tip:
                    pro_tips.append(cleaned_tip)
                continue

            if re.match(r'^(step\s*\d+:?|\d+\.?)$', text, re.IGNORECASE):
                continue

            text = re.sub(r'^(step\s*\d+:?|\d+[\.\)]\s*)', '', text, flags=re.IGNORECASE).strip()
            if text:
                cleaned_steps.append(text)

        cook_label = get_cooking_label(cleaned_steps)
        prep_label = get_prep_label(ingredients)

        return render_template(
            'recipeDetails.html', 
            meal=meal, 
            ingredients=ingredients, 
            instructions=cleaned_steps, 
            pro_tips=pro_tips,
            cook_label=cook_label,
            prep_label=prep_label
        )
    except Exception as e:
        print(f"Error fetching recipe details: {e}")

    return redirect(url_for('search_recipes'))


# 4. Route Country read from SQLite local
@app.route('/recipes/flag')
def recipes_by_flag():
    selected_area = request.args.get('area', 'Canadian').strip()
    page = int(request.args.get('page', 1))
    limit = 15
    fetch_limit = page * limit
    offset = 0
    meals = []

    countries = get_countries_from_db()
    country_info = countries.get(selected_area, {})
    search_name = country_info.get('name', selected_area)

    try:
        conn = get_db_connection()
        # Take 15 recipes of each country from CSDL local
        if selected_area.lower() == 'international':
            total_count = conn.execute('''
                SELECT COUNT(*) FROM recipe_cache 
                WHERE area IS NULL OR area = '' OR area = 'Unknown' OR area = 'International'
            ''').fetchone()[0]

            rows = conn.execute('''
                SELECT raw_data, dietary_tags FROM recipe_cache 
                WHERE area IS NULL OR area = '' OR area = 'Unknown' OR area = 'International'
                LIMIT ? OFFSET ?
            ''', (fetch_limit + 1, offset)).fetchall()
        else:
            total_count = conn.execute('''
                SELECT COUNT(*) FROM recipe_cache 
                WHERE area LIKE ? OR area LIKE ?
            ''', (f'%{selected_area}%', f'%{search_name}%')).fetchone()[0]

            rows = conn.execute('''
                SELECT raw_data, dietary_tags FROM recipe_cache
                WHERE area LIKE ? OR area LIKE ?
                LIMIT ? OFFSET ?
            ''', (f'%{selected_area}%', f'%{search_name}%', fetch_limit + 1, offset)).fetchall()
            
        conn.close()

        # 🌟 Đã sửa: dùng fetch_limit để kiểm tra và cắt dữ liệu cho nút Load More
        has_more = len(rows) > fetch_limit
        display_rows = rows[:fetch_limit]

        for row in display_rows:
            meal_data = json.loads(row['raw_data'])
            raw_instructions = meal_data.get('strInstructions', '')
            meal_data['cook_label'] = get_cooking_label(raw_instructions)
            meal_data['prep_label'] = get_prep_label(meal_data)
            meals.append(meal_data)
    except Exception as e:
        print(f"Error fetching area meals from DB: {e}")
        has_more = False
        total_count = 0


    return render_template('recipesFlag.html', 
                           meals=meals, 
                           countries=countries, 
                           selected_area=selected_area,
                           page=page,
                           has_more=has_more,
                           total_count=total_count)


# 5. Dietary Profile
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():

    restrictions_list = [
        'Gluten-Free',
        'Dairy-Free',
        'Vegan',
        'Vegetarian',
        'Nut-Free',
        'Soy-Free',
        'Halal',
        'Kosher',
        'Low-Sodium'
    ]

    conn = get_db_connection()

    if request.method == 'POST':

        # Get personal information
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()

        # Get dietary information
        selected = request.form.getlist('restrictions')
        selected = [r for r in selected if r in restrictions_list]

        restrictions_string = ','.join(selected)

        ingredients_to_avoid = request.form.get(
            'ingredients_to_avoid', ''
        ).strip()

        dietary_notes = request.form.get(
            'dietary_notes', ''
        ).strip()

        # Update the user's personal information
        conn.execute('''
            UPDATE user
            SET first_name = ?, last_name = ?
            WHERE id = ?
        ''', (first_name, last_name, current_user.id))

        # Save or update dietary information
        conn.execute('''
            INSERT INTO dietary_profile (
                user_id,
                restrictions,
                ingredients_to_avoid,
                dietary_notes
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                restrictions = excluded.restrictions,
                ingredients_to_avoid = excluded.ingredients_to_avoid,
                dietary_notes = excluded.dietary_notes

        ''', (
            current_user.id,
            restrictions_string,
            ingredients_to_avoid,
            dietary_notes
        ))

        conn.commit()
        conn.close()

        flash('Your profile has been updated successfully!', 'success')

        return redirect(url_for('profile'))

    # Retrieve personal information
    user = conn.execute('''
        SELECT first_name, last_name, email
        FROM user
        WHERE id = ?
    ''', (current_user.id,)).fetchone()

    # Retrieve dietary information
    saved_profile = conn.execute('''
        SELECT restrictions, ingredients_to_avoid, dietary_notes
        FROM dietary_profile
        WHERE user_id = ?
    ''', (current_user.id,)).fetchone()

    conn.close()

    selected_restrictions = []
    ingredients_to_avoid = ''
    dietary_notes = ''

    if saved_profile:
        if saved_profile['restrictions']:
            selected_restrictions = saved_profile['restrictions'].split(',')

        ingredients_to_avoid = saved_profile['ingredients_to_avoid'] or ''
        dietary_notes = saved_profile['dietary_notes'] or ''

    return render_template(
        'profile.html',
        restrictions_list=restrictions_list,
        selected_restrictions=selected_restrictions,
        first_name=user['first_name'] if user else '',
        last_name=user['last_name'] if user else '',
        email=user['email'] if user else '',
        ingredients_to_avoid=ingredients_to_avoid,
        dietary_notes=dietary_notes
    )

@app.route('/diet-guide')
def diet_guide():
    diet_info = {}
    diet_ingredients = {}

    # Read the information of each diet
    info_path = os.path.join(app.static_folder, 'diet_info.json')
    if os.path.exists(info_path):
        with open(info_path, 'r', encoding='utf-8') as f:
            diet_info = json.load(f)

    # Read list of ingredient
    ingredients_path = os.path.join(app.static_folder, 'diet_ingredients.json')
    if os.path.exists(ingredients_path):
        with open(ingredients_path, 'r', encoding='utf-8') as f:
            diet_ingredients = json.load(f)

    return render_template('dietGuide.html', diet_info=diet_info, diet_ingredients=diet_ingredients)

# Watch all ingredeient for each Diet Meals
@app.route('/diet-ingredients/<diet_name>')
def diet_ingredients_detail(diet_name):
    diet_ingredients = {}

    # Read file JSON:
    ingredients_path = os.path.join(app.static_folder, 'diet_ingredients.json')
    if os.path.exists(ingredients_path):
        with open(ingredients_path, 'r', encoding='utf-8') as f:
            diet_ingredients = json.load(f)

    # Take list of Diet 
    ingredients_list = diet_ingredients.get(diet_name, [])

    return render_template(
        'dietIngredients.html', 
        diet_name=diet_name, 
        ingredients=ingredients_list
    )

if __name__ == '__main__':
    init_db()  # Automatically run the database initialization when the application launches
    app.run(debug=True)