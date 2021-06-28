# Example: modeling a complementarity condition as a
#   disjunction
#
# This model does not work with existing transformations.
# See simple2.py and simple3.py for variants that work.

from pyomo.core import *
from pyomo.gdp import *
from pyomo.environ import *
from data import *

Demand, Prod = Data_fetch()
def build_model():

    """Constants"""
    # Economic constants
    days = 150                           # Duration of period
    r = 0.05                            # Discount rate
    epsi = {}
    for n in RangeSet(25):              # Annuity factor
        epsi[n] = r/(1-(1+r)**(-n))
    hours = 24*days                     # Duration of period
    period = hours/8760                 # Fraction of one year

    # Generator units
    chp_factor = Prod["CHP"]            # Heat-Power ratio for generators
    P_min = Prod["Pmin"]                # Minimum power [kW]
    P_max = Prod["Pmax"]                # Maximum power [kW]
    P_fuelc = Prod["Pfuel_cost"]        # NOK/kWh
    P_eta = Prod["Peta"]
    P_lifetime = Prod["Plifetime"]
    P_invest = {}
    em_gen = {}
    for n in RangeSet(P_min.__len__()):
        P_invest[n] = Prod["Pinvest"][n] * epsi[P_lifetime[n]] * period      # NOK/yr
        em_gen[n] = Prod["Pemi"][n]/P_eta[1]                                # gCO2/kWh

    # Heat units
    Q_min = Prod["Qmin"]                #
    Q_max = Prod["Qmin"]                #
    Q_eta = Prod["Qeta"]                #
    Q_fuelc = Prod["Qfuel_cost"]        # NOK/kWh
    Q_lifetime = Prod["Qlifetime"]      #
    Q_invest = {}                       #
    em_heat = {}                        #
    for n in RangeSet(Q_min.__len__()):
        Q_invest[n] = Prod["Qinvest"][n] * epsi[Q_lifetime[n]] * period     # NOK/yr
        em_heat[n] = Prod["Qemi"][n] / Q_eta[1]                             # gCO2/kWh

    # Grid
    grid_max = 400                      # kW
    dh_cost = 0.09                      #
    dh_max = 100                        #
    em_dh = 133                         # gCO2/kWh
    spot = {}                           #
    em_grid = {}                        #
    for n in RangeSet(hours):
        #spot[n] = Prod["Spot"][n]
        spot[n] = 5
        em_grid[n] = Prod["Gridemi"][n]

    # Solar
    PV = {}                             # kW Power
    ST = {}                             # kW Heat
    for n in RangeSet(hours):
        PV[n] = Prod["PV"][n]
        ST[n] = Prod["ST"][n]
    PV_invest = Prod["PVinvest"] * epsi[Prod["PV_lifetime"]] * period     # NOK/yr
    ST_invest = Prod["STinvest"] * epsi[Prod["ST_lifetime"]] * period     # NOK/yr

    # Demand
    P_dem = {}                          # kWh
    Q_dem = {}                          # kWh
    for n in RangeSet(hours):           #
        P_dem[n] = Demand["P_el"][n]
        Q_dem[n] = Demand["Q_sh"][n] + Demand["Q_hw"][n]


    """Initialize Model"""
    m = ConcreteModel()

    """Sets"""
    m.G = RangeSet(P_min.__len__())
    m.H = RangeSet(Q_min.__len__())
    m.T = RangeSet(hours)

    """Parameters"""
    # Electricity
    m.P_min = Param(m.G, initialize= P_min)         # Minimum production
    m.P_max = Param(m.G, initialize= P_max)         # Maximum production
    m.P_dem = Param(m.T, initialize= P_dem)        # Demand
    m.em_gen = Param(m.G, initialize= em_gen) # Emission intensity per gen
    m.P_fuelc = Param(m.G, initialize= P_fuelc)       # Fuel cost per gen
    m.P_invest = Param(m.G, initialize= P_invest)   # Discounted investment cost
    m.P_eta = Param(m.G, initialize= P_eta)

    # Heat
    m.Q_min = Param(m.G, initialize=Q_min)  # Minimum production
    m.Q_max = Param(m.G, initialize=Q_max)  # Maximum production
    m.Q_dem = Param(m.T, initialize=Q_dem)
    m.chp = Param(m.G, initialize=chp_factor)
    m.em_heat = Param(m.H, initialize=em_heat)  # Emission intensity per heat
    m.Q_invest = Param(m.H, initialize=Q_invest)  # Discounted investment cost
    m.Q_fuelc = Param(m.H, initialize=Q_fuelc)  # Fuel cost per heat
    m.Q_eta = Param(m.G, initialize=Q_eta)

    # Grid
    m.spot = Param(m.T, initialize= spot)       # Spot price
    m.em_grid = Param(m.T, initialize= em_grid)      # Emission intensity from grid
    m.grid_max = Param(initialize=grid_max)     # Transmission capacity of grid
    m.dh_cost = Param(initialize= dh_cost)
    m.dh_max = Param(initialize=dh_max)  # Transmission capacity of grid
    m.em_dh = Param(initialize= em_dh)

    # Solar
    m.pv = Param(m.T, initialize= PV)
    m.st = Param(m.T, initialize= ST)

    """Variables"""
    m.gen = Var(m.G, m.T, within= NonNegativeReals, bounds= (0, 1000)) # Production per generator
    m.grid = Var(m.T, initialize= 0, within= NonNegativeReals, bounds= (0, 1000))                    # Import from grid
    m.heat = Var(m.H, m.T, within= NonNegativeReals, bounds= (0, 1000))
    m.dh = Var(m.T, initialize=0, within=NonNegativeReals, bounds=(0, 1000))
    m.u_gen = Var(m.G,m.T, within= Binary)

    """Constraints"""
    # Zero emission compared to buying from grid
    def ghg_min(m):
        electricity_emissions = sum(m.gen[g,t] * m.Fi_g[g] for g in m.G for t in m.T)
        heat_emissions = sum(m.heat[h,t] * m.Fi_h[h] for h in m.H for t in m.T)
        grid_emissions = sum(m.p_imp[t] * m.Fi_grid[t] + m.dh[t] * m.Fi_dh for t in m.T)
        base_emissions = sum((m.P_dem[t] + m.Q_dem[t]) * m.Fi_grid[t] for t in m.T)
        return electricity_emissions+heat_emissions+grid_emissions <= base_emissions
    m.c_ghg = Constraint(rule= ghg_min)

    # Production equal to demand
    def power_met(m, t):
        return sum(m.gen[g,t] for g in m.G) + m.p_imp[t] + m.pv[t] >= m.P_dem[t]
    m.c_pdem = Constraint(m.T, rule= power_met)

    def heat_met(m, t):
        return sum(m.gen[g,t]*m.chp[g] for g in m.G) + sum(m.heat[h,t] for h in m.H) + m.dh[t] + m.st[t] >= m.Q_dem[t]
    m.c_qdem = Constraint(m.T, rule= heat_met)

    # Import and export less then capaciity
    def grid_cap(m, t):
        return m.p_imp[t] <= m.Max_grid
    m.c_grid_cap = Constraint(m.T, rule= grid_cap)

    def dh_cap(m, t):
        return m.dh[t] <= m.Max_dh
    m.c_dh_cap = Constraint(m.T, rule= dh_cap)

    # Maximum operational hours
    def y_big_M(model):
        bigM = 10000  # Should be a big number, big enough that it will be bigger than any number in your
        # model, but small enough that it will stay around the same order of magnitude. Avoid
        # utterly big number like 1e12 and + if you don't need to, since having numbers too
        # large causes problems.
        PENALTY_TRESHOLD = 19000
        return PENALTY_TRESHOLD - sum(
            model.x[supplier, market]
            for supplier in model.suppliers
            for market in model.markets
            if 'BC' in supplier
        ) <= model.y * bigM

    m.y_big_M = Constraint(rule=y_big_M)

    """Disjunctions"""

    # Disjunction for generators that have limited range (0 or within range)
    def disjZero(block,g,t):
        model = block.model()
        block.c = Constraint(expr=model.gen[g,t] == 0)
    m.dpz = Disjunct(m.G, m.T, rule=disjZero)

    def disjMinMax(block,g,t):
        model = block.model()
        block.c1 = Constraint(expr=model.gen[g,t] >= model.P_min[g])
        block.c2 = Constraint(expr=model.gen[g,t] <= model.P_max[g])
    m.dpmm = Disjunct(m.G, m.T, rule=disjMinMax)

    def D_rule(block,g,t):
        model = block.model()
        return [model.dpz[g,t], model.dpmm[g,t]]
    m.D_Pmin_max = Disjunction(m.G, m.T, rule= D_rule)

    # Disjunction for heat that have limited range (0 or within range)

    def disjZero(block,h,t):
        model = block.model()
        block.c = Constraint(expr=model.heat[h,t] == 0)
    m.dqz = Disjunct(m.H, m.T, rule=disjZero)

    def disjMinMax(block,h,t):
        model = block.model()
        block.c1 = Constraint(expr=model.heat[h,t] >= model.Q_min[h])
        block.c2 = Constraint(expr=model.heat[h,t] <= model.Q_max[h])
    m.dqmm = Disjunct(m.H, m.T, rule=disjMinMax)

    def D_rule(block,h,t):
        model = block.model()
        return [model.dqz[h,t], model.dqmm[h,t]]
    m.D_Qmin_max = Disjunction(m.H, m.T, rule= D_rule)

    """Objective"""
    # Minimize electricity from grid
    def OBJ_rule(model):
        return sum(m.grid[t] for t in m.T)

    # Minimize cost
    def OBJ_rule(model):
        generator_operation = sum(m.P_fuelc[g] * m.gen[g, t] / m.P_eta[g] for g in m.G for t in m.T)
        heat_operation = sum(m.Q_fuelc[h] * m.heat[h, t] / m.Q_eta[h] for h in m.H for t in m.T)
        grid_costs = sum(m.grid[t] * m.spot[t] for t in m.T) + sum(m.dh[t] * m.dh_cost for t in m.T)
        investment = sum(m.P_invest[g] for g in m.G) + sum(m.Q_invest[h] for h in m.H)
        return generator_operation + heat_operation + grid_costs + investment
    m.o = Objective(rule= OBJ_rule, sense= minimize)

    return m

# Calling the solver
m = build_model()
TransformationFactory('core.logical_to_linear').apply_to(m)
TransformationFactory('gdp.bigm').apply_to(m)

solver = SolverFactory('gurobi')
results = solver.solve(m)
results.write(num=1)



print("Cost:", m.o.value())
print("Cost:", sum((m.P_dem[t] + m.Q_dem[t])*m.spot[t] for t in m.T))
#for i in m.T:
#    print("Hour ", i, ": ")
#    print("--------------")
#    print("P_dem: ", m.P_dem[i])
#    print("PV:    ", m.pv[i])
#    print("Gen1:  ", m.gen[1,i].value)
#    print("Gen2:  ", m.gen[2,i].value)
#    print("Grid:  ", m.grid[i].value)
#    print("P_tot: ", sum(m.gen[g, i].value for g in m.G) + m.grid[i].value + m.pv[i])
#    print("---")
#    print("Q_dem: ", m.Q_dem[i])
#    print("ST:    ", m.st[i])
#    print("Heat1: ", m.heat[1, i].value)
#    print("Heat2: ", m.heat[2, i].value)
#    print("DH:    ", m.dh[i].value)
#    print("CHP:   ", sum(m.gen[g, i].value*m.chp[g] for g in m.G))
#    print("Q_tot: ", sum(m.heat[h,i].value for h in m.H) + m.dh[i].value + m.st[i])
#    print("--------------")

Results_to_file(m)
