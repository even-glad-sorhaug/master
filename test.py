# Example: modeling a complementarity condition as a
#   disjunction
#
# This model does not work with existing transformations.
# See simple2.py and simple3.py for variants that work.

from pyomo.core import *
from pyomo.gdp import *
from pyomo.environ import *

def build_model():

    T = list(range(2))

    """Constants"""
    # Generators
    demand = 500            # kWh
    min = {1:150,2:200}     # kW
    max = {1:400,2:350}     # kW
    fuel = {1:20,2:15}      # NOK/kWh
    invest = {1:300,2:400}  # NOK/yr
    em_gen = {1: 15, 2: 20} # gCO2/kWh

    # Solar
    PV = 30                 # kW

    # Grid
    grid_max = 400          # kW
    spot = 25               # NOK/kWh
    em_grid = 18            # gCO2/kWh

    """Initialize Model"""
    m = ConcreteModel()

    """Sets"""
    m.G = RangeSet(2)

    """Parameters"""
    m.min = Param(m.G, initialize= min)         # Minimum production
    m.max = Param(m.G, initialize= max)         # Maximum production
    m.demand = Param(initialize= demand)        # Demand
    m.emission = Param(m.G, initialize= em_gen) # Emission intensity per gen
    m.fuel = Param(m.G, initialize= fuel)       # Fuel cost per gen
    m.invest = Param(m.G, initialize= invest)   # Discounted investment cost

    m.pv = Param(initialize= PV)

    m.spot = Param(initialize= spot, name= "Spot price")            # Spot price
    m.em_grid = Param(initialize= em_grid)      # Emission intensity from grid
    m.grid_max = Param(initialize=grid_max)     # Transmission capacity of grid

    """Variables"""
    m.gen = Var(m.G, within= NonNegativeReals, bounds= (0, 1000), name= "Generator production") # Production per generator
    m.grid = Var(initialize= 0, within= NonNegativeReals, bounds= (0, 1000))                    # Import from grid

    """Constraints"""
    # Zero emission compared to buying from grid
    def ghg_min(m):
        return sum(m.gen[g] * m.Fi_g[g] for g in m.G) <= m.P_dem * m.Fi_grid
    m.c_ghg = Constraint(rule= ghg_min)

    # Production equal to demand
    m.c_demand = Constraint(expr=sum(m.gen[g] for g in m.G) + m.grid + m.pv == m.demand)

    # Import and export less then capaciity
    m.c_grid_cap = Constraint(expr= m.grid <= m.grid_max)

    """Disjunctions"""

    # Disjunction for generators that have limited range
    def disjZero(block,g):
        model = block.model()
        block.c = Constraint(expr=model.gen[g] == 0)
    m.dz = Disjunct(m.G, rule=disjZero)

    def disjMinMax(block,g):
        model = block.model()
        block.c1 = Constraint(expr=model.gen[g] >= model.P_min[g])
        block.c2 = Constraint(expr=model.gen[g] <= model.P_max[g])
    m.dmm = Disjunct(m.G, rule=disjMinMax)

    def D_rule(block, g):
        model = block.model()
        return [model.dz[g], model.dmm[g]]
    m.D_min_max = Disjunction(m.G, rule= D_rule)

    """Objective"""
    # Minimize cost
    m.o = Objective(expr= sum(m.fuel[g] * m.gen[g] for g in m.G) + m.grid*m.spot, sense= minimize)

    return m

# Calling the solver
m = build_model()
TransformationFactory('core.logical_to_linear').apply_to(m)
TransformationFactory('gdp.bigm').apply_to(m)

solver = SolverFactory('gurobi')
results = solver.solve(m)
results.write(num=1)
print("Cost:", m.o.value())
print("PV:  ", m.pv.value)
print("Gen1:", m.gen[1].value)
print("Gen2:", m.gen[2].value)
print("Grid:", m.grid.value)
print("Tot: ", sum(m.gen[g].value for g in m.G) + m.grid.value + m.pv)