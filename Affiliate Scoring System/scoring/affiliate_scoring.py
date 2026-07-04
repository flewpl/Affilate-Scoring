
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import get_connection


def load_affiliates() -> pd.DataFrame:
    connection = get_connection()
    try:
        return pd.read_sql("SELECT * FROM affiliates", connection)
    finally:
        connection.close()



BENCHMARKS = {
    "SEO": {
        "reg_rate": {
            "dir": "high_is_bad",
            "yellow": 0.09,
            "red":    0.14,
        },
        "ftd_rate": {
            "dir": "high_is_bad",
            "yellow": 0.42,
            "red":    0.55,
        },
        "ngr_per_ftd": {
            "dir": "low_is_bad",
            "yellow": 90,
            "red":    40,
        },
        "retention_30d": {
            "dir": "low_is_bad",
            "yellow": 0.40,
            "red":    0.25,
        },
        "_min_sample": {
            "clicks": 1000,
            "registrations": 50,
            "ftd_count": 15,
        }
    },

    "PPC": {
        "reg_rate": {
            "dir": "high_is_bad",
            "yellow": 0.06,
            "red":    0.06,  
        },
        "ftd_rate": {
            "dir": "high_is_bad",
            "yellow": 0.32,
            "red":    0.45,
        },
        "ngr_per_ftd": {
            "dir": "low_is_bad",
            "yellow": 45,
            "red":    20,
        },
        "retention_30d": {
            "dir": "low_is_bad",
            "yellow": 0.22,
            "red":    0.12,
        },
        "_min_sample": {
            "clicks": 3000,
            "registrations": 60,
            "ftd_count": 12,
        }
    },

    "Streamer": {
        "reg_rate": {
            "dir": "high_is_bad",
            "yellow": 0.14,
            "red":    0.22,
        },
        "ftd_rate": {
            "dir": "high_is_bad",
            "yellow": 0.58,
            "red":    0.70,
        },
        "ngr_per_ftd": {
            "dir": "low_is_bad",
            "yellow": 65,
            "red":    30,
        },
        "retention_30d": {
            "dir": "low_is_bad",
            "yellow": 0.33,
            "red":    0.18,
        },
        "_min_sample": {
            "clicks": 500,
            "registrations": 40,
            "ftd_count": 15,
        }
    },

    "Email": {
        "reg_rate": {
            "dir": "high_is_bad",
            "yellow": 0.07,
            "red":    0.12,
        },
        "ftd_rate": {
            "dir": "high_is_bad",
            "yellow": 0.40,
            "red":    0.52,
        },
        "ngr_per_ftd": {
            "dir": "low_is_bad",
            "yellow": 55,
            "red":    25,
        },
        "retention_30d": {
            "dir": "low_is_bad",
            "yellow": 0.30,
            "red":    0.18,
        },
        "_min_sample": {
            "clicks": 800,
            "registrations": 40,
            "ftd_count": 12,
        }
    },
}


METRIC_WEIGHTS = {
    "ngr_per_ftd":    0.40,
    "retention_30d":  0.30,
    "ftd_rate":       0.20,
    "reg_rate":       0.10,
}

FLAG_SCORE = {
    " Green":  1.0,
    " Yellow": 0.5,
    " Red":    0.0,
}

def check_data(row):
    """Validates if the affiliate has enough traffic for a reliable score."""
    profile_name = row.get("profile_name")

    if profile_name not in BENCHMARKS:
        return "OK"
    profile = BENCHMARKS[row["profile_name"]]["_min_sample"]

    if row["clicks"] < profile["clicks"]:
        return "Insufficient data: clicks"
    if row["registrations"] < profile["registrations"]:
        return "Insufficient data: registrations"
    if row["ftd_count"] < profile["ftd_count"]:
        return "Insufficient data: ftd_count"
    return "OK"

def evaluate_partners(row):
    profile_name = row.get("profile_name")

    # 1. Catch fraud / unknown categories
    if profile_name not in BENCHMARKS:
        return {
            "status": "Banned / Fraud Category",
            "flags": {
                "reg_rate": " Red",
                "ftd_rate": " Red",
                "ngr_per_ftd": " Red",
                "retention_30d": " Red"
            },
            "final_score": 0.0,
            "final_status": " Red"  # overall red status
        }
        
    # 2. Check minimum sample size
    status = check_data(row)
    if status != "OK":
        return {
            "status": status, 
            "flags": {}, 
            "final_score": None,
            "final_status": " Not Enough Data" # not enough data to score
        }
    
    # 3. Compute per-metric flags and the final score
    profile = BENCHMARKS[profile_name]
    flags = {}
    total_score = 0.0

    for metric, thresholds in profile.items():
        if metric.startswith("_"):
            continue

        value = row.get(metric, 0)
        direction = thresholds["dir"]
        metric_flag = ""

        if direction == "high_is_bad":
            if value >= thresholds["red"]:
                metric_flag = " Red"
            elif value >= thresholds["yellow"]:
                metric_flag = " Yellow"
            else:
                metric_flag = " Green"

        elif direction == "low_is_bad":
            if value <= thresholds["red"]:
                metric_flag = " Red"
            elif value <= thresholds["yellow"]:
                metric_flag = " Yellow"
            else:
                metric_flag = " Green"
                
        flags[metric] = metric_flag
        
        # add this metric's contribution to the total score
        weight = METRIC_WEIGHTS.get(metric, 0)
        score_multiplier = FLAG_SCORE.get(metric_flag, 0)
        total_score += weight * score_multiplier

    # 4. Derive the final color from total_score
    if total_score >= 0.75:
        final_color = " Green"
    elif total_score >= 0.40:
        final_color = " Yellow"
    else:
        final_color = " Red"

    return {
        "status": "Evaluated",
        "flags": flags,
        "final_score": round(total_score, 2),
        "final_status": final_color
    }


    







if __name__ == "__main__":
    data = load_affiliates()
    result = evaluate_partners(data.iloc[1])
    print(result)
