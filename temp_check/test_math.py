import math

def calc_nest_egg(savings, monthly, ann_return, years, esc_rate):
    r = ann_return / 100
    esc = esc_rate / 100
    bal = savings
    total_contrib = 0
    for y in range(1, years + 1):
        add = monthly
        if esc > 0 and y > 1:
            add = monthly * (1 + esc) ** (y - 1)
        bal += add * 12
        bal += bal * r
        total_contrib += add * 12
    growth = bal - savings - total_contrib
    return bal, total_contrib, growth

egg, contrib, growth = calc_nest_egg(50000, 500, 7, 35, 2)
print(f"Nest egg: ${egg:,.0f}")
print(f"Total contributions: ${contrib:,.0f}")
print(f"Growth: ${growth:,.0f}")
print(f"Growth %: {growth/egg*100:.0f}%")

def project_drawdown(nest_egg, ann_return, years, monthly_goal, infl):
    r = ann_return / 100
    i = infl / 100
    bal = nest_egg
    monthly = monthly_goal
    total_withdrawn = 0
    for age in range(years):
        yr_withdraw = monthly * 12
        bal -= yr_withdraw
        if bal <= 0:
            return age, total_withdrawn
        total_withdrawn += yr_withdraw
        bal += bal * r
        monthly *= (1 + i)
    return years, total_withdrawn

duration, withdrawn = project_drawdown(1000000, 7, 30, 4000, 3)
print(f"Funds last: {duration} years")
print(f"Total withdrawn: ${withdrawn:,.0f}")
