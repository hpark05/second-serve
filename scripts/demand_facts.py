"""Curated demand-side facts. Each row cites a saved source slug (see SOURCES in scrape_volume.py)
and a verbatim quote that scrape_volume.py checks against the saved page text.

VOLUME_FACTS: (hall, metric, value, unit, period, source_slug, notes, quote)
HALL_FACTS:   (hall, attribute, value, source_slug, notes, quote)
"""

ALL = "All Cal Dining"
DC = "All four dining commons"

VOLUME_FACTS = [
    # --- per-hall daily headcount (official Cal Dining hall pages, current site) ---
    ("Crossroads", "students_served_per_day", "4400", "students/day", "current site copy (pulled 2026-10-27; undated)", "crossroads",
     "Official hall page. Likely a rounded marketing figure, not a measured count.", "welcomes 4,400 students through its doors every day"),
    ("Café 3", "students_served_per_day", "2500", "students/day (lower bound)", "current site copy (pulled 2026-10-27; undated)", "cafe_3",
     "Official hall page says 'over 2,500'.", "loves serving over 2,500 students daily"),
    ("Clark Kerr", "students_served_per_day", "1200", "students/day (approx.)", "current site copy (pulled 2026-10-27; undated)", "clark_kerr",
     "Official hall page says 'about 1,200'.", "serves about 1,200 students every day"),
    # Foothill: no figure on current page (page body empty) -> gap, documented in docs/sources-demand.md
    # --- system-wide volume ---
    (ALL, "meal_plan_holders", "12000", "meal plan holders (lower bound)", "2026 (job posting dated 2026-08)", "job_posting_insidehighered_88071",
     "Boilerplate in a UC Berkeley Dining job posting; 'more than 12,000'. Includes off-campus and voluntary plans.", "With more than 12,000 meal plan holders"),
    (ALL, "meals_served_per_year", "5000000", "meals/year (lower bound)", "2026 (job posting dated 2026-08)", "job_posting_insidehighered_88071",
     "Across 14 facilities incl. retail, training table, early childhood, catering. Not dining commons only.", "serves over 5 million meals per year in 14 facilities"),
    (ALL, "operating_days_hours", "7 days/week, 17 hours/day", "schedule", "2026", "job_posting_insidehighered_88071", "",
     "services the campus seven days per week, seventeen hours per day"),
    (ALL, "staff", "450 staff + ~400 student workers", "people", "2026", "job_posting_insidehighered_88071", "",
     "employing 450 full and part-time staff and approximately 400 Cal student workers"),
    (DC, "meals_served_per_day", "10000", "meals/day (lower bound)", "undated (StopWaste case study, LeanPath era c. 2012-2014)", "stopwaste_cal_dining",
     "Four residential dining halls. Publication date not shown on page.", "Cal Dining serves over 10,000 meals each day to UC Berkeley students and faculty at four residential dining halls on campus"),
    (DC, "meals_served_per_day", "8000", "meals/day", "2004", "ucb_news_2004_green", "Historic; dining halls only.", "dining halls, which serve 8,000 meals a day"),
    (ALL, "students_living_on_campus", "6750", "students", "2015 (FoodService Director, 2015-01-08)", "fsd_beyond_50_berkeley", "Dated; housing has grown by 2,400+ beds since 2018.",
     "No. of Students Living on Campus: 6,750"),
    (ALL, "meal_plans_sold", "10104", "meal plans", "2015 (FoodService Director, 2015-01-08)", "fsd_beyond_50_berkeley", "", "No. of Meal Plans Sold: 10,104"),
    (ALL, "annual_dining_revenue", "59.5", "USD millions", "2015 (FoodService Director, 2015-01-08)", "fsd_beyond_50_berkeley", "", "Annual Dining Program Revenues: $59.5 million"),
    (ALL, "meals_served_per_year", "4000000", "meals/year", "2008 (FoodService Director, 2008-05-01)", "fsd_shawn_lapean", "Historic.", "ANNUAL MEALS SERVED: 4 million"),
    (ALL, "people_served_per_day", "28000", "people/day (approx.)", "2019 (Spoon University, 2019-11-01)", "spoon_behind_the_scenes",
     "Student publication; whole operation incl. retail. Low reliability.", "serving food to about 28,000 people every day"),
    ("Café 3", "chicken_breast_per_day", "200", "lb/day (avg)", "2019 (Spoon University, 2019-11-01)", "spoon_behind_the_scenes", "Student publication; useful production-scale anchor.",
     "serves an average of 200 pounds of chicken breast per day and 100 pounds of salad per meal"),
    # --- Crossroads historic ---
    ("Crossroads", "seats", "800", "seats", "2003 (opening press release)", "ucb_news_2003_crossroads_release", "Other source (FSD 2008) says 850 seats.", "Crossroads can seat 800 people at a time"),
    ("Crossroads", "seats", "850", "seats", "2008 (FoodService Director, 2008-05-01)", "fsd_shawn_lapean", "Conflicts with 800 in 2003 release.", "850-seat Crossroads dining facility"),
    ("Crossroads", "building_area", "40331", "sq ft", "2003", "ucb_news_2003_crossroads_release", "Building, not only the dining room.", "40,331-square-foot building"),
    ("Crossroads", "diners_single_dinner", "2000", "diners (approx.)", "2003 (opening week)", "ucb_news_2003_crossroads_release", "", "close to 2,000 already have come through the facility for one dinner"),
    ("Crossroads", "meal_transactions_per_day", "4000", "transactions/day (lower bound)", "2005 (FoodService Director, 2005-06-10)", "fsd_going_green",
     "Plus ~1,500/day at the attached retail outlet.", "Crossroads handles over 4,000 meal transactions daily"),
    ("Crossroads", "meals_per_day", "4000-5000", "meals/day", "c. 2006 (quoted in FoodService Director, 2007-02-01)", "fsd_colorful_next_step",
     "Kitchen designed for ~2,500/day per FSD 2008.", "4,000-5,000 meals a day"),
    ("Crossroads", "kitchen_design_capacity", "2500", "meals/day", "2008 (FoodService Director, 2008-05-01)", "fsd_shawn_lapean", "",
     "a kitchen designed to serve 2,500 a day was often swamped with more than 5,000"),
    (ALL, "residents_per_resident_community", "1100", "residents (approx.)", "2007 (FoodService Director, 2007-02-01)", "fsd_colorful_next_step",
     "Director quote: three resident communities ~1,100 each. Historic.", "We have three resident communities with about 1,100 in each location"),
    # --- housing capacity ---
    (ALL, "campus_housing_capacity_beds", "9800", "beds", "fall 2022 (UC Regents, March 2023)", "regents_mar23_j1_housing_pdf",
     "All Berkeley campus housing (residence halls + apartments), not dining-plan residents only. Occupancy 9,695 (99%).", "Berkeley 9,800 9,695 99% 45,268 21%"),
    (ALL, "new_beds_since_2018", "2400", "beds (lower bound)", "2026 (housing site)", "housing_construction_projects", "Includes apartments without required meal plans.",
     "Since 2018, UC Berkeley has added more than 2,400 beds in four new housing developments"),
    (ALL, "planned_new_dining_commons_seats", "500", "seats", "planned (Bancroft-Fulton, ~1,625 beds)", "housing_construction_projects", "Future demand point; not yet open.",
     "The housing complex will feature a 500-seat dining commons"),
    ("Foothill", "summer_guest_capacity", "700", "guests", "summer conference housing (current site)", "summer_conf_suites", "Summer conference capacity, not academic-year residents.",
     "The complex houses up to 700 guests"),
    ("Clark Kerr", "summer_guest_capacity", "400", "guests", "summer conference housing (current site)", "summer_conf_traditional_halls", "Summer conference capacity; suites listed separately at 250.",
     "The complex houses up to 400 guests in double-occupancy rooms"),
    ("Crossroads", "summer_guest_capacity_units_1_2_3", "800", "guests (4 buildings x ~200)", "summer conference housing (current site)", "summer_conf_traditional_halls",
     "Units 1-3 high-rises feed Crossroads/Café 3. Summer, double-occupancy; academic year is mostly triples so real count is higher.",
     "Each building houses approximately 200 guests in double-occupancy rooms"),
    # --- meal plan structure (drives swipe demand) ---
    (ALL, "blue_gold_plan_swipes", "14", "swipes/week", "2026-27", "meal_plans_terms_on_campus_2026_27", "Default plan, included in residence hall contract.",
     "Provides 14 meal swipes per week in the dining commons"),
    (ALL, "blue_gold_plan_flex", "300", "flex+flex+ dollars/semester", "2026-27", "meal_plans_terms_on_campus_2026_27", "", "150 flex dollars, and 150 flex+ dollars per semester"),
    (ALL, "ultimate_plan_upgrade_cost", "500", "USD/semester", "2026-27", "meal_plans_faq_2026_27", "Ultimate = unlimited swipes, one every 30 min.",
     "Upgrade from the Blue & Gold Plan to the Ultimate Plan for $500 per semester"),
    (ALL, "swipe_expiry", "weekly, Saturday midnight", "rule", "2026-27", "meal_plans_faq_2026_27", "Unused swipes are forfeited weekly: a source of planned-but-unused demand.",
     "Any unused meal swipes expire on Saturday at midnight each week"),
    (ALL, "residence_meal_plan_required", "yes", "rule", "2026-27", "meal_plans_terms_on_campus_2026_27", "", "This plan is automatically included in the Residence Hall contract and fees"),
    (ALL, "meal_price_breakfast_planholder_vs_cash", "11 / 14", "USD", "2026-27", "meal_plans_on_campus_2026_27", "Plan-holder effective price vs. cash door price.", "Breakfast $11 $14"),
    (ALL, "meal_price_lunch_planholder_vs_cash", "12 / 16", "USD", "2026-27", "meal_plans_on_campus_2026_27", "", "Lunch/Brunch $12 $16"),
    (ALL, "meal_price_dinner_planholder_vs_cash", "13 / 18", "USD", "2026-27", "meal_plans_on_campus_2026_27", "", "Dinner $13 $18"),
    (ALL, "off_campus_plan_prices", "1305 / 3420 / 4035", "USD/year", "2026-27", "meal_plans_off_campus_2026_27", "Advantage / Blue & Gold / Ultimate off-campus.", "$1,305 $3,420 $4,035"),
    # --- waste baseline ---
    (DC, "pre_consumer_waste_reduction", "27", "tons/year (19% reduction)", "undated StopWaste case study (LeanPath)", "stopwaste_cal_dining",
     "A reduction, not a total. Implies baseline ~142 tons/yr pre-consumer waste (27/0.19), derived not stated.", "reduced food waste by 19%, equivalent to 27 tons/year, or $98,402/year"),
    (DC, "food_waste_composted_from_dining_halls", "70", "tons/year", "2004", "ucb_news_2004_green", "Historic.", "including about 70 tons from the campus dining halls"),
    (ALL, "unused_swipe_resale_demand", "1985 earned / 4125 saved", "USD over 15 days", "Jan 2025 (Daily Californian)", "dailycal_meal_swipe_business",
     "Student swipe-resale app shut down by UC Berkeley Dining; evidence of unused swipes.", "earned the freshmen who sold swipes a combined total of $1,985 and saved upperclassmen a total of $4,125 on meals"),
]

AYCE_Q = "Our dining commons, including Crossroads, Café 3, Clark Kerr, and Foothill, are all-you-care-to-eat locations"

HALL_FACTS = [
    ("Crossroads", "address", "2415 Bowditch Street", "crossroads", "", "2415 Bowditch Street"),
    ("Crossroads", "stations_count", "10", "crossroads", "Official page.", "Its 10 stations serve a variety of eats like pho, pizza, deli, salad bar, and more"),
    ("Crossroads", "cuisine_themes", "international; pho, pizza, deli, salad bar; allergen-free platform", "crossroads", "", "well known for great flavor profiles and international foods"),
    ("Crossroads", "adjacent_retail", "The Den (Pizzeria 1868, Peet's Coffee)", "crossroads", "", "Pizzeria 1868 and Peet’s Coffee"),
    ("Crossroads", "all_you_care_to_eat", "yes", "meal_plans_faq_2026_27", "", AYCE_Q),
    ("Crossroads", "feeder_housing", "Units 1 & 2, Martinez Commons", "housing_martinez", "Martinez page names Crossroads as nearest; Units link from 2008 press.", "Crossroads dining commons is located across the street at 2415 Bowditch Street"),
    ("Café 3", "address", "2400 Durant Avenue", "cafe_3", "Inside Unit 3.", "2400 Durant Avenue"),
    ("Café 3", "stations_count", "2 dining stations + kosher station", "cafe_3", "", "featuring two dining stations, a kosher station"),
    ("Café 3", "cuisine_themes", "pizza, burgers, chicken sandwiches, fries, pasta; Halal center plate; Kosher kitchen", "cafe_3", "", "pizza, burgers, chicken sandwiches, fries, pasta"),
    ("Café 3", "halal_kosher", "Designated Halal and Kosher-friendly location; Kosher Kitchen Sun-Thu lunch/dinner", "meal_plans_faq_2026_27", "",
     "Café 3 is UC Berkeley Dining’s designated location for Halal and Kosher-friendly meals"),
    ("Café 3", "adjacent_retail", "Bear Market", "cafe_3", "", "a convenience store called the"),
    ("Café 3", "all_you_care_to_eat", "yes", "meal_plans_faq_2026_27", "", AYCE_Q),
    ("Café 3", "feeder_housing", "Unit 3, Blackwell", "housing_blackwell", "", "Café 3 dining commons is only a block away at 2400 Durant Avenue"),
    ("Foothill", "address", "2700 Hearst Avenue", "foothill", "Official page has no description text (gap).", "2700 Hearst Avenue"),
    ("Foothill", "all_you_care_to_eat", "yes", "meal_plans_faq_2026_27", "", AYCE_Q),
    ("Foothill", "feeder_housing", "Foothill, Stern", "housing_stern", "", "next to the Foothill residence hall complex"),
    ("Clark Kerr", "address", "2601 Warring Street", "clark_kerr", "", "2601 Warring Street"),
    ("Clark Kerr", "stations_count", "4 hot food stations + salad/deli bar", "clark_kerr", "", "Home to four hot food stations, and a salad and deli bar"),
    ("Clark Kerr", "cuisine_themes", "enchiladas, beef stew, tikka masala; made-to-order pizza/pasta; Halal burgers; vegan; top-9-allergen-free station", "clark_kerr", "",
     "The allergy-friendly station is free of the nine major allergens"),
    ("Clark Kerr", "all_you_care_to_eat", "yes", "meal_plans_faq_2026_27", "", AYCE_Q),
    ("Clark Kerr", "feeder_housing", "Clark Kerr Campus residence hall", "housing_clark_kerr", "", "The Clark Kerr dining hall serves three meals per day"),
    (DC, "carry_out_policy", "No carry-out beyond a piece of fruit or small dessert", "meal_plans_faq_2026_27", "Relevant to surplus: food is meant to be eaten on premises.",
     "additional carry-out is not permitted"),
    (DC, "hours_note", "Hours subject to change; closed for breakfast Wed 2026-11-11", "hours_of_operation", "",
     "Crossroads, Café 3, Foothill Dining Commons, and Clark Kerr Dining Commons will be closed for breakfast"),
]
