import sys
from pathlib import Path

from faker import Faker
import random

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import get_connection

Faker.seed(42)
fake = Faker()
# connection for log in to database — credentials come from .env, see config.py
connection = get_connection()
OUTPUT_DIR = Path(__file__).resolve().parent
cursor = connection.cursor()


#cleaning tables
cursor.execute("""DROP TABLE IF EXISTS affiliates""");

# table 1 - profile templates
cursor.execute("""
CREATE TABLE IF NOT EXISTS affiliate_templates (
    profile_name VARCHAR(50),
    clicks_min INT,
    clicks_max INT,
    reg_rate_min FLOAT,
    reg_rate_max FLOAT,
    ftd_rate_min FLOAT,
    ftd_rate_max FLOAT,
    ngr_per_ftd_min INT,
    ngr_per_ftd_max INT,
    retention_30d_min FLOAT,
    retention_30d_max FLOAT,
    weight FLOAT
);
""")

# table 2 - the affiliates themselves
cursor.execute("""
CREATE TABLE IF NOT EXISTS affiliates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100),
    profile_name    VARCHAR(50),
    clicks          INT,
    registrations   INT,
    ftd_count       INT,
    reg_rate        FLOAT,
    ftd_rate        FLOAT,
    ngr_per_ftd     FLOAT,
    total_ngr       FLOAT,
    retention_30d   FLOAT
);
""")



AFFILIATE_PROFILES = {
    'SEO': {
        'clicks':       (3000, 40000),
        'reg_rate':     (0.04, 0.09),
        'ftd_rate':     (0.28, 0.42),
        'ngr_per_ftd':  (90, 220),
        'retention_30d':(0.42, 0.68),
        'weight': 0.35      # 35% of affiliates
    },
    'PPC': {
        'clicks':       (15000, 120000),  # lots of traffic
        'reg_rate':     (0.015, 0.035),   # but low conversion
        'ftd_rate':     (0.18, 0.32),
        'ngr_per_ftd':  (45, 110),
        'retention_30d':(0.22, 0.42),
        'weight': 0.25
    },
    'Streamer': {
        'clicks':       (500, 8000),      # low traffic
        'reg_rate':     (0.06, 0.14),     # but high conversion
        'ftd_rate':     (0.35, 0.55),
        'ngr_per_ftd':  (70, 160),
        'retention_30d':(0.35, 0.58),
        'weight': 0.15
    },
    'Email': {
        'clicks':       (1000, 12000),
        'reg_rate':     (0.03, 0.07),
        'ftd_rate':     (0.22, 0.38),
        'ngr_per_ftd':  (55, 130),
        'retention_30d':(0.30, 0.52),
        'weight': 0.15
    },
    'Fraud': {
        'clicks':       (500, 4000),
        'reg_rate':     (0.18, 0.45),     # abnormally high
        'ftd_rate':     (0.55, 0.92),     # main red flag
        'ngr_per_ftd':  (3, 18),          # players don't actually play
        'retention_30d':(0.01, 0.07),     # nobody sticks around
        'weight': 0.10
    }
}
 

insert_query_profiles = """
INSERT INTO affiliate_templates(profile_name, clicks_min, clicks_max, reg_rate_min, reg_rate_max, ftd_rate_min, ftd_rate_max, ngr_per_ftd_min, ngr_per_ftd_max, retention_30d_min, retention_30d_max, weight)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

insert_query_affiliate = """
INSERT INTO affiliates(name, profile_name, clicks, registrations, ftd_count, reg_rate, ftd_rate, ngr_per_ftd, total_ngr, retention_30d)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""



for name, metric in AFFILIATE_PROFILES.items():
    cursor.execute(insert_query_profiles, (
        name,
        metric['clicks'][0], metric['clicks'][1],
        metric['reg_rate'][0], metric['reg_rate'][1],
        metric['ftd_rate'][0], metric['ftd_rate'][1],
        metric['ngr_per_ftd'][0], metric['ngr_per_ftd'][1],
        metric['retention_30d'][0], metric['retention_30d'][1],
        metric['weight']
    ))

connection.commit()
print("template table has been filled up")


for name, metric in AFFILIATE_PROFILES.items():
    for _ in range(int(metric['weight'] * 1000)):  # generate 1000 affiliates weighted by profile
        clicks = random.randint(*metric['clicks'])
        reg_rate = random.uniform(*metric['reg_rate'])
        registrations = int(clicks * reg_rate)
        ftd_rate = random.uniform(*metric['ftd_rate'])
        ftd_count = int(registrations * ftd_rate)
        ngr_per_ftd = random.uniform(*metric['ngr_per_ftd'])
        total_ngr = ftd_count * ngr_per_ftd
        retention_30d = random.uniform(*metric['retention_30d']) 



        cursor.execute(insert_query_affiliate, (
            fake.company(),
            name,
            clicks,
            registrations,
            ftd_count,
            round(reg_rate, 4),
            round(ftd_rate, 4),
            round(ngr_per_ftd, 2),
            round(total_ngr, 2),
            round(retention_30d, 4)
        ))

connection.commit()
print("affiliates table has been filled up")



    

