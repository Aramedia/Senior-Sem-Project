import sqlite3
from urllib import response
import random
import re
from flask import Flask, flash, redirect, render_template, request, url_for
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

#  take all the recipes ịn the library
def get_filtered_meals_fast_from_api(prep_filter, type_filter, target_count = 15):
    """Quickly find items that meet the filter criteria by randomly scanning through a few characters, stopping as soon as 15 items have been collected from TheMealDB API."""
    filtered_meals = []
    seen_ids = set()

    # 1) Randomly shuffle the 26 letters of the alphabet
    letters = list('abcdefghijklmnopqrstuvwxyz')
    random.shuffle(letters)

    for letter in letters:
        try:
            res = requests.get(f'https://www.themealdb.com/api/json/v1/1/search.php?f={letter}')
            raw_meals = res.json().get('meals') or []
            
            for meal in raw_meals:
                meal_id = meal.get('idMeal')
                if not meal_id or meal_id in seen_ids:
                    continue
                
                # Count for each meals
                raw_instructions = meal.get('strInstructions', '')
                cook_label = get_cooking_label(raw_instructions)
                prep_label = get_prep_label(meal)

                # Check the number of ingredient
                if prep_filter == 'minimal' and prep_label != 'Easy to prepare':
                    continue
                if prep_filter == 'standard' and prep_label != 'Standard to prepare':
                    continue
                if prep_filter == 'complex' and prep_label != 'Hard to prepare':
                    continue

                # Check base on Recipes Instruction
                if type_filter == 'quick' and cook_label != 'Quick and Easy':
                    continue
                if type_filter == 'standard' and cook_label != 'Standard Cooking':
                    continue
                if type_filter == 'detailed' and cook_label != 'Home cooked Special (Longer Recipe)':
                    continue

                # Assign labels and add valid items
                meal['cook_label'] = cook_label
                meal['prep_label'] = prep_label
                seen_ids.add(meal_id)
                filtered_meals.append(meal)

                # Stop when enough 15 meals
                if len(filtered_meals) >= target_count:
                    return filtered_meals

        except Exception as e:
            print(f"Error fetching letter {letter}: {e}")
            
    return filtered_meals

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


# Main route for the home page

# 1. main.html
@app.route('/')
def home():
  recipes = []
  try:
    # Call API of TheMealDB to get 8 random recipes
    raw_recipes = get_random_letter_meals(8)

    # Transfer data to main.html
    for meal in raw_recipes:
        raw_tags = meal.get('strTags')
        tags_list = raw_tags.split(',') if raw_tags else [meal.get('strCategory', 'SAFE')]

        raw_instructions = meal.get('strInstructions', '')
        cook_label = get_cooking_label(raw_instructions)
        prep_label = get_prep_label(meal)
        
        recipes.append ({
                'id': meal.get('idMeal'),
                'name': meal.get('strMeal'),
                'category': meal.get('strCategory'),
                'area': meal.get('strArea'),
                'image': meal.get('strMealThumb'),
                'cooktime': cook_label,
                'prep_label': prep_label,
                'tags': tags_list
            })
  except Exception as e:
    print(f"Error fetching recipes: {e}")
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
@app.route('/recipes', methods=['GET', 'POST'])
def search_recipes():
    # 1) Take filter data from URL
    prep_filter = request.args.get('prep', '').strip() # easy, standard or hard to prepare
    type_filter = request.args.get('type', '').strip() # quick, stard, detail(long) recipes
    category_filter = request.args.get('category','').strip()

    # If use the filter for prepare and type
    if (prep_filter or type_filter) and request.method == 'GET':
        meals = get_filtered_meals_fast_from_api(prep_filter, type_filter, target_count=15)
        return render_template('recipes.html', meals=meals)
    
    meals = []

    # 2) Take the original data
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            try:
                res = requests.get(f'https://www.themealdb.com/api/json/v1/1/search.php?s={keyword}')
                meals = res.json().get('meals') or []
            except Exception as e:
                print(f"Error searching: {e}")
        else:
            meals = get_random_letter_meals(15)
    elif category_filter:
        try:
            res = requests.get(f'https://www.themealdb.com/api/json/v1/1/filter.php?c={category_filter}')
            meals = res.json().get('meals') or []
        except Exception as e:
            print(f"Error category: {e}")
    else:
        meals = get_random_letter_meals(15)

    for meal in meals:
        raw_instructions = meal.get('strInstructions', '')
        meal['cook_label'] = get_cooking_label(raw_instructions)
        meal['prep_label'] = get_prep_label(meal)

    return render_template('recipes.html', meals = meals[:15])


# Supports retrieving multiple random, non-duplicate dishes.
def get_random_letter_meals(count=15):
    meals_pool = []

    letters = list('abcdefghijklmnopqrstuvwxyz')
    random.shuffle(letters)  # Shuffle letters to ensure randomness

    try:
        for letter in letters:
            response = requests.get(f'https://www.themealdb.com/api/json/v1/1/search.php?s={letter}')
            data = response.json()
            raw_meals = data.get('meals') or []
            
            # Add unique meals to the pool
            for meal in raw_meals:
                if meal not in meals_pool:
                    if not any(m['idMeal'] == meal['idMeal'] for m in meals_pool):          
                        meals_pool.append(meal)
            # Have we collected enough meals? If yes, break the loop.
            if len(meals_pool) >= count:
                break
            
        return meals_pool[:count]
    except Exception as e:
        print(f"Error fetching initial recipes: {e}")
        return []

# Route to display details of a specific dish based on its ID.
@app.route('/recipe/<meal_id>')
def recipe_detail(meal_id):
    try:
        # Call TheMealDB API to fetch details by meal ID
        response = requests.get(f'https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}')
        data = response.json()
        meals = data.get('meals')
        
        if meals:
            meal = meals[0]
            
            # Automatically split the list of ingredients and their quantities
            ingredients = []
            for i in range(1, 21):
                ingredient = meal.get(f'strIngredient{i}')
                measure = meal.get(f'strMeasure{i}')
                if ingredient and ingredient.strip():
                    ingredients.append({
                        'name': ingredient.strip(),
                        'measure': measure.strip() if measure else ''
                    })
            # Correctly format the instructions recipes
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
                
                # if in the Pro Tips section, summary all in the pro_tips
                if is_tip_section:
                    #  Delete "-", "*", "1.", if have, in the first of the line, and keep the rest of the text.
                    cleaned_tip = re.sub(r'^[\*\-\d\.]+\s*', '', text).strip()
                    if cleaned_tip:
                        pro_tips.append(cleaned_tip)
                    continue

                # Pass the number: "1", "2", "STEP 1", "STEP 2:")
                if re.match(r'^(step\s*\d+:?|\d+\.?)$', text, re.IGNORECASE):
                    continue
                
                # Delete "STEP 1:", "1.", "Step 2" in the first of the line, and keep the rest of the text.
                text = re.sub(r'^(step\s*\d+:?|\d+[\.\)]\s*)', '', text, flags=re.IGNORECASE).strip()
                
                if text:
                    cleaned_steps.append(text)  

            # Determine the cooking label based on the instructions
            cook_label = get_cooking_label(cleaned_steps)
            prep_label = get_prep_label(ingredients)

            return render_template('recipeDetails.html', 
                                   meal=meal, 
                                   ingredients=ingredients, 
                                   instructions=cleaned_steps, 
                                   pro_tips=pro_tips,
                                   cook_label=cook_label,
                                   prep_label=prep_label)
    except Exception as e:
        print(f"Error fetching recipe details: {e}")

    return redirect(url_for('search_recipes'))

# Flag of TheMealDB
COUNTRY_FLAGS = {
    'American': {'code': 'US', 'flag': '🇺🇸', 'name': 'American'},
    'British': {'code': 'GB', 'flag': '🇬🇧', 'name': 'British'},
    'Canadian': {'code': 'CA', 'flag': '🇨🇦', 'name': 'Canadian'},
    'Chinese': {'code': 'CN', 'flag': '🇨🇳', 'name': 'Chinese'},
    'Croatian': {'code': 'HR', 'flag': '🇭🇷', 'name': 'Croatian'},
    'Dutch': {'code': 'NL', 'flag': '🇳🇱', 'name': 'Dutch'},
    'Egyptian': {'code': 'EG', 'flag': '🇪🇬', 'name': 'Egyptian'},
    'Filipino': {'code': 'PH', 'flag': '🇵🇭', 'name': 'Filipino'},
    'French': {'code': 'FR', 'flag': '🇫🇷', 'name': 'French'},
    'Greek': {'code': 'GR', 'flag': '🇬🇷', 'name': 'Greek'},
    'Indian': {'code': 'IN', 'flag': '🇮🇳', 'name': 'Indian'},
    'Irish': {'code': 'IE', 'flag': '🇮🇪', 'name': 'Irish'},
    'Italian': {'code': 'IT', 'flag': '🇮🇹', 'name': 'Italian'},
    'Jamaican': {'code': 'JM', 'flag': '🇯🇲', 'name': 'Jamaican'},
    'Japanese': {'code': 'JP', 'flag': '🇯🇵', 'name': 'Japanese'},
    'Kenyan': {'code': 'KE', 'flag': '🇰🇪', 'name': 'Kenyan'},
    'Malaysian': {'code': 'MY', 'flag': '🇲🇾', 'name': 'Malaysian'},
    'Mexican': {'code': 'MX', 'flag': '🇲🇽', 'name': 'Mexican'},
    'Moroccan': {'code': 'MA', 'flag': '🇲🇦', 'name': 'Moroccan'},
    'Polish': {'code': 'PL', 'flag': '🇵🇱', 'name': 'Polish'},
    'Portuguese': {'code': 'PT', 'flag': '🇵🇹', 'name': 'Portuguese'},
    'Russian': {'code': 'RU', 'flag': '🇷🇺', 'name': 'Russian'},
    'Spanish': {'code': 'ES', 'flag': '🇪🇸', 'name': 'Spanish'},
    'Thai': {'code': 'TH', 'flag': '🇹🇭', 'name': 'Thai'},
    'Tunisian': {'code': 'TN', 'flag': '🇹🇳', 'name': 'Tunisian'},
    'Turkish': {'code': 'TR', 'flag': '🇹🇷', 'name': 'Turkish'},
    'Vietnamese': {'code': 'VN', 'flag': '🇻🇳', 'name': 'Vietnamese'}
}

@app.route('/recipes/flag')
def recipes_by_flag():
    selected_area = request.args.get('area', 'Vietnamese').strip()
    meals = []
    
    try:
        res = requests.get(f'https://www.themealdb.com/api/json/v1/1/filter.php?a={selected_area}')
        raw_meals = res.json().get('meals') or []
        # Take 15 recipes
        for m in raw_meals[:15]:
            detail_res = requests.get(f'https://www.themealdb.com/api/json/v1/1/lookup.php?i={m["idMeal"]}')
            meal_data = detail_res.json().get('meals', [{}])[0]
            
            # Gán thông tin nhãn giống như bên search_recipes
            raw_instructions = meal_data.get('strInstructions', '')
            meal_data['cook_label'] = get_cooking_label(raw_instructions)
            meal_data['prep_label'] = get_prep_label(meal_data)
            
            meals.append(meal_data)
    except Exception as e:
        print(f"Error fetching area meals: {e}")
# 6. Dietary Profile
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

        # Get the restrictions selected by the user
        selected = request.form.getlist('restrictions')

        # Only accept restrictions from our approved list
        selected = [r for r in selected if r in restrictions_list]

        # Convert the list into a string for SQLite
        restrictions_string = ','.join(selected)

        # Save or update the user's dietary profile
        conn.execute('''
            INSERT INTO dietary_profile (user_id, restrictions)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET restrictions = excluded.restrictions
        ''', (current_user.id, restrictions_string))

        conn.commit()
        conn.close()

        flash('Your dietary profile has been saved!', 'success')

        return redirect(url_for('home'))
    
    # Retrieve the user's saved restrictions
    saved_profile = conn.execute(
        'SELECT restrictions FROM dietary_profile WHERE user_id = ?',
        (current_user.id,)
    ).fetchone()

    conn.close()

    selected_restrictions = []

    if saved_profile and saved_profile['restrictions']:
        selected_restrictions = saved_profile['restrictions'].split(',')

    return render_template(
        'profile.html',
        restrictions_list=restrictions_list,
        selected_restrictions=selected_restrictions
    )



    return render_template(
        'recipesFlag.html', 
        meals=meals[:15], 
        countries=COUNTRY_FLAGS, 
        selected_area=selected_area
    )
if __name__ == '__main__':
    init_db()  # Automatically run the database initialization when the application launches
    app.run(debug=True)

