import sqlite3
import requests
import json

DB_NAME = 'safeplate.db'

AREA_ISO_MAP = {
    'Afghan': 'af', 'Albanian': 'al', 'Algerian': 'dz', 'American': 'us', 'Andorran': 'ad',
    'Angolan': 'ao', 'Antiguan, Barbudan': 'ag', 'Argentine': 'ar', 'Armenian': 'am',
    'Aruban': 'aw', 'Australian': 'au', 'Austrian': 'at', 'Azerbaijani': 'az', 'Bahamian': 'bs',
    'Bahraini': 'bh', 'Bangladeshi': 'bd', 'Barbadian': 'bb', 'Belarusian': 'by', 'Belgian': 'be',
    'Belizean': 'bz', 'Beninese': 'bj', 'Bermudian': 'bm', 'Bhutanese': 'bt', 'Bolivian': 'bo',
    'Bosnian, Herzegovinian': 'ba', 'Motswana': 'bw', 'Brazilian': 'br', 'British': 'gb',
    'Bruneian': 'bn', 'Bulgarian': 'bg', 'Burkinabe': 'bf', 'Burundian': 'bi', 'Cabo Verdean': 'cv',
    'Cambodian': 'kh', 'Cameroonian': 'cm', 'Canadian': 'ca', 'Central African': 'cf', 'Chadian': 'td',
    'Chilean': 'cl', 'Chinese': 'cn', 'Colombian': 'co', 'Comorian': 'km', 'Congolese': 'cg',
    'Costa Rican': 'cr', 'Croatian': 'hr', 'Cuban': 'cu', 'Cypriot': 'cy', 'Czech': 'cz',
    'Danish': 'dk', 'Djiboutian': 'dj', 'Dominican': 'do', 'Dutch': 'nl', 'Ecuadorean': 'ec',
    'Egyptian': 'eg', 'Salvadoran': 'sv', 'Equatorial Guinean': 'gq', 'Eritrean': 'er', 'Estonian': 'ee',
    'Ethiopian': 'et', 'Fijian': 'fj', 'Finnish': 'fi', 'French': 'fr', 'Gabonese': 'ga',
    'Gambian': 'gm', 'Georgian': 'ge', 'German': 'de', 'Ghanaian': 'gh', 'Greek': 'gr',
    'Grenadian': 'gd', 'Guatemalan': 'gt', 'Guinean': 'gn', 'Guyanese': 'gy', 'Haitian': 'ht',
    'Honduran': 'hn', 'Hungarian': 'hu', 'Icelandic': 'is', 'Indian': 'in', 'Indonesian': 'id',
    'Iranian': 'ir', 'Iraqi': 'iq', 'Irish': 'ie', 'Israeli': 'il', 'Italian': 'it',
    'Ivorian': 'ci', 'Jamaican': 'jm', 'Japanese': 'jp', 'Jordanian': 'jo', 'Kazakhstani': 'kz',
    'Kenyan': 'ke', 'Kuwaiti': 'kw', 'Kyrgyz': 'kg', 'Lao': 'la', 'Latvian': 'lv',
    'Lebanese': 'lb', 'Liberian': 'lr', 'Libyan': 'ly', 'Lithuanian': 'lt', 'Luxembourgish': 'lu',
    'Malagasy': 'mg', 'Malawian': 'mw', 'Malaysian': 'my', 'Maldivian': 'mv', 'Malian': 'ml',
    'Maltese': 'mt', 'Mauritanian': 'mr', 'Mauritian': 'mu', 'Mexican': 'mx', 'Moldovan': 'md',
    'Monacan': 'mc', 'Mongolian': 'mn', 'Montenegrin': 'me', 'Moroccan': 'ma', 'Mozambican': 'mz',
    'Namibian': 'na', 'Nepalese': 'np', 'New Zealander': 'nz', 'Nicaraguan': 'ni', 'Nigerian': 'ng',
    'Norwegian': 'no', 'Omani': 'om', 'Pakistani': 'pk', 'Panamanian': 'pa', 'Papua New Guinean': 'pg',
    'Paraguayan': 'py', 'Peruvian': 'pe', 'Filipino': 'ph', 'Polish': 'pl', 'Portuguese': 'pt',
    'Qatari': 'qa', 'Romanian': 'ro', 'Russian': 'ru', 'Rwandan': 'rw', 'Saint Lucian': 'lc',
    'Samoan': 'ws', 'Saudi Arabian': 'sa', 'Senegalese': 'sn', 'Serbian': 'rs', 'Seychellois': 'sc',
    'Sierra Leonean': 'sl', 'Singaporean': 'sg', 'Slovak': 'sk', 'Slovenian': 'si', 'Somali': 'so',
    'South African': 'za', 'South Korean': 'kr', 'Spanish': 'es', 'Sri Lankan': 'lk', 'Sudanese': 'sd',
    'Surinamese': 'sr', 'Swedish': 'se', 'Swiss': 'ch', 'Syrian': 'sy', 'Tajik': 'tj',
    'Tanzanian': 'tz', 'Thai': 'th', 'Togolese': 'tg', 'Tongan': 'to', 'Trinidadian': 'tt',
    'Tunisian': 'tn', 'Turkish': 'tr', 'Turkmen': 'tm', 'Ugandan': 'ug', 'Ukrainian': 'ua',
    'Uruguayan': 'uy', 'Uzbek': 'uz', 'Venezuelan': 've', 'Vietnamese': 'vn', 'Yemeni': 'ye',
    'Zambian': 'zm', 'Zimbabwean': 'zw'
}

def init_all_tables(conn):
    """Create all cache tables in SQLite if they do not exist."""
    # 1. Recipes Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS recipe_cache (
            meal_id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            area TEXT,
            image TEXT,
            instructions TEXT,
            raw_data TEXT
        )
    ''')

    # 2. Ingredients Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ingredients_cache (
            ingredient_id TEXT PRIMARY KEY,
            name TEXT UNIQUE,
            description TEXT,
            type TEXT,
            image_url TEXT
        )
    ''')

    # 3. Categories Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categories_cache (
            category_id TEXT PRIMARY KEY,
            name TEXT UNIQUE,
            thumbnail TEXT,
            description TEXT
        )
    ''')

    # 4. Areas / Countries Table - XÓA BẢNG CŨ ĐỂ TẠO LẠI CẤU TRÚC MỚI
    conn.execute('DROP TABLE IF EXISTS areas_cache')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS areas_cache (
            area_name TEXT PRIMARY KEY,
            country_name TEXT,
            country_code TEXT,
            flag_url TEXT
        )
    ''')

    conn.commit()


def seed_database():
    conn = sqlite3.connect(DB_NAME)
    init_all_tables(conn)

    print(" Starting COMPLETE DATABASE SEEDING from TheMealDB API...\n")

    # STEP 1: Download All Recipes (A to Z)
    print(" [1/4] Fetching all Meals (alphabet a-z)...")
    letters = 'abcdefghijklmnopqrstuvwxyz'
    meal_count = 0

    for letter in letters:
        try:
            res = requests.get(f'https://www.themealdb.com/api/json/v1/1/search.php?f={letter}')
            meals = res.json().get('meals') or []
            
            for meal in meals:
                meal_id = meal.get('idMeal')
                conn.execute('''
                    INSERT OR REPLACE INTO recipe_cache (meal_id, name, category, area, image, instructions, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    meal_id,
                    meal.get('strMeal'),
                    meal.get('strCategory'),
                    meal.get('strArea'),
                    meal.get('strMealThumb'),
                    meal.get('strInstructions'),
                    json.dumps(meal)
                ))
                meal_count += 1
            
            conn.commit()
            print(f"   Saved meals starting with '{letter}'...")
        except Exception as e:
            print(f"   Error fetching letter '{letter}': {e}")

    print(f" Total Meals Saved: {meal_count}\n")

    # STEP 2: Download All Ingredients List
    print(" [2/4] Fetching full Ingredients database...")
    try:
        res = requests.get('https://www.themealdb.com/api/json/v1/1/list.php?i=list')
        ingredients = res.json().get('meals') or []
        
        for ing in ingredients:
            ing_name = ing.get('strIngredient')
            # Generate HD image URL for ingredients
            img_url = f"https://www.themealdb.com/images/ingredients/{ing_name}.png" if ing_name else ""

            conn.execute('''
                INSERT OR REPLACE INTO ingredients_cache (ingredient_id, name, description, type, image_url)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                ing.get('idIngredient'),
                ing_name,
                ing.get('strDescription'),
                ing.get('strType'),
                img_url
            ))
        
        conn.commit()
        print(f" Total Ingredients Saved: {len(ingredients)}\n")
    except Exception as e:
        print(f" Error fetching ingredients: {e}\n")

    # STEP 3: Download All Categories with Details
    print(" [3/4] Fetching Categories with descriptions...")
    try:
        res = requests.get('https://www.themealdb.com/api/json/v1/1/categories.php')
        categories = res.json().get('categories') or []
        
        for cat in categories:
            conn.execute('''
                INSERT OR REPLACE INTO categories_cache (category_id, name, thumbnail, description)
                VALUES (?, ?, ?, ?)
            ''', (
                cat.get('idCategory'),
                cat.get('strCategory'),
                cat.get('strCategoryThumb'),
                cat.get('strCategoryDescription')
            ))
        
        conn.commit()
        print(f" Total Categories Saved: {len(categories)}\n")
    except Exception as e:
        print(f" Error fetching categories: {e}\n")

    # STEP 4: Download Country Areas List & Add International
    print("📌 [4/4] Fetching Country / Areas list...")
    try:
        res = requests.get('https://www.themealdb.com/api/json/v1/1/list.php?a=list')
        areas = res.json().get('meals') or []
        
        # 1. Add each country from API
        for area in areas:
            area_name = area.get('strArea')
            country_name = area.get('strCountry') or area_name
            code = AREA_ISO_MAP.get(area_name, 'un')
            flag_url = f"https://flagcdn.com/w80/{code.lower()}.png"

            conn.execute('''
                INSERT OR REPLACE INTO areas_cache (area_name, country_name, country_code, flag_url)
                VALUES (?, ?, ?, ?)
            ''', (
                area_name,
                country_name,
                code.upper(),
                flag_url
            ))

        # 2. Add International group 
        conn.execute('''
            INSERT OR REPLACE INTO areas_cache (area_name, country_name, country_code, flag_url)
            VALUES (?, ?, ?, ?)
        ''', ('International', 'International', 'UN', 'https://flagcdn.com/w80/un.png'))

        conn.commit()
        print(f" Total Areas Saved: {len(areas) + 1}\n")
    except Exception as e:
        print(f" Error fetching areas: {e}\n")

    conn.close()
    print(" SUCCESS! ALL API DATA HAS BEEN DOWNLOADED & SAVED TO SAFEPLATE.DB!")

if __name__ == '__main__':
    seed_database()