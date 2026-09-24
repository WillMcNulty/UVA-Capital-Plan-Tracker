"""The two example projects on the Feasibility tab.

1. course_example: the debt-financed example from lecture S19 of CE 3010 (Capital Projects), University of
   Virginia, Fall 2025, reproduced from the slide's printed values to show the model matches the course. Used with
   attribution; it is a teaching case, not a real UVA project.
2. residence_hall: a made-up example written for this site, not a real project. A 400-bed residence hall
   costing $56M over two years of construction, financed with $11M of equity and a $45.9M 25-year loan at 4.5%
   (including 2% cost of issuance), with $5.6M of first-year rent against $1.9M of operating cost. That puts
   first-year debt-service coverage at about 1.20, a common lender minimum.
"""
from .model import Case


def lecture_example():
    """Lecture S19 slide 8: equity $1,764,200 in years 0 and 1; a $14,678,140.88 loan (incl. 2% cost of issuance)
    drawn in year 2 with $1,116,309.29 a year of debt service over a 20-year term from year 2; project expenses
    $8,962,133.97 in years 2 and 3; operations from year 4 for 20 years (EGI $2,195,250.67 and O&M $650,000, both
    +3% a year); horizon year 23. The slide doesn't state the discount rate or the loan rate: 3% reproduces its NPV,
    and PMT(r, 20, 14,678,140.88) = 1,116,309.29 implies r = 4.376%."""
    return Case(name="Lecture S19 example (debt-financed)", horizon=23, equity={0: 1764200, 1: 1764200},
                expenses={2: 8962133.97, 3: 8962133.97}, op_start=4, op_years=20,
                egi0=2195250.67, egi_growth=0.03, om0=650000, om_growth=0.03, discount=0.03,
                loan={2: 14678140.88}, loan_rate=0.0437602245, loan_term=20, debt_start=2)


def course_example():
    return lecture_example()


def residence_hall():
    return Case(name="Made-up example: 400-bed residence hall", horizon=32, equity={0: 5.5e6, 1: 5.5e6},
                expenses={1: 28e6, 2: 28e6}, op_start=3, op_years=30, egi0=5.6e6, egi_growth=0.03,
                om0=1.9e6, om_growth=0.035, discount=0.04, loan={1: 22.95e6, 2: 22.95e6}, loan_rate=0.045,
                loan_term=25, debt_start=3)


EXAMPLES = {"course": course_example, "hall": residence_hall}
