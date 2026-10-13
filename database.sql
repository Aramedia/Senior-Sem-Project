PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS users;

-- user table
CREATE TABLE users ( 
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL UNIQUE,
    user_password_hash VARCHAR(255) NOT NULL,   
    display_name VARCHAR(255) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);  

-- dietary restrictions table
CREATE TABLE dietary_restrictions (
    restriction_id INT AUTO_INCREMENT PRIMARY KEY,
    restriction_name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(255) NOT NULL CHECK (category IN ('allergy', 'medical', 'lifestyle', 'other'))  
);

-- table that links user to dietary restcrictions
CREATE TABLE user_dietary_restrictions (
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    restriction_id INT REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE,
    severity VARCHAR(255) NOT NULL CHECK severity IN ('mild', 'moderate', 'severe')),
    PRIMARY KEY (user_id, restriction_id)
    FOREIGN KEY (user_email) REFERENCES users(user_email) ON DELETE CASCADE,
    FOREIGN KEY (restriction_id) REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE
);

-- ingredients table
CREATE TABLE ingredients (
    ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
    ingredient_name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(255) NOT NULL CHECK (category IN ('vegetable', 'fruit', 'grain', 'protein', 'dairy', 'spice', 'other'))
);

-- table that links ingredients to dietary restrictions
CREATE TABLE ingredient_dietary_restrictions (
    ingredient_id INT REFERENCES ingredients(ingredient_id) ON DELETE CASCADE,
    restriction_id INT REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE,
    PRIMARY KEY (ingredient_id, restriction_id)
);

-- recipe table
CREATE TABLE recipes (
    recipe_id INT AUTO_INCREMENT PRIMARY KEY,
    recipe_name VARCHAR(255) NOT NULL,
    instructions TEXT NOT NULL,
    created_by INT REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    source_url VARCHAR(255)
);

-- table that links recipes to ingredients
CREATE TABLE recipe_ingredients (
    recipe_id INT REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    ingredient_id INT REFERENCES ingredients(ingredient_id) ON DELETE CASCADE,
    quantity VARCHAR(255) NOT NULL,
    PRIMARY KEY (recipe_id, ingredient_id)
);  

-- table for saved recipes by users
CREATE TABLE user_saved_recipes (
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recipe_id INT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, recipe_id)
);

-- brands table
CREATE TABLE brands (
    brand_id INT AUTO_INCREMENT PRIMARY KEY,
    brand_name VARCHAR(255) NOT NULL UNIQUE,
    website_url VARCHAR(255)
);  

-- products table
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    brand_id INT REFERENCES brands(brand_id) ON DELETE SET NULL,
    ingredients TEXT NOT NULL,
    nutrition_facts TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- table that links products to dietary restrictions
CREATE TABLE product_dietary_restrictions (
    product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
    restriction_id INT REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE,
    PRIMARY KEY (product_id, restriction_id)
);  

-- table that tag products are suitable for specific dietary restrictions
CREATE TABLE product_tags (
    product_id INT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    restriction_id INT NOT NULL REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL 'label' CHECK (source IN ('label', 'manufacturer', 'third-party')),
    may_contain_traces INT NOT NULL DEFAULT 0 CHECK (may_contain_traces IN (0, 1)),
    verified_at VARCHAR(255),
    PRIMARY KEY (product_id, restriction_id, source)
);

-- restaurant/grocery store table
CREATE TABLE establishments (
    establishment_id INT AUTO_INCREMENT PRIMARY KEY,
    establishment_name VARCHAR(255) NOT NULL,
    establishment_type VARCHAR(255) NOT NULL CHECK (establishment_type IN ('restaurant', 'grocery store', 'other')),
    address VARCHAR(255) NOT NULL,
    city VARCHAR(255) NOT NULL,
    state VARCHAR(255) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    phone_number VARCHAR(20),
    website_url VARCHAR(255)
);  

-- establishments accommodations for dietary restrictions
CREATE TABLE establishment_accommodations (
    establishment_id INT NOT NULLREFERENCES establishments(establishment_id) ON DELETE CASCADE,
    restriction_id INT NOT NULL REFERENCES dietary_restrictions(restriction_id) ON DELETE CASCADE,
    support_level VARCHAR(255) NOT NULL DEFAULT 'options'
    CHECK (support_level IN ('dedicated', 'options', 'can_modify', 'not_supported')),
    source VARCHAR(255) NOT NULL CHECK (source IN ('menu', 'staff', 'website', 'other')),
    verified_at TIMESTAMP,
    PRIMARY KEY (establishment_id, restriction_id)
);
 -- table for which products a store carries
 CREATE TABLE store_products (
    establishment_id INT NOT NULL REFERENCES establishments(establishment_id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    PRIMARY KEY (establishment_id, product_id)
);

-- indexes for faster lookups
CREATE INDEX idx_recipe_name ON recipes_ingredients(ingredient_id); 
CREATE INDEX idx_ing_viol_restriction ON ingredient_violations(restriction_id); 
CREATE INDEX idx_user_restr_restr ON user_restrictions(restriction_id);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_psf_restriction ON product_dietary_restrictions(restriction_id);
CREATE INDEX idx_establishment_type_loc ON establishments(establishment_type, city, state, zip_code);
CREATE INDEX idx_pa_restriction ON establishment_accommodations(restriction_id);

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

