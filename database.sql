PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS available_countries_view;
DROP VIEW IF EXISTS safe_products;
DROP VIEW IF EXISTS establishments_for_user;
DROP VIEW IF EXISTS safe_recipes;
DROP VIEW IF EXISTS user_dietary_restrictions_view;

DROP TABLE IF EXISTS store_products;
DROP TABLE IF EXISTS establishment_accommodations;
DROP TABLE IF EXISTS establishments;
DROP TABLE IF EXISTS product_tags;
DROP TABLE IF EXISTS product_dietary_restrictions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS brands;
DROP TABLE IF EXISTS user_saved_recipes;
DROP TABLE IF EXISTS recipe_ingredients;
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS ingredient_dietary_restrictions;
DROP TABLE IF EXISTS ingredients;
DROP TABLE IF EXISTS user_dietary_restrictions;
DROP TABLE IF EXISTS dietary_restrictions;
DROP TABLE IF EXISTS users;

-- user table
CREATE TABLE users ( 
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL UNIQUE,
    user_password_hash TEXT NOT NULL,   
    display_name TEXT,
    zip_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
); 

-- dietary restrictions table
CREATE TABLE dietary_restrictions (
    restriction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    restriction_name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL CHECK (category IN ('allergy', 'medical', 'lifestyle', 'other'))  
);

-- table that links user to dietary restcrictions
CREATE TABLE user_dietary_restrictions (
    user_id INTEGER NOT NULL,
    restriction_id INTEGER NOT NULL,
    severity TEXT NOT NULL DEFAULT 'moderate' CHECK (severity IN ('mild', 'moderate', 'severe')),
    PRIMARY KEY (user_id, restriction_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (restriction_id) REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE
);

-- ingredients table
CREATE TABLE ingredients (
    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL CHECK (category IN ('vegetable', 'fruit', 'grain', 'protein', 'dairy', 'spice', 'other'))
);

-- table that links ingredients to dietary restrictions
CREATE TABLE ingredient_dietary_restrictions (
    ingredient_id INTEGER NOT NULL,
    restriction_id INTEGER NOT NULL,
    PRIMARY KEY (ingredient_id, restriction_id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id) ON DELETE CASCADE,
    FOREIGN KEY (restriction_id) REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE
);

-- recipe table
CREATE TABLE recipes (
    recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_name TEXT NOT NULL,
    instructions TEXT NOT NULL,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_url TEXT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- table that links recipes to ingredients
CREATE TABLE recipe_ingredients (
    recipe_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantity TEXT NOT NULL,
    PRIMARY KEY (recipe_id, ingredient_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id) ON DELETE CASCADE
);

-- table for saved recipes by users
CREATE TABLE user_saved_recipes (
    user_id INTEGER NOT NULL,
    recipe_id INTEGER NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, recipe_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE
);

-- brands table
CREATE TABLE brands (
    brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name TEXT NOT NULL UNIQUE,
    website_url TEXT
);

-- products table
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    brand_id INTEGER,
    ingredients TEXT NOT NULL,
    nutrition_facts TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id) ON DELETE SET NULL
);

-- table that links products to dietary restrictions
CREATE TABLE product_dietary_restrictions (
    product_id INTEGER NOT NULL,
    restriction_id INTEGER NOT NULL,
    PRIMARY KEY (product_id, restriction_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (restriction_id) REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE
); 

-- table that tag products are suitable for specific dietary restrictions
CREATE TABLE product_tags (
    product_id INTEGER NOT NULL,
    restriction_id INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'label' CHECK (source IN ('label', 'manufacturer', 'third-party')),
    may_contain_traces INTEGER NOT NULL DEFAULT 0 CHECK (may_contain_traces IN (0, 1)),
    verified_at TEXT,
    PRIMARY KEY (product_id, restriction_id, source),
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (restriction_id) REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE
);

-- restaurant/grocery store table
CREATE TABLE establishments (
    establishment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    establishment_name TEXT NOT NULL,
    establishment_type TEXT NOT NULL CHECK (establishment_type IN ('restaurant', 'grocery store', 'other')),
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip_code TEXT NOT NULL,
    phone_number TEXT,
    website_url TEXT
);  

-- establishments accommodations for dietary restrictions
CREATE TABLE establishment_accommodations (
    establishment_id INTEGER NOT NULL,
    restriction_id INTEGER NOT NULL,
    support_level TEXT NOT NULL DEFAULT 'options' CHECK (support_level IN ('dedicated', 'options', 'can_modify', 'not_supported')),
    source TEXT NOT NULL CHECK (source IN ('menu', 'staff', 'website', 'other')),
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (establishment_id, restriction_id),
    FOREIGN KEY (establishment_id) REFERENCES establishments(establishment_id) ON DELETE CASCADE,
    FOREIGN KEY (restriction_id) REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE
);

 -- table for which products a store carries
CREATE TABLE store_products (
    establishment_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    PRIMARY KEY (establishment_id, product_id),
    FOREIGN KEY (establishment_id) REFERENCES establishments(establishment_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- indexes for faster lookups
CREATE INDEX idx_recipe_ingredients_ing ON recipe_ingredients(ingredient_id); 
CREATE INDEX idx_ing_diet_restr ON ingredient_dietary_restrictions(restriction_id); 
CREATE INDEX idx_user_diet_restr ON user_dietary_restrictions(restriction_id);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_prod_diet_restr ON product_dietary_restrictions(restriction_id);
CREATE INDEX idx_establishment_loc ON establishments(establishment_type, city, state, zip_code);
CREATE INDEX idx_est_accommodations ON establishment_accommodations(restriction_id);

-- views for easier access to data

-- user dietary restrictions view
CREATE VIEW user_dietary_restrictions_view AS
WITH RECURSIVE expanded(user_id, restriction_id, severity) AS (
    SELECT user_id, restriction_id, restriction_name, severity
    FROM user_dietary_restrictions udr
    UNION
    SELECT e.user_id, dr.restriction_id, dr.restriction_name, e.severity
    FROM expanded e
    JOIN user_dietary_restrictions udr ON u.user_id = udr.user_id
    JOIN dietary_restrictions dr ON udr.restriction_id = dr.restriction_id
)
SELECT user_id, restriction_id, MIN(severity) AS severity
FROM expanded
GROUP BY user_id, restriction_id;

-- recipes that are safe for users based on their dietary restrictions
CREATE VIEW safe_recipes AS
SELECT u.user_id, r.recipe_id, r.recipe_name
FROM users u
CROSS JOIN recipes r
WHERE NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredient_dietary_restrictions idr ON ri.ingredient_id = idr.ingredient_id
    JOIN user_dietary_restrictions udr ON idr.restriction_id = udr.restriction_id
    WHERE u.user_id = udr.user_id AND r.recipe_id = ri.recipe_id
)
AND NOT EXISTS (
    SELECT 1
    FROM recipe_ingredients ri
    JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
    WHERE ri.recipe_id = r.recipe_id
);

-- establishments that accommodate users based on their dietary restrictions
CREATE VIEW establishments_for_user AS
SELECT ur_count.user_id, e.establishment_id, e.establishment_name, e.establishment_type, e.address, e.city, e.state, e.zip_code
FROM establishments e
JOIN (
    SELECT user_id, COUNT(*) AS needed
    FROM user_dietary_restrictions udr
    GROUP BY user_id
) ur_count
WHERE (
    SELECT COUNT(DISTINCT ea.restriction_id)
    FROM establishment_accommodations ea
    JOIN user_dietary_restrictions udr ON ea.restriction_id = udr.restriction_id
    WHERE ea.establishment_id = e.establishment_id AND udr.user_id = ur_count.user_id
) = ur_count.needed; 


-- products that are safe for users based on their dietary restrictions
CREATE VIEW safe_products AS
SELECT ur_count.user_id, p.product_id, p.product_name, p.brand_id AS brands
FROM products p
JOIN brands b ON b.brand_id = p.brand_id
JOIN (
    SELECT user_id, COUNT(*) AS needed
    FROM user_dietary_restrictions udr
    GROUP BY user_id
) ur_count 
WHERE NOT EXISTS (
    SELECT COUNT(DISTINCT pt.restriction_id)
    FROM product_tags pt
    JOIN user_dietary_restrictions udr ON pt.restriction_id = udr.restriction_id
    WHERE p.product_id = pt.product_id AND ur_count.user_id = udr.user_id
) = ur_count.needed;

-- View that retrieves a list of countries that actually have dishes (including 'International')CREATE VIEW IF NOT EXISTS available_countries_view AS
CREATE VIEW available_countries_view AS
SELECT DISTINCT 
    a.area_name, 
    a.country_name, 
    a.country_code, 
    a.flag_url
FROM areas_cache a
INNER JOIN recipe_cache r ON (
    r.area = a.area_name 
    OR (a.area_name = 'International' AND (r.area IS NULL OR r.area = '' OR r.area = 'Unknown' OR r.area = 'International'))
)
ORDER BY CASE WHEN a.area_name = 'International' THEN 1 ELSE 0 END, a.country_name ASC;


-- STARTER DATA

INSERT INTO dietary_restrictions (restriction_name, category) VALUES
('Gluten-Free', 'allergy'),
('Nut-Free', 'allergy'),
('Dairy-Free', 'allergy'),
('Vegan', 'lifestyle'),
('Vegetarian', 'lifestyle'),
('Pescatarian', 'lifestyle'),
('Keto', 'lifestyle'),
('Paleo', 'lifestyle'),
('Low-Sodium', 'medical'),
('Low-Sugar', 'medical');

INSERT INTO ingredients (ingredient_name, category) VALUES
('Chicken', 'protein'),
('Beef', 'protein'),
('Pork', 'protein'),
('Tofu', 'protein'),
('Lentils', 'protein'),
('Rice', 'grain'),
('Quinoa', 'grain'),
('Wheat', 'grain'),
('Almonds', 'protein'),
('Milk', 'dairy'),
('Cheese', 'dairy'),
('Eggs', 'protein'),
('Broccoli', 'vegetable'),
('Spinach', 'vegetable'),
('Carrots', 'vegetable'),
('Apples', 'fruit'),
('Bananas', 'fruit'),
('Strawberries', 'fruit');

