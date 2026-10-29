# UC / UC Berkeley benchmark sources

Pull date for all files: 2026-10-27. Fetched with curl and a browser User-Agent. Numbers are in `../uc_numbers.csv`. Page refs are PDF page numbers (1-based), not printed folio numbers.

## Files

### caldining_waste_reduction.html
- URL: https://dining.berkeley.edu/sustainability/waste-reduction/
- Contents: Berkeley Dining (Cal Dining) waste-reduction page. Covers Leanpath, food donation, composting and fryer oil.
- Key numbers: Leanpath in use "since 2021" in back-of-house at 4 dining commons, 3 campus restaurants, the Eateries at MLK and Training Table. Donates "over 50,000 pounds of food or about 40,000 meals" each semester. Food that cannot be donated is composted (SB 1383).
- Confidence: high that the page says this. Med on the numbers themselves, because the page is undated and gives no year or method.
- Note: a search snippet cited a staging copy (live-wp-sa-caldinging-1.pantheon.berkeley.edu) as saying "about 30,000 lbs per year". I fetched that copy on the pull date and it was identical to the live page (50,000 lbs/semester), so I deleted it. The 30k figure may be an older version that is no longer online.

### caldining_sustainability.html
- URL: https://dining.berkeley.edu/sustainability/
- Contents: Cal Dining sustainability landing page. Qualitative only, no numbers. Names a Sustainability Program Coordinator as the contact.
- Confidence: high (no numbers to check).

### caldining_job_posting_cook_88071.html
- URL: https://careers.insidehighered.com/job/3539856/cook-5523c-berkeley-dining-88071/
- Contents: UC Berkeley job posting (datePosted 2026-08-14) with Berkeley Dining's standard boilerplate.
- Key numbers: "more than 12,000 meal plan holders", "over 5 million meals per year in 14 facilities".
- Confidence: med. This is recruiting boilerplate, not a report, and it gives no fiscal year.

### stopwaste_cal_dining_case_study.html
- URL: https://www.stopwaste.org/resource/cal-dining-food-waste-prevention (redirected from stopwaste.org/node/4778)
- Contents: StopWaste (Alameda County) case study of Cal Dining's early pre-consumer waste tracking (LeanPath, c. 2011-13).
- Key numbers:
  - 19% food waste reduction, equal to 27 tons/yr and $98,402/yr in avoided food cost
  - expects more than 15 more tons/yr reduced, worth about $50,000/yr
  - "over 10,000 meals each day" at 4 residential dining halls
  - a quote says "reduced food waste by over a third" in year one, saving $1,600/week
- Confidence: med. The case study is undated (c. 2013) and its own figures disagree (19% vs over a third; see Contradictions).

### berkeley_news_2012_cal_dining_food_waste.html
- URL: https://news.berkeley.edu/2012/11/15/america-recycles-day-epa-recognizes-campus-food-waste-reduction
- Contents: Berkeley News, 2012-11-15, on EPA recognition and Cal Dining joining the EPA Food Recovery Challenge.
- Key numbers:
  - LeanPath used since Aug 2011
  - kitchen waste cut from more than 3,000 lbs/week to about 2,000 lbs/week ("over a third")
  - more than $1,600/week in avoided purchases
  - 2013-14 goal of about $700,000 in food cost savings
  - Cal Dining aimed for zero landfill waste by 2020
  - campus diversion excluding construction was 46% (2012 sustainability report)
- Confidence: high for 2012.

### berkeley_waste_page.html
- URL: https://sustainability.berkeley.edu/waste
- Contents: UC Berkeley Office of Sustainability "Our Performance: Waste" page.
- Key numbers:
  - 54% of municipal solid waste (MSW) diverted; goal 90%
  - landfilled MSW fell from 4,095 tons (2015) to 3,431 tons (2025)
  - 90% construction and demolition (C&D) diversion as of 2019
  - STARS waste points 3.27 of 5
- Confidence: med. The 54% has no year (see Contradictions). The charts are images and were not parsed.

### ucop_2025_berkeley_location.html
- URL: https://sustainabilityreport.ucop.edu/2025/locations/uc-berkeley/
- Contents: UC Berkeley page of the UCOP 2025 Annual Report on Sustainable Practices. Covers FY2024-25.
- Key numbers:
  - sustainable food 19% of food and beverage spend ($3.3M); plant-based 37% ($6.6M)
  - "Spend on sustainable food was 6% below goal levels" (19% vs the 25% goal)
  - diversion 53% excluding C&D and 55% including C&D
  - total waste generation down 718 tons vs FY2023-24 (-10%); recycled waste down about 24%
  - chart alt-text gives FY2025 generation per person per day: 0.21 lb organics, 0.40 lb landfill, 0.14 lb recycling
- Derived, not in the CSV: implied Berkeley food and beverage spend is about $17-18M/yr ($3.3M / 0.19 ≈ $17.4M; $6.6M / 0.37 ≈ $17.8M).
- Confidence: high. This is the most recent official Berkeley-specific data.

### berkeley_food_performance.html
- URL: https://sustainability.berkeley.edu/our-performance/food (redirected from /food)
- Contents: Office of Sustainability "Our Performance: Food" page.
- Key numbers:
  - goals: at least 25% sustainable food by 2030; "Expand food recovery efforts in partnership with the campus Basic Needs program"
  - "About 25% of the food purchased by dining halls, campus restaurants, and concessions is sustainable"
  - repeats the 50,000 lbs/semester (about 40,000 meals) donation figure
  - pre-consumer food that is safe to eat goes to the pantry; post-consumer waste is composted
- Confidence: med. The page is undated and its 25% conflicts with UCOP's 19%.

### berkeley_2019_zero_waste_plan_wayback.pdf
- URL: https://facilities.berkeley.edu/sites/default/files/2019_uc_berkeley_zero_waste_plan_final.pdf
- Contents: UC Berkeley 2019 Zero Waste Plan, 44 pp. The live URL returns 404, so this copy is from the Wayback Machine (snapshot 20240225230336, `id_` raw mode).
- Key numbers:
  - p18, Table 1, FY2012-13 to FY2017-18:
    - landfill fell from 4,622 to 3,718 tons
    - composting was 1,722 tons in FY2017-18
    - diversion rate went from 47% to 52% (excludes C&D)
    - per capita waste went from 1.21 to 0.97 lbs per weighted campus user per day
  - p19, Table 2, FY2017-18:
    - food waste diverted 1,721.7 tons, 43.1% of the 3,998.4 tons diverted
    - green waste and food 339.7 tons
  - p20: organics are about 52% of diversion and 22% of all waste collected
  - p21, Table 3, landfill-stream waste characterization (2012-13 TGIF audit of 5 buildings, 3,814 lbs sorted):
    - compostables are 41% of the landfill stream; all plastic 32%; true landfill 13%
    - at Crossroads dining hall, 217 of 479 lbs (about 45%) was compost
  - p3: audits suggest 75-80% diversion is achievable through downstream handling
- Confidence: high for what the document says. The audit is old (2012-13) and small.

### bsa_countdown_zero_waste_2020.html
- URL: https://bsa.berkeley.edu/node/662
- Contents: Berkeley Staff Assembly post, 2019 ("14 months away" from the end-2020 goal).
- Key numbers: "Waste audits show that 75-80% of what is being put into our landfill bins can be composted or recycled."
- Confidence: med. It gives no audit details.

### berkeley_news_feeding_forward.html
- URL: https://news.berkeley.edu/2014/11/12/students-feeding-forward-app-fights-hunger-food-waste/
- Contents: 2014 article on Feeding Forward, a food-recovery platform founded by Berkeley students (a precursor to Copia).
- Key numbers: more than 500,000 lbs recovered since spring 2013; more than 400 donor groups, including Cal Dining and Cal Catering; about 100 recipient nonprofits.
- Confidence: high for 2014. This is Bay Area-wide, not campus-only.

### ucop_2025_annual_report_summary.pdf
- URL: https://sustainabilityreport.ucop.edu/2025/wp-content/uploads/sites/7/2025/12/2025-UC-Annual-Report-on-Sustainable-Practices-Summary.pdf
- Contents: UCOP 2025 Annual Report on Sustainable Practices, summary (7 pp). Covers FY2024-25.
- Key numbers:
  - p3, systemwide food:
    - 16% of campus and 23% of academic health center food purchases met sustainability criteria, over $35M in total
    - 31% (over $63M) of food and beverage spend was plant-based
    - 10 locations are on track for the 25% plant-based goal
  - p6, waste: 5 campuses on track for the 25% per capita MSW reduction by 2025; 2 of them on track for 50% by 2030. No systemwide diversion % is given.
- Confidence: high.

### ucop_2024_annual_report_summary.pdf
- URL: https://sustainabilityreport.ucop.edu/2024/wp-content/uploads/sites/6/2025/01/2024-UC-Annual-Report-on-Sustainable-Practices-Summary-9-Dec-24-v1-3.pdf
- Contents: UCOP 2024 summary. Covers FY2023-24.
- Key numbers:
  - p3, food:
    - 18% of campus and 20% of health center food purchases were sustainable, nearly $37M
    - campus sustainable spend up 16% year over year
    - 31% of campus and 23% of health center spend was plant-based
  - p6, waste: campuses diverted about 75% of MSW plus C&D; 5 campuses already meet the 25% per capita goal
- Confidence: high.

### ucop_2023_annual_report_summary.pdf
- URL: https://sustainabilityreport.ucop.edu/2023/wp-content/uploads/sites/5/2023/12/2023-UC-Annual-Report-on-Sustainable-Practices-Summary.pdf
- Contents: UCOP 2023 summary. Covers FY2022-23.
- Key numbers:
  - p2, food: 19% sustainable, over $33M (+$6M year over year); 29% (nearly $51M) plant-based
  - p4, waste: nearly 70% MSW plus C&D diversion; per capita waste under the 2025 goal of 1 lb/person/day
- Confidence: high.

### uc_sustainable_practices_policy.pdf
- URL: https://policy.ucop.edu/doc/3100155/SustainablePractices (needs a cookie jar; it redirect-loops without one)
- Contents: UC Policy on Sustainable Practices, 52 pp. Issuance and effective date 10/19/2026, so this is the newest revision.
- Key numbers:
  - p17, §III.F zero waste: cut per capita MSW 25% from FY2015-16 by 2025 and 50% by 2030; divert 90% of MSW; health locations 25 lbs per adjusted patient day by 2025
  - p21, §III.H foodservice:
    - 25% sustainable food by 2030 for each campus and health location
    - 25% plant-based by 2030 (strive for 30%)
    - food recovery programs must recover "the maximum amount of Edible Food" in line with California regulations
  - p42-43, §V.H.6 procedures:
    - **food recovered must be reported in pounds annually at each campus-operated facility, starting FY2027-28** (third-party vendors encouraged, not required)
    - food recovery ranks ahead of composting and landfill diversion
    - campuses must write food recovery into dining and catering contracts
  - p4: "Edible Food" includes surplus food
- Confidence: high.

### ucop_sustainable_foodservice.html
- URL: https://www.ucop.edu/sustainability/policy-areas/sustainable-foodservice/index.html
- Contents: UCOP policy-area summary page.
- Key numbers: 25% sustainable food (AASHE STARS definition) per campus and **30%** (Practice Greenhealth definition) per academic health center by 2030; 25% plant-based by 2030, striving for 30%.
- Confidence: med. It may predate the Oct 2026 policy (see Contradictions).

## Contradictions
1. **Berkeley sustainable food %:** UCOP FY2024-25 says 19% ($3.3M), "6% below goal". The campus Food page says "about 25%" with no date. Use the 19%.
2. **Berkeley diversion:** the campus Waste page says 54% with no year. UCOP FY2024-25 says 53% excluding C&D and 55% including C&D. The 2019 plan gives 52% for FY2017-18. Diversion has been roughly flat at 52-55% for 7+ years against a 90% goal.
3. **Cal Dining early LeanPath results:** StopWaste says 19% (27 tons/yr). The same page's quote and Berkeley News 2012 say "over a third" (3,000 to 2,000 lbs/week). They likely cover different scopes or time windows.
4. **Health center sustainable-food target:** the UCOP web page says 30% (Practice Greenhealth). The 10/19/2026 policy text (p21) says 25% for each campus and health location. The policy PDF is authoritative.
5. **Donation volume:** a search snippet attributed "about 30,000 lbs/year" to a Cal Dining staging page. Both copies fetched today say 50,000 lbs per semester. That is about 100,000 lbs/yr, a gap of more than 3x.
6. **Systemwide sustainable food:** 19% (FY22-23, all locations), then 18% campus (FY23-24), then 16% campus (FY24-25). Campus share is falling, and UCOP attributes this to inflation, budget cuts and tracking problems.

## Gaps (searched, not found)
- Any Cal Dining annual report or public Leanpath dashboard: no lbs wasted, no waste per meal, no current pre- or post-consumer split.
- A dated, method-backed figure for Cal Dining donated lbs per year. Only the undated 50k lbs/semester exists.
- Official meals served per year. Only job-posting boilerplate; no fiscal-year figure.
- A recent (post-2013) UC Berkeley waste characterization study. The 2019 plan confirms none has been done since 2013.
- The Cal Zero Waste FAQ with landfill tonnage history: the URL 404s and node/69 resolves to an unrelated page.
- Basic Needs Center pantry lbs distributed: the current pantry page has no volume figures. A search snippet cited "about 19,500 visits/semester (2019)" but it is not on the live page, so it is not in the CSV.
- A Berkeley Food Recovery Network chapter: no chapter-level figures found. Feeding Forward (2013-14) is the closest.
- UCOP 2025 per-campus food-recovery lbs: not reported yet. The policy only starts this in FY2027-28.
- Full (non-summary) UCOP report PDFs: the per-location web pages were used instead. The Berkeley page chart data is mostly canvas rendered by JS, and only the alt-text numbers were captured.
