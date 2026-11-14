import itertools
import json
import os
import random
import re
import sqlite3

SEED = 0
random.seed(SEED)
os.makedirs("data", exist_ok=True)
DB = "data/business.db"

CITIES = ["Chennai", "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Pune",
          "Kolkata", "Ahmedabad", "Jaipur", "Kochi", "Coimbatore", "Lucknow"]
SEGMENTS = ["Retail", "Corporate", "Startup"]
STATUSES = ["Delivered", "Shipped", "Cancelled", "Pending"]
CATEGORIES = {
    "Electronics": ["Phone", "Laptop", "Tablet", "Speaker", "Camera", "Monitor"],
    "Furniture": ["Desk", "Chair", "Shelf", "Sofa", "Cabinet", "Table"],
    "Clothing": ["Jacket", "Shirt", "Jeans", "Dress", "Scarf", "Shoes"],
    "Grocery": ["Rice", "Tea", "Coffee", "Spices", "Oil", "Lentils"],
    "Sports": ["Bat", "Racket", "Ball", "Helmet", "Mat", "Gloves"],
}
ADJ = ["Pro", "Mini", "Max", "Lite", "Plus", "Classic"]
FIRST = ["Asha", "Ravi", "Meena", "Karthik", "Divya", "Arjun", "Lakshmi", "Sanjay",
         "Priya", "Vikram", "Nisha", "Rahul", "Anita", "Suresh", "Kavya", "Manoj",
         "Pooja", "Gautam", "Rekha", "Dinesh"]
LAST = ["Kumar", "Iyer", "Reddy", "Nair", "Sharma", "Patel", "Menon", "Das", "Singh", "Rao"]

SCHEMA = (
    "Database schema (SQLite):\n"
    "customers(id, name, city, segment, signup_date)\n"
    "products(id, name, category, price)\n"
    "orders(id, customer_id, order_date, status)\n"
    "order_items(id, order_id, product_id, quantity)\n"
    "Write one SQLite SELECT query inside a ```sql block."
)

if os.path.exists(DB):
    os.remove(DB)
con = sqlite3.connect(DB)
con.executescript("""
CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT, segment TEXT, signup_date TEXT);
CREATE TABLE products(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price INTEGER);
CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT);
CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER);
""")


def rand_date(y0, y1):
    y = random.randint(y0, y1)
    return f"{y}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"


names = set()
while len(names) < 60:
    names.add(f"{random.choice(FIRST)} {random.choice(LAST)}")
names = sorted(names)
random.shuffle(names)
for i, n in enumerate(names, 1):
    con.execute("INSERT INTO customers VALUES (?,?,?,?,?)",
                (i, n, random.choice(CITIES), random.choice(SEGMENTS), rand_date(2021, 2023)))

prod_rows = []
pid = 1
prices = random.sample(range(100, 5000), 30)
for cat, nouns in CATEGORIES.items():
    for noun in nouns:
        prod_rows.append((pid, f"{noun} {random.choice(ADJ)}", cat, prices[pid - 1]))
        pid += 1
seen_names = set()
for r in prod_rows:
    nm = r[1]
    while nm in seen_names:
        nm = f"{r[1].split()[0]} {random.choice(ADJ)} {random.randint(2, 9)}"
    seen_names.add(nm)
    con.execute("INSERT INTO products VALUES (?,?,?,?)", (r[0], nm, r[2], r[3]))

buyers = random.sample(range(1, 61), 48)
sellable = random.sample(range(1, 31), 25)
oid = iid = 1
for _ in range(400):
    con.execute("INSERT INTO orders VALUES (?,?,?,?)",
                (oid, random.choice(buyers), rand_date(2023, 2025), random.choice(STATUSES)))
    for p in random.sample(sellable, random.randint(1, 4)):
        con.execute("INSERT INTO order_items VALUES (?,?,?,?)", (iid, oid, p, random.randint(1, 5)))
        iid += 1
    oid += 1
con.commit()

PRODUCT_NAMES = [r[0] for r in con.execute("SELECT name FROM products").fetchall()]
CUSTOMER_NAMES = [r[0] for r in con.execute("SELECT name FROM customers").fetchall()]

T = [
    ("T01", "How many customers live in {city}?",
     "SELECT COUNT(*) FROM customers WHERE city='{city}'", {"city": CITIES}, False),
    ("T02", "List the names of customers in the {segment} segment.",
     "SELECT name FROM customers WHERE segment='{segment}'", {"segment": SEGMENTS}, False),
    ("T03", "How many orders have status '{status}'?",
     "SELECT COUNT(*) FROM orders WHERE status='{status}'", {"status": STATUSES}, False),
    ("T04", "What is the average price of products in the {category} category?",
     "SELECT AVG(price) FROM products WHERE category='{category}'", {"category": list(CATEGORIES)}, False),
    ("T05", "List products in the {category} category priced above {price}.",
     "SELECT name FROM products WHERE category='{category}' AND price>{price}",
     {"category": list(CATEGORIES), "price": [500, 1500, 2500]}, False),
    ("T06", "How many distinct customers have an order with status '{status}'?",
     "SELECT COUNT(DISTINCT customer_id) FROM orders WHERE status='{status}'", {"status": STATUSES}, False),
    ("T07", "What is the total quantity sold of the product '{product}'?",
     "SELECT SUM(oi.quantity) FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE p.name='{product}'",
     {"product": PRODUCT_NAMES}, False),
    ("T08", "What is the total revenue from {category} products?",
     "SELECT SUM(oi.quantity*p.price) FROM order_items oi JOIN products p ON p.id=oi.product_id "
     "WHERE p.category='{category}'", {"category": list(CATEGORIES)}, False),
    ("T09", "Which customers in {city} have placed at least one order? List their names.",
     "SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id=c.id WHERE c.city='{city}'",
     {"city": CITIES}, False),
    ("T10", "How many orders were placed in {year}?",
     "SELECT COUNT(*) FROM orders WHERE strftime('%Y', order_date)='{year}'",
     {"year": ["2023", "2024", "2025"]}, False),
    ("T11", "What is the total revenue in {year}?",
     "SELECT SUM(oi.quantity*p.price) FROM orders o JOIN order_items oi ON oi.order_id=o.id "
     "JOIN products p ON p.id=oi.product_id WHERE strftime('%Y', o.order_date)='{year}'",
     {"year": ["2023", "2024", "2025"]}, False),
    ("T13", "Which {n} products have the highest price? List their names.",
     "SELECT name FROM products ORDER BY price DESC LIMIT {n}", {"n": [3, 5, 7]}, False),
    ("T14", "List the cities that have more than {k} customers.",
     "SELECT city FROM customers GROUP BY city HAVING COUNT(*)>{k}", {"k": [3, 4, 5]}, False),
    ("T19", "How many orders did the customer '{customer}' place?",
     "SELECT COUNT(*) FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.name='{customer}'",
     {"customer": CUSTOMER_NAMES}, False),
    ("T20", "What is the total quantity of items ordered by customers in {city}?",
     "SELECT SUM(oi.quantity) FROM customers c JOIN orders o ON o.customer_id=c.id "
     "JOIN order_items oi ON oi.order_id=o.id WHERE c.city='{city}'", {"city": CITIES}, False),
    ("T21", "List customers in {city} who are in the {segment} segment.",
     "SELECT name FROM customers WHERE city='{city}' AND segment='{segment}'",
     {"city": CITIES, "segment": SEGMENTS}, False),
    ("T22", "How many products cost less than {price}?",
     "SELECT COUNT(*) FROM products WHERE price<{price}", {"price": [500, 1000, 2000, 3000, 4000]}, False),
    ("T23", "How many orders with status '{status}' were placed in {year}?",
     "SELECT COUNT(*) FROM orders WHERE status='{status}' AND strftime('%Y', order_date)='{year}'",
     {"status": STATUSES, "year": ["2023", "2024", "2025"]}, False),
    ("T12", "How many orders did each customer in {city} place? Show name and count.",
     "SELECT c.name, COUNT(o.id) FROM customers c LEFT JOIN orders o ON o.customer_id=c.id "
     "WHERE c.city='{city}' GROUP BY c.id", {"city": CITIES}, True),
    ("T15", "How many customers have never placed an order?",
     "SELECT COUNT(*) FROM customers WHERE id NOT IN (SELECT customer_id FROM orders)", {}, True),
    ("T17", "List the {category} products that have never been ordered.",
     "SELECT name FROM products WHERE category='{category}' AND id NOT IN (SELECT product_id FROM order_items)",
     {"category": list(CATEGORIES)}, True),
    ("T18", "Which customer has spent the most in total? Give the name.",
     "SELECT c.name FROM customers c JOIN orders o ON o.customer_id=c.id JOIN order_items oi ON oi.order_id=o.id "
     "JOIN products p ON p.id=oi.product_id GROUP BY c.id ORDER BY SUM(oi.quantity*p.price) DESC, c.id LIMIT 1",
     {}, True),
]


def run(sql):
    return con.execute(sql).fetchall()


def trivial(rows):
    return (not rows) or rows in ([(0,)], [(None,)])


iid_pairs, novel_pairs = [], []
for tid, q, sql, params, novel in T:
    keys = list(params)
    combos = itertools.product(*[params[k] for k in keys]) if keys else [()]
    for combo in combos:
        kw = dict(zip(keys, combo))
        question, gold = q.format(**kw), sql.format(**kw)
        if trivial(run(gold)):
            continue
        rec = {"template_id": tid, "question": question, "gold_sql": gold,
               "prompt": f"{SCHEMA}\nQuestion: {question}"}
        (novel_pairs if novel else iid_pairs).append(rec)

random.shuffle(iid_pairs)
cut = int(len(iid_pairs) * 0.75)
train, test_iid = iid_pairs[:cut], iid_pairs[cut:]


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


train_q = {norm(r["question"]) for r in train}
train_sql = {norm(r["gold_sql"]) for r in train}
leak = {
    "train_size": len(train), "test_iid_size": len(test_iid), "test_novel_size": len(novel_pairs),
    "exact_question_overlap_iid": sum(norm(r["question"]) in train_q for r in test_iid),
    "exact_sql_overlap_iid": sum(norm(r["gold_sql"]) in train_sql for r in test_iid),
    "exact_question_overlap_novel": sum(norm(r["question"]) in train_q for r in novel_pairs),
    "exact_sql_overlap_novel": sum(norm(r["gold_sql"]) in train_sql for r in novel_pairs),
    "template_overlap_novel": len({r["template_id"] for r in novel_pairs} & {r["template_id"] for r in train}),
    "method": "exact match on whitespace-normalised, lower-cased question and gold SQL; template-id overlap",
}
assert leak["exact_question_overlap_iid"] == 0 and leak["exact_question_overlap_novel"] == 0, "LEAK"
assert leak["template_overlap_novel"] == 0, "LEAK: novel template appears in train"

for name, rows in [("train", train), ("test_iid", test_iid), ("test_novel", novel_pairs)]:
    with open(f"data/{name}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
with open("data/leak_report.json", "w") as f:
    json.dump(leak, f, indent=2)
print(json.dumps(leak, indent=2))
