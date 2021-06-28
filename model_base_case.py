"""

Optimization model for a microgrid with fuel cell chp
    =====================================

    (c) Even Glad Sørhaug, March 2021

    ====================================

"""
#

from pyomo.gdp import *
from pyomo.environ import *
from data import *
# import numpy as np

def build_model_base_case(system_data):
    Demand, Prod, Base, Storage = Data_fetch(system_data)

    """Constants"""
    # Economic constants
    days = Base["Days"]                           # Duration of period
    r = Base["r"]                   # Discount rate
    epsi = {}
    for n in RangeSet(25):              # Annuity factor
        epsi[n] = r/(1-(1+r)**(-n))
    hours = 24*days                     # Duration of period
    period = hours/8760                 # Fraction of one year

    # Demand
    P_dem = {}  # kWh
    Q_dem = {}  # kWh
    for n in RangeSet(hours):  #
        P_dem[n] = Demand["P_el"][n]
        Q_dem[n] = Demand["Q_sh"][n] + Demand["Q_hw"][n]
    #P_dem_max = max(P_dem.values())

    # Generator units
    chp_factor = Prod["CHP"]            # Heat-Power ratio for generators
    P_min = Prod["Pmin"]                # Minimum power [kW]
    P_max = Prod["Pmax"]                # Maximum power [kW]
    P_fuelc = Prod["Pfuel_cost"]        # NOK/kWh
    P_eta = Prod["Peta"]
    P_lifetime = Prod["Plifetime"]
    P_maint = {}
    P_hours_max = Prod["Phours_max"]
    P_invest = {}
    em_gen = {}
    for n in RangeSet(P_min.__len__()):
        P_invest[n] = Prod["Pinvest"][n] * epsi[P_lifetime[n]] * period     # NOK/hr
        P_maint[n] = Prod["Pmaint"][n] * period
        em_gen[n] = Prod["Pemi"][n]/P_eta[1]                                # gCO2/kWh

    # Heat units
    Q_min = Prod["Qmin"]                #
    Q_max = Prod["Qmin"]                #
    Q_eta = Prod["Qeta"]                #
    Q_fuelc = Prod["Qfuel_cost"]        # NOK/kWh
    Q_lifetime = Prod["Qlifetime"]      #
    Q_hours_max = Prod["Qhours_max"]
    Q_maint = {}
    Q_invest = {}                       #
    em_heat = {}                        #
    for n in RangeSet(Q_min.__len__()):
        Q_invest[n] = Prod["Qinvest"][n] * epsi[Q_lifetime[n]] * period     # NOK/period
        Q_maint[n] = Prod["Qmaint"][n] * period
        em_heat[n] = Prod["Qemi"][n] / Q_eta[1]                             # gCO2/kWh

    # Grid
    c_fixtar = Base["Fixed_tarif"]*period
    c_entar = Base["Energy_tarif"]
    c_powtar = Base["Power_tarif"]
    C_gc = Base["GC_cost"]
    C_dh_fixed = Base["DH_fixed"]*period
    c_dh_powtar = {}
    C_dh_entar = {}
    C_co2 = Base["Emission_cost"]
    dh_max = Base["DH_max"]                        #
    em_dh = Base["DH_em"]                          # gCO2/kWh
    C_imp = {}
    C_exp = {}                          #
    em_grid = {}                        #
    grid_max = {}                       # kW
    for n in RangeSet(hours):
        C_imp[n] = (Prod["Spot"][n] + c_entar) * 1.25
        C_exp[n] = Prod["Spot"][n]
        em_grid[n] = Prod["Gridemi"][n]
        grid_max[n] = Base["Grid_max"]
        C_dh_entar[n] = Prod["DH_energy"][n] * 1.25
        c_dh_powtar[n] = Prod["DH_power"][n]


    # Solar
    PV = {}                             # kW Power
    ST = {}                             # kW Heat
    Temp = {}                           # Outisde temperature, C
    for n in RangeSet(hours):
        PV[n] = Prod["PV"][n]
        ST[n] = Prod["ST"][n]
        Temp[n] = Demand["Temp"][n]
    if Prod["PVinvest"] == 0:
        PV_invest = 0
        ST_invest = 0
        PV_maint = 0
        ST_maint = 0
    else:
        PV_invest = Prod["PVinvest"] * epsi[Prod["PV_lifetime"]] * period     # NOK/yr
        ST_invest = Prod["STinvest"] * epsi[Prod["ST_lifetime"]] * period     # NOK/yr
        PV_maint = Prod["PVmaint"] * period
        ST_maint = Prod["STmaint"] * period

    # Energy Storage
    v_bat_0 = Storage["Start"][1]                 # Battery energy status
    v_bat_max = Storage["Capacity"][1]             # bat max cap
    v_bat_min = Storage["Max_dod"][1]*v_bat_max
    eta_bat = Storage["Eta_ch"][1]
    P_bat_max = Storage["Max_dis"][1]
    Invest_bat = Storage["Invest"][1] * epsi[Storage["Lifetime"][1]] * period
    Cap_min_bat = Storage["Cap_min"][1]
    Cap_max_bat = Storage["Cap_max"][1]

    v_tes_0 = Storage["Start"][2]
    v_tes_max = Storage["Capacity"][2]
    v_tes_min = Storage["Max_dod"][2] * v_bat_max
    eta_tes = Storage["Eta_ch"][2]
    Q_tes_max = Storage["Max_dis"][2]
    Invest_tes = Storage["Invest"][2] * epsi[Storage["Lifetime"][2]] * period
    Cap_min_tes = Storage["Cap_min"][2]
    Cap_max_tes = Storage["Cap_max"][2]


    """Initialize Model"""
    m = ConcreteModel()

    """Sets"""
    m.G = RangeSet(P_min.__len__())
    m.H = RangeSet(Q_min.__len__())
    m.B = RangeSet(P_min.__len__()+Q_min.__len__())
    m.T = RangeSet(hours)
    m.start = 1

    """Parameters"""
    m.hours = Param(initialize=hours)

    m.output = Param(initialize="results_" + Base["File_name"], mutable=True)
    m.config = Param(initialize="Bio + FC", mutable=True)
    m.period = Param(initialize=period)
    m.C_co2 = Param(initialize=C_co2)
    m.C_gc = Param(initialize=C_gc)

    # Electricity
    m.P_min = Param(m.G, initialize=P_min)          # Minimum production
    m.P_max = Param(m.G, initialize=P_max)          # Maximum production
    m.P_dem = Param(m.T, initialize=P_dem)          # Demand
    m.P_eta = Param(m.G, initialize=P_eta)
    m.P_hours_max = Param(m.G, initialize=P_hours_max)
    m.C_g_fuel = Param(m.G, initialize=P_fuelc, mutable=True)      # Fuel cost per gen
    m.C_g_invest = Param(m.G, initialize=P_invest)    # Discounted investment cost
    m.C_g_maint = Param(m.G, initialize=P_maint)
    m.Fi_g = Param(m.G, initialize=em_gen)  # Emission intensity per gen


    # Heat
    m.Q_min = Param(m.G, initialize=Q_min)  # Minimum production
    m.Q_max = Param(m.G, initialize=Q_max)  # Maximum production
    m.Q_dem = Param(m.T, initialize=Q_dem)
    m.Q_eta = Param(m.H, initialize=Q_eta)
    m.Q_hours_max = Param(m.G, initialize=Q_hours_max)
    m.C_h_invest = Param(m.H, initialize=Q_invest)  # Discounted investment cost
    m.C_h_fuel = Param(m.H, initialize=Q_fuelc)  # Fuel cost per heat
    m.C_h_maint = Param(m.H, initialize=Q_maint)
    m.Fi_h = Param(m.H, initialize=em_heat)  # Emission intensity per heat
    m.chp = Param(m.G, initialize=chp_factor)

    m.Temp = Param(m.T, initialize=Temp)

    # Grid
    m.C_imp = Param(m.T, initialize=C_imp)       # Spot price
    m.C_exp = Param(m.T, initialize=C_exp)  # Spot price
    m.C_grid_power = Param(initialize=c_powtar)
    m.C_fixtar = Param(initialize=c_fixtar)
    m.Max_grid = Param(m.T, initialize=grid_max, mutable= True)     # Transmission capacity of grid
    m.Fi_grid = Param(m.T, initialize=em_grid)  # Emission intensity from grid

    m.C_dh_entar = Param(m.T,initialize= C_dh_entar)
    m.C_dh_power = Param(m.T,initialize=c_dh_powtar)
    m.C_dh_fixed = Param(initialize= C_dh_fixed)
    m.Max_dh = Param(initialize=dh_max)  # Transmission capacity of grid
    m.Fi_dh = Param(initialize= em_dh)

    # Solar
    m.pv = Param(m.T, initialize=PV)
    m.st = Param(m.T, initialize=ST)
    m.C_pv_maint = Param(initialize=PV_maint)
    m.C_st_maint = Param(initialize=ST_maint)
    m.C_pv_invest = Param(initialize=PV_invest)
    m.C_st_invest = Param(initialize=ST_invest)

    # Battery
    m.eta_bat = Param(initialize=eta_bat)
    m.v_bat_0 = Param(initialize=v_bat_0)
    m.Min_v_bat = Param(initialize=v_bat_min)
    m.Max_v_bat = Param(initialize=v_bat_max)
    m.C_bat_invest = Param(initialize=Invest_bat)
    m.Min_cap_bat = Param(initialize=Cap_min_bat)
    m.Max_cap_bat = Param(initialize=Cap_max_bat)

    m.eta_tes = Param(initialize=eta_tes)
    m.v_tes_0 = Param(initialize=v_tes_0)
    m.Min_v_tes = Param(initialize=v_tes_min)
    m.Max_v_tes = Param(initialize=v_tes_max)
    m.C_tes_invest = Param(initialize=Invest_tes)
    m.Min_cap_tes = Param(initialize=Cap_min_tes)
    m.Max_cap_tes = Param(initialize=Cap_max_tes)

    """Variables"""
    m.gen = Var(m.G, m.T, bounds=(0, 1000)) # Production per generator
    m.p_imp = Var(m.T, initialize=0, bounds= (0, 1000))                    # Import from grid
    m.p_exp = Var(m.T, initialize=0, bounds=(0, 1000))  # Export to grid
    m.heat = Var(m.H, m.T, bounds=(0, 1000))
    m.dh = Var(m.T, initialize=0, bounds=(0, 1000))

    # Electric boiler
    m.boiler = Var(m.T, initialize=0, bounds=(0,315))

    # Binary variables
    m.u_gen = Var(m.G, m.T, within=Binary)
    m.u_heat = Var(m.H, m.T, within=Binary)
    m.b_g = Var(m.G, within=Binary)
    m.b_h = Var(m.H, within=Binary)

    # Energy storage
    m.v_bat = Var(m.T, initialize=m.Min_v_bat, bounds=(m.Min_v_bat, m.Max_v_bat))
    m.p_bat_ch = Var(m.T, initialize=0, bounds=(0, P_bat_max))
    m.p_bat_dis = Var(m.T, initialize=0, bounds=(0, P_bat_max))

    m.v_tes = Var(m.T, initialize=m.Min_v_tes, bounds=(m.Min_v_tes, m.Max_v_tes))
    m.q_tes_ch = Var(m.T, initialize=0, bounds=(0, Q_tes_max))
    m.q_tes_dis = Var(m.T, initialize=0, bounds=(0, Q_tes_max))

    """Constraints"""
    # Zero emission compared to buying from grid
    def ghg_min(m):
        electricity_emissions = sum(m.gen[g,t] * m.Fi_g[g] for g in m.G for t in m.T)
        heat_emissions = sum(m.heat[h,t] * m.Fi_h[h] for h in m.H for t in m.T)
        grid_emissions = sum(m.p_imp[t] * m.Fi_grid[t] + m.dh[t] * m.Fi_dh for t in m.T)
        base_emissions = sum((m.P_dem[t] + m.Q_dem[t]) * m.Fi_grid[t] for t in m.T)
        return electricity_emissions+heat_emissions+grid_emissions <= base_emissions
    #m.c_ghg = Constraint(rule= ghg_min)

    # Production equal to demand
    def power_met(m, t):
        return sum(m.gen[g,t] for g in m.G) + m.p_imp[t] + m.pv[t] + m.eta_bat * m.p_bat_dis[t] == \
               m.P_dem[t] + m.p_exp[t] + m.p_bat_ch[t] + m.boiler[t]
    m.c_pdem = Constraint(m.T, rule= power_met)

    def heat_met(m, t):
        chp_heat = sum(m.gen[g,t]*m.chp[g] for g in m.G)
        heaters = sum(m.heat[h,t] for h in m.H)
        return chp_heat + heaters + m.dh[t] + m.st[t] + m.eta_tes * m.q_tes_dis[t] + m.boiler[t] == \
               m.Q_dem[t] + m.q_tes_ch[t]
    m.c_qdem = Constraint(m.T, rule= heat_met)

    # Import and export less then capaciity
    def grid_cap(m, t):
        return m.p_imp[t] <= m.Max_grid[t]
    m.c_grid_cap = Constraint(m.T, rule= grid_cap)

    def dh_cap(m, t):
        return m.dh[t] <= m.Max_dh
    m.c_dh_cap = Constraint(m.T, rule= dh_cap)


    # Battery and charge
    def bat_storage(m, t):
        if t == 1:
            return m.v_bat[t] == m.Min_v_bat
        else:
            return m.v_bat[t] == m.v_bat[t - 1] + m.eta_bat * (m.p_bat_ch[t - 1] - m.p_bat_dis[t - 1])
    m.c_bat_store = Constraint(m.T, rule= bat_storage)

    # Battery and charge
    def tes_storage(m, t):
        if t == 1:
            return m.v_tes[t] == m.Min_v_tes
        else:
            return m.v_tes[t] == m.v_tes[t - 1] + m.eta_tes * (m.q_tes_ch[t - 1] - m.q_tes_dis[t - 1])
    m.c_tes_store = Constraint(m.T, rule=tes_storage)

    def max_hours_gen(m, g):
        return sum(m.u_gen[g, t] for t in m.T) <= m.P_hours_max[g]
    m.c_hours_max_gen = Constraint(m.G, rule=max_hours_gen)

    def max_hours_heat(m, h):
        return sum(m.u_heat[h, t] for t in m.T) <= m.Q_hours_max[h]
    m.c_hours_max_heat = Constraint(m.H, rule=max_hours_heat)

    """Disjunctions"""
    # Disjunction for generators that have limited range (0 or within range)
    def disjZero(block, g, t):
        model = block.model()
        block.c1 = Constraint(expr=model.gen[g, t] == 0)
        block.c2 = Constraint(expr=model.u_gen[g, t] == 0)

    m.dpz = Disjunct(m.G, m.T, rule=disjZero)

    def disjMinMax(block, g, t):
        model = block.model()
        block.c1 = Constraint(expr=model.gen[g, t] >= model.P_min[g])
        block.c2 = Constraint(expr=model.gen[g, t] <= model.P_max[g])
        block.c3 = Constraint(expr=model.u_gen[g, t] == 1)

    m.dpmm = Disjunct(m.G, m.T, rule=disjMinMax)

    def D_rule_P(block,g,t):
        model = block.model()
        return [model.dpz[g,t], model.dpmm[g,t]]
    m.D_Pmin_max = Disjunction(m.G, m.T, rule= D_rule_P)

    # Disjunction for heat that have limited range (0 or within range)
    def disjZero(block,h,t):
        model = block.model()
        block.c1 = Constraint(expr=model.heat[h,t] == 0)
        block.c2 = Constraint(expr=model.u_heat[h, t] == 0)
    m.dqz = Disjunct(m.H, m.T, rule=disjZero)

    def disjMinMax(block,h,t):
        model = block.model()
        block.c1 = Constraint(expr=model.heat[h,t] >= model.Q_min[h])
        block.c2 = Constraint(expr=model.heat[h,t] <= model.Q_max[h])
        block.c3 = Constraint(expr=model.u_heat[h, t] == 1)
    m.dqmm = Disjunct(m.H, m.T, rule=disjMinMax)

    def D_rule_Q(block,h,t):
        model = block.model()
        return [model.dqz[h,t], model.dqmm[h,t]]
    m.D_Qmin_max = Disjunction(m.H, m.T, rule= D_rule_Q)

    # Battery charge or discharge
    def disjCh(block,t):
        model = block.model()
        block.c = Constraint(expr=model.p_bat_ch[t] == 0)
    m.d_batch = Disjunct(m.T, rule=disjCh)
    m.c_end = Constraint(expr=m.p_bat_dis[hours] <= (m.v_bat[hours] - v_bat_min))

    def disjDis(block, t):
        model = block.model()
        block.c = Constraint(expr=model.p_bat_dis[t] == 0)
    m.d_batdis = Disjunct(m.T, rule=disjDis)

    def D_rule_bat(block,t):
        model = block.model()
        return [model.d_batch[t], model.d_batdis[t]]
    m.D_bat = Disjunction(m.T, rule= D_rule_bat)

    def disjCh(block,t):
        model = block.model()
        block.c = Constraint(expr=model.q_tes_ch[t] == 0)
    m.d_tesch = Disjunct(m.T, rule=disjCh)
    m.d_end = Constraint(expr=m.q_tes_dis[hours] <= (m.v_tes[hours] - v_tes_min))

    def disjDis(block, t):
        model = block.model()
        block.c = Constraint(expr=model.q_tes_dis[t] == 0)
    m.d_tesdis = Disjunct(m.T, rule=disjDis)

    def D_rule_tes(block,t):
        model = block.model()
        return [model.d_tesch[t], model.d_tesdis[t]]
    m.D_tes = Disjunction(m.T, rule= D_rule_tes)

    # Disjunction for investment in each of the technologies
    def disjInvestZero(block, g):
        model = block.model()
        block.c1 = Constraint(expr=model.b_g[g] == 0)
        block.c2 = Constraint(expr=sum(model.gen[g, t] for t in m.T) == 0)

    m.dinvzero = Disjunct(m.G, rule=disjInvestZero)

    def disjInvest(block, g):
        model = block.model()
        block.c1 = Constraint(expr=model.b_g[g] == 1)
        block.c2 = Constraint(expr=sum(model.gen[g, t] for t in m.T) >= 0)
    m.dinvest = Disjunct(m.G, rule=disjInvest)

    def D_rule_P(block, g):
        model = block.model()
        return [model.dinvest[g], model.dinvzero[g]]
    m.D_g_invest = Disjunction(m.G, rule=D_rule_P)

    #Heat
    def disjInvestZero(block, h):
        model = block.model()
        block.c1 = Constraint(expr=model.b_h[h] == 0)
        block.c2 = Constraint(expr=sum(model.heat[h, t] for t in m.T) == 0)
    m.d_h_invzero = Disjunct(m.H, rule=disjInvestZero)

    def disjInvest(block, h):
        model = block.model()
        block.c1 = Constraint(expr=model.b_h[h] == 1)
        block.c2 = Constraint(expr=sum(model.heat[h, t] for t in m.T) >= 0)
    m.d_h_invest = Disjunct(m.H, rule=disjInvest)

    def D_rule_Q(block, h):
        model = block.model()
        return [model.d_h_invest[h], model.d_h_invzero[h]]
    m.D_h_invest = Disjunction(m.H, rule=D_rule_Q)

    """Objective"""
    # Minimize electricity from grid
    def OBJ_import_min(model):
        return sum(m.p_imp[t] for t in m.T)
    #m.o2 = Objective(rule=OBJ_import_min, sense=minimize)

    # Minimize cost
    def OBJ_cost_min(model):
        investment = sum(m.C_g_invest[g] * m.b_g[g] for g in m.G) + \
                     sum(m.C_h_invest[h] for h in m.H) + m.C_pv_invest + m.C_st_invest
        maintenance = sum(m.C_g_maint[g] * m.b_g[g] for g in m.G) + sum(m.C_h_maint[h] * m.b_h[h] for h in m.H) + m.C_pv_maint + m.C_st_maint
        generator_operation = sum(m.C_g_fuel[g] * m.gen[g, t] / m.P_eta[g] for g in m.G for t in m.T)
        heat_operation = sum(m.C_h_fuel[h] * m.heat[h, t] / m.Q_eta[h] for h in m.H for t in m.T)
        fuel_cost = generator_operation + heat_operation
        certificate_savings = sum(m.pv[t] for t in m.T) * m.C_gc
        import_costs = sum(m.p_imp[t] * m.C_imp[t] for t in m.T) + sum(m.dh[t] * m.C_dh_entar[t] for t in m.T)
        emission_costs = m.C_co2 * (sum(m.Fi_g[g] * m.gen[g, t] / m.P_eta[g] for g in m.G for t in m.T) + \
                                    sum(m.C_co2 * m.Fi_h[h] * m.heat[h, t] / m.Q_eta[h] for h in m.H for t in m.T))
        grid_power_costs = (m.C_grid_power * 200 + m.C_fixtar) * m.period * 1.25
        dh_grid_costs = (calc_dh_power_cost(m,m.period) + m.C_dh_fixed) * 1.25
        export_costs = sum(m.p_exp[t] * m.C_exp[t] for t in m.T)
        return fuel_cost + import_costs + investment + maintenance + grid_power_costs + dh_grid_costs -\
               export_costs - certificate_savings
    m.o = Objective(rule= OBJ_cost_min, sense= minimize)

    return m

def initiate_black_out(m,t,duration):
    i = 1
    while i <= duration:
        m.Max_grid[t] = 0
        t += 1
        i += 1
    return()

def initiate_maintainance(m,t,duration):
    i = 1
    while i <= duration:
        m.gen[2,t].fix(0)
        t += 1
        i += 1
    return()

def calc_total_cost(m):
    generator_operation = sum(m.C_g_fuel[g] * m.gen[g, t].value / m.P_eta[g] for g in m.G for t in m.T)
    heat_operation = sum(m.C_h_fuel[h] * m.heat[h, t].value / m.Q_eta[h] for h in m.H for t in m.T)
    fuel_cost = generator_operation + heat_operation
    import_costs = sum(m.p_imp[t].value * m.C_imp[t] for t in m.T) + sum(m.dh[t].value * m.C_dh_entar[t] for t in m.T)
    emission_costs = m.C_co2 * (sum(m.Fi_g[g] * m.gen[g, t].value / m.P_eta[g] for g in m.G for t in m.T) + \
                                sum(m.C_co2 * m.Fi_h[h] * m.heat[h, t].value / m.Q_eta[h] for h in m.H for t in m.T))
    grid_power_costs = (m.C_grid_power * 200 + m.C_fixtar) * m.period * 1.25
    dh_grid_costs = (calc_dh_power_cost(m, m.period) + m.C_dh_fixed) * 1.25
    investment = sum(m.C_g_invest[g] * m.b_g[g].value for g in m.G) + sum(m.C_h_invest[h] * m.b_h[h].value for h in m.H) + m.C_pv_invest + m.C_st_invest
    maintenance = sum(m.C_g_maint[g] * m.b_g[g].value for g in m.G) + sum(m.C_h_maint[h] * m.b_h[h].value for h in m.H) + m.C_pv_maint + m.C_st_maint
    export_costs = sum(m.p_exp[t].value * m.C_exp[t] for t in m.T)
    certificate_savings = sum(m.pv[t] for t in m.T) * m.C_gc

    return fuel_cost + import_costs + investment + maintenance + grid_power_costs + dh_grid_costs - export_costs - certificate_savings

def calc_dh_power_cost(m,period):
    short = [2]
    medium = [4,6,8,9,11]
    long = [1,3,5,7,10,12]
    if period <= 1/52:
        c_dh_power = m.C_dh_power[1] * max(m.dh[t].value for t in m.T) * 0.25
    else:
        start_day = 1
        c_dh_power = 0
        for month in range(1,13):
            if month in short:
                days = 28
            elif month in medium:
                days = 30
            elif month in long:
                days = 31
            c_dh_power += \
                max(m.dh[t].value for t in range(start_day*24,start_day*24+days*24)) * m.C_dh_power[start_day*24+1]
            start_day += days
    return c_dh_power

def calc_emissions(m):
    emissions = sum(m.gen[g, t].value * m.Fi_g[g] for g in m.G for t in m.T) + \
    sum(m.heat[h, t].value * m.Fi_h[h] for h in m.H for t in m.T) + \
    sum(m.p_imp[t].value * m.Fi_grid[t] + m.dh[t].value * m.Fi_dh for t in m.T)
    return emissions