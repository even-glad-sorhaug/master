"""

Optimization model for a microgrid with fuel cell chp
    =====================================

    (c) Even Glad Sørhaug, March 2021

    ====================================

"""
import model as mod
import numpy as np
import sys
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory


def Data_fetch(system_data):
    Data = Get_Data(system_data)

    # Create matrices for the lines and cables
    Demand = Demand_matrices(Data)
    Prod = Prod_matrices(Data)
    Base = Base_data(Data)
    Storage = Storage_matrices(Data)

    return Demand, Prod, Base, Storage

def Get_Data(Data):

    result = {}

    Excel_sheets = ["Sources",  "Demand", "Solar", "Grid", "Storage", "Declarations"]     #Sheet names in book
    Data_Names = {"Sources":"PowerSources",  "Demand":"LoadDemand",\
                  "Solar":"SolarProd", "Grid":"Grid", "Storage":"Storage", "Declarations":"BaseData"} #Names for data for each sheet
    Num_Names = {"Sources":"NumSources", "Demand":"NumDemand", "Solar":"NumSolar",\
                 "Grid":"NumGrid", "Storage":"NumStorage", "Declarations":"NumData"}      #Names for numbering
    List_Names = {"Sources": "SourceList","Demand":"DemandList", "Solar":"SolarList",\
                  "Grid":"GridList", "Storage":"StorageList", "Declarations":"DataList"}   #Names for numbering

    for sheet in Excel_sheets:          #For each sheet
        df = pd.read_excel(Data, sheet_name = sheet)  #Read sheet

        df = df.set_index(df.columns[0])        #First column is index
        num = len(df.loc[:])            # Length of dataframe
        df = df.to_dict()               #Convert sheet to dictionary

        df[Num_Names[sheet]] = num
        df[List_Names[sheet]] = np.arange(1,num+1)

        result[Data_Names[sheet]] = df

        #End for


    return(result)

def Results_to_file(model):

    #Dictionaries for data
    GeneratorData = {}

    #Data for each generator
    Heat = {}
    PV = {}
    ST = {}
    P_imp = {}
    P_exp = {}
    DH = {}
    El_Demand = {}
    Heat_Demand = {}
    v_bat = {}
    P_bat_ch = {}
    P_bat_dis = {}
    v_tes = {}
    Q_tes_ch = {}
    Q_tes_dis = {}
    Boiler = {}
    Temp = {}

    # Utility
    for t in model.T:
        El_Demand[t] = round(model.P_dem[t], 2)
        Heat_Demand[t] = round(model.Q_dem[t], 2)
        P_imp[t] = round(model.p_imp[t].value, 2)
        P_exp[t] = round(model.p_exp[t].value, 2)
        DH[t] = round(model.dh[t].value, 2)
        PV[t] = round(model.pv[t], 2)
        ST[t] = round(model.st[t], 2)
        v_bat[t] = round(model.v_bat[t].value, 2)
        P_bat_ch[t] = round(model.p_bat_ch[t].value, 2)
        P_bat_dis[t] = round(model.eta_bat * model.p_bat_dis[t].value, 2)
        v_tes[t] = round(model.v_tes[t].value, 2)
        Q_tes_ch[t] = round(model.q_tes_ch[t].value, 2)
        Q_tes_dis[t] = round(model.eta_tes * model.q_tes_dis[t].value, 2)
        Boiler[t] = round(model.boiler[t].value, 2)
        Temp[t] = round(model.Temp[t], 2)

    GeneratorData["D_el"] = El_Demand
    GeneratorData["D_heat"] = Heat_Demand
    GeneratorData["PV"] = PV
    GeneratorData["ST"] = ST
    GeneratorData["Bat_stored"] = v_bat
    GeneratorData["Bat_ch"] = P_bat_ch
    GeneratorData["Bat_dis"] = P_bat_dis
    GeneratorData["TES_stored"] = v_tes
    GeneratorData["TES_ch"] = Q_tes_ch
    GeneratorData["TES_dis"] = Q_tes_dis
    GeneratorData["Boiler"] = Boiler

    # Generator data
    for n in model.G:
        gen_name = "Power " + str(n)
        chp_name = "CHP " + str(n)
        #binary_name = "Binary" + str(n)
        Power = {}
        CHP = {}
        U_gen = {}
        for t in model.T:
            Power[t] = round(model.gen[n,t].value, 2)
            CHP[t] = round(model.chp[n]*model.gen[n,t].value, 2)
            U_gen[t] = model.u_gen[n,t].value
        GeneratorData[gen_name] = Power
        GeneratorData[chp_name] = CHP
        #GeneratorData[binary_name] = U_gen
    # Heat data
    for n in model.H:
        heat_name = "Heat " + str(n)
        for t in model.T:
            Heat[t] = round(model.heat[n, t].value, 2)
        GeneratorData[heat_name] = Heat

    #Store generator data
    GeneratorData["Import"] = P_imp
    GeneratorData["Export"] = P_exp
    GeneratorData["DH"] = DH

    # Totals and hours of work
    generator_totals = {1:{},2:{}}
    heater_totals = {}
    g = 1
    h = 1
    for key in GeneratorData.keys():
        total = sum(GeneratorData[key].values())
        hours = 0
        for t in model.T:
            if GeneratorData[key][t] != 0:
                hours += 1
        if "Power" in key:
            generator_totals[1][g] = total
            generator_totals[2][g] = sum(GeneratorData["CHP " + str(g)].values())
            g += 1
        elif "Heat" in key:
            heater_totals[h] = total
            h += 1
        GeneratorData[key]["Total"] = total
        GeneratorData[key]["Hours"] = hours

    #Temperature
    GeneratorData["Temp"] = Temp

    #Convert dictionaries to dataframes
    GeneratorData = pd.DataFrame(data=GeneratorData)
    print(GeneratorData)

    """
    Economic data
    """

    EconomicData = {}

    # Utility exchange
    Import = {1:sum(model.p_imp[t].value * model.C_imp[t] for t in model.T)}
    Export = {1:sum(model.p_exp[t].value * model.C_exp[t] for t in model.T)}
    DH_cost = (mod.calc_dh_power_cost(model,model.period,model.start) + model.C_dh_fixed) * 1.25 +\
              sum(model.dh[t].value * model.C_dh_entar[t] for t in model.T)
    #For constant dh pw
    #DH_cost = (4.4*max(model.dh) + model.C_dh_fixed) * 1.25 +sum(model.dh[t].value * model.C_dh_entar[t] for t in model.T)
    DH = {1:DH_cost}
    Fixed_tarif = {1:(model.C_grid_power*200 + model.C_fixtar) * model.period * 1.25}
    #Certificates = {1:sum(model.C_g_fuel[2] * model.gen[2, t].value / model.P_eta[2] + model.pv[t] for t in model.T) * model.C_gc}
    Certificates = {1: sum(model.pv[t] for t in model.T) * model.C_gc}

    # For each generator unit
    i = 1
    Name = {}
    Name[i] = "Total"
    Maint = {}
    Maint[i] = sum(model.C_g_maint[g] * model.b_g[g].value for g in model.G) + sum(model.C_h_maint[h] * model.b_h[h].value for h in model.H) + model.C_pv_maint + model.C_st_maint
    Invest = {}
    Invest[i] = sum(model.C_g_invest[g] * model.b_g[g].value for g in model.G) + sum(model.C_h_invest[h] * model.b_h[h].value for h in model.H) + model.C_pv_invest + model.C_st_invest
    Fuel = {}
    Fuel[i] = sum(model.C_g_fuel[g].value * model.gen[g, t].value / model.P_eta[g] for g in model.G for t in model.T) + \
              sum(model.C_h_fuel[h] * model.heat[h, t].value / model.Q_eta[h] for h in model.H for t in model.T)
    Emissions = {}
    Emissions[i] = mod.calc_emissions(model)
    LCOE = {}
    LCOE[i] = 0

    for n in model.G:
        name = "Power " + str(n)
        i += 1
        Name[i] = name
        Maint[i] = model.C_g_maint[n] * model.b_g[n].value
        Invest[i] = model.C_g_invest[n] * model.b_g[n].value
        Fuel[i] = sum(model.C_g_fuel[n].value * model.gen[n, t].value / model.P_eta[n] for t in model.T)
        Emissions[i] = sum(model.gen[n, t].value * model.Fi_g[n] for t in model.T)
        LCOE[i] = calc_lcoe(generator_totals[1][n],generator_totals[2][n],Invest[i],Maint[i],Fuel[i])

    # Heat data
    for n in model.H:
        name = "Heat " + str(n)
        i += 1
        Name[i] = name
        Maint[i] = model.C_h_maint[n] * model.b_h[n].value
        Invest[i] = model.C_h_invest[n] * model.b_h[n].value
        Fuel[i] = sum(model.C_h_fuel[n] * model.heat[n, t].value / model.Q_eta[n] for t in model.T)
        Emissions[i] = sum(model.heat[n, t].value * model.Fi_h[n] for t in model.T)
        LCOE[i] = calc_lcoe(0,heater_totals[n],Invest[i],Maint[i],Fuel[i])

    i += 1
    Name[i] = "PV"
    Maint[i] = model.C_pv_maint.value
    Invest[i] = model.C_pv_invest.value
    LCOE[i] = calc_lcoe(GeneratorData["PV"]["Total"], 0, model.C_pv_invest.value, model.C_pv_maint.value, 0)
    i += 1
    Name[i] = "ST"
    Maint[i] = model.C_st_maint.value
    Invest[i] = model.C_st_invest.value
    LCOE[i] = calc_lcoe(0, GeneratorData["ST"]["Total"], model.C_st_invest.value, model.C_st_maint.value, 0)

    emission_costs = {1:model.C_co2 * (sum(model.Fi_g[g] * model.gen[g, t].value / model.P_eta[g] for g in model.G for t in model.T) + \
                                sum(model.Fi_h[h] * model.heat[h, t].value / model.Q_eta[h] for h in model.H for t in model.T))}
    Total_cost = {1:Invest[1] + Maint[1] + Fuel[1] + Import[1] + DH[1] + Fixed_tarif[1] - Export[1] - Certificates[1]}

    # LCOE
    Name[i+1] = "El Grid"
    Name[i+2] = "DH"
    LCOE[i+1] = calc_lcoe(GeneratorData["Import"]["Total"],0,Fixed_tarif[1],0,Import[1])    # Electricity from grid LCOE
    LCOE[i+2] = calc_lcoe(0,GeneratorData["ST"]["Total"],0,0,DH[1])                         # Heat from grid LCOE

    EconomicData["Name"] = Name
    EconomicData["Invest"] = Invest
    EconomicData["Fuel"] = Fuel
    EconomicData["Maint"] = Maint
    EconomicData["Import"] = Import
    EconomicData["Export"] = Export
    EconomicData["Certificates"] = Certificates
    EconomicData["DH"] = DH
    EconomicData["Grid_Tariffs"] = Fixed_tarif
    EconomicData["Emission_costs"] = emission_costs
    EconomicData["Total_cost"] = Total_cost
    EconomicData["Emissions"] = Emissions
    EconomicData["LCOE"] = LCOE

    EconomicData = pd.DataFrame(data= EconomicData)
    # Decide what the name of the output file should be
    output_file = model.output.value

    # Store each result in an excel file, given a separate sheet
    path = "file_storage\\" + output_file
    with pd.ExcelWriter(path) as writer:
        GeneratorData.to_excel(writer, sheet_name="Energy")
        EconomicData.to_excel(writer, sheet_name="Economics")

    print("\n\n")
    print("Results stored in: " + path)
    print("Everything went well!")
    print("\n\n")

def Base_data(Data):

    Base = {}

    # Base data
    Base["r"] = Data["BaseData"]["Value"][1]
    Base["Grid_max"] = Data["BaseData"]["Value"][2]
    Base["DH_max"] = Data["BaseData"]["Value"][3]
    Base["Fixed_tarif"] = Data["BaseData"]["Value"][4]
    Base["Energy_tarif"] = Data["BaseData"]["Value"][5]
    Base["Power_tarif"] = Data["BaseData"]["Value"][6]
    Base["DH_cost"] = Data["BaseData"]["Value"][7]
    Base["DH_fixed"] = Data["BaseData"]["Value"][8]
    Base["DH_em"] = Data["BaseData"]["Value"][9]
    Base["Emission_cost"] = Data["BaseData"]["Value"][10]
    Base["GC_cost"] = Data["BaseData"]["Value"][11]
    Base["Days"] = Data["BaseData"]["Value"][12]
    Base["File_name"] = Data["BaseData"]["Value"][13]

    return(Base)

def Storage_matrices(Data):
    Storage = {}

    #Energy storage data

    Capacity = {}
    Eta_ch = {}
    Eta_dis = {}
    Max_dis = {}
    Start = {}
    Max_dod = {}
    Lifetime = {}
    Invest = {}
    Cap_min = {}
    Cap_max = {}

    for n in range(1,Data["Storage"]["NumStorage"]+1):
        Capacity[n] = Data["Storage"]["Capacity"][n]
        Eta_ch[n] = Data["Storage"]["Eta_ch"][n]
        Eta_dis[n] = Data["Storage"]["Eta_dis"][n]
        Max_dis[n] = Data["Storage"]["Max_dis"][n]
        Start[n] = Data["Storage"]["Start"][n]
        Max_dod[n] = Data["Storage"]["Max_dod"][n]
        Lifetime[n] = Data["Storage"]["Lifetime"][n]
        Invest[n] = Data["Storage"]["Invest"][n]
        Cap_min[n] = Data["Storage"]["cap_min"][n]
        Cap_max[n] = Data["Storage"]["cap_max"][n]


    Storage["Capacity"] = Capacity
    Storage["Eta_ch"] = Eta_ch
    Storage["Eta_dis"] = Eta_dis
    Storage["Max_dis"] = Max_dis
    Storage["Start"] = Start
    Storage["Max_dod"] = Max_dod
    Storage["Lifetime"] = Lifetime
    Storage["Invest"] = Invest
    Storage["Cap_min"] = Cap_min
    Storage["Cap_max"] = Cap_max
    return(Storage)

def Demand_matrices(Data):
    Demand = {}

    #Electricity demand

    P_el = np.zeros(Data["LoadDemand"]["NumDemand"])
    for n in range(1,Data["LoadDemand"]["NumDemand"]+1):
        P_el[n-1] = Data["LoadDemand"]["Electric hourly [kW]"][n]

    #Heat for space heating
    Q_sh = np.zeros(Data["LoadDemand"]["NumDemand"])
    for n in range(1,Data["LoadDemand"]["NumDemand"]+1):
        Q_sh[n-1] = Data["LoadDemand"]["Space heating hourly [kW]"][n]

    #Heat for hot water
    Q_hw = np.zeros(Data["LoadDemand"]["NumDemand"])
    for n in range(1,Data["LoadDemand"]["NumDemand"]+1):
        Q_hw[n-1] = Data["LoadDemand"]["DHW hourly [kW]"][n]

    # Heat for hot water
    Temp = np.zeros(Data["LoadDemand"]["NumDemand"])
    for n in range(1, Data["LoadDemand"]["NumDemand"] + 1):
        Temp[n - 1] = Data["LoadDemand"]["Temperature outdoor [°C]"][n]

    Demand["P_el"] = P_el
    Demand["Q_sh"] = Q_sh
    Demand["Q_hw"] = Q_hw
    Demand["Temp"] = Temp
    return(Demand)

def Prod_matrices(Data):
    Production = {}

    PV = {}
    ST = {}
    PVmaint = {}
    STmaint = {}

    spot = {}
    gridemi = {}
    dh_en_part = {}
    dh_pw_part = {}

    Pname = {}
    Pmin = {}
    Pmax = {}
    Pinvest = {}
    Pfuel_cost = {}
    Peta = {}
    Plifetime = {}
    Pemi = {}
    CHP = {}
    Pmaint = {}
    Phours_max = {}

    Qname = {}
    Qmin = {}
    Qmax = {}
    Qinvest = {}
    Qfuel_cost = {}
    Qeta = {}
    Qlifetime = {}
    Qemi = {}
    Qmaint = {}
    Qhours_max = {}

    #Electric generators
    i = 1
    for n in range(1, Data["PowerSources"]["NumSources"] + 1):
        power = Data["PowerSources"]["Electricity [kWe]"][n]
        if type(power) == int or type(power) == float:
            Pname[i] = Data["PowerSources"]["Source"][n]
            Pmin[i] = Data["PowerSources"]["Min [kW]"][n]
            Pmax[i] = Data["PowerSources"]["Max [kW]"][n]
            Pinvest[i] = Data["PowerSources"]["Investment"][n]
            Pfuel_cost[i] = Data["PowerSources"]["Fuel Cost"][n]
            Peta[i] = Data["PowerSources"]["Efficiency"][n]
            Plifetime[i] = Data["PowerSources"]["Lifetime"][n]
            Pemi[i] = Data["PowerSources"]["Emissions"][n]
            CHP[i] = Data["PowerSources"]["CHP"][n]
            Pmaint[i] = Data["PowerSources"]["O&M"][n]
            Phours_max[i] = Data["PowerSources"]["Max hours"][n]
            i += 1
        elif Data["PowerSources"]["Source"][n] == "PV":
            PVinvest = Data["PowerSources"]["Investment"][n]
            PVlifetime = Data["PowerSources"]["Lifetime"][n]
            PVmaint = Data["PowerSources"]["O&M"][n]
        elif Data["PowerSources"]["Source"][n] == "ST":
            STinvest = Data["PowerSources"]["Investment"][n]
            STlifetime = Data["PowerSources"]["Lifetime"][n]
            STmaint = Data["PowerSources"]["O&M"][n]

    i = 1

    # Heaters
    for n in range(1, Data["PowerSources"]["NumSources"] + 1):
        power = Data["PowerSources"]["Heat [kWth]"][n]
        if type(power) == int or type(power) == float:
            Qname[n - 1] = Data["PowerSources"]["Source"][n]
            Qmin[i] = Data["PowerSources"]["Min [kW]"][n]
            Qmax[i] = Data["PowerSources"]["Max [kW]"][n]
            Qinvest[i] = Data["PowerSources"]["Investment"][n]
            Qfuel_cost[i] = Data["PowerSources"]["Fuel Cost"][n]
            Qeta[i] = Data["PowerSources"]["Fuel Cost"][n]
            Qlifetime[i] = Data["PowerSources"]["Lifetime"][n]
            Qemi[i] = Data["PowerSources"]["Emissions"][n]
            Qmaint[i] = Data["PowerSources"]["O&M"][n]
            Qhours_max[i] = Data["PowerSources"]["Max hours"][n]
            i += 1

    # Solar
    for n in range(1, Data["SolarProd"]["NumSolar"] + 1):
        PV[n] = Data["SolarProd"]["PV"][n]
        ST[n] = Data["SolarProd"]["ST"][n]
        spot[n] = Data["Grid"]["Spot"][n]
        gridemi[n] = Data["Grid"]["Emission"][n]
        dh_en_part[n] = Data["Grid"]["dh_en_part"][n]
        dh_pw_part[n] = Data["Grid"]["dh_pw_part"][n]


    Production["Pname"] = Pname
    Production["Pmin"] = Pmin
    Production["Pmax"] = Pmax
    Production["Pinvest"] = Pinvest
    Production["Pfuel_cost"] = Pfuel_cost
    Production["Peta"] = Peta
    Production["Plifetime"] = Plifetime
    Production["Pemi"] = Pemi
    Production["Pmaint"] = Pmaint
    Production["Phours_max"] = Phours_max
    Production["CHP"] = CHP

    Production["Qname"] = Qname
    Production["Qmin"] = Qmin
    Production["Qmax"] = Qmax
    Production["Qinvest"] = Qinvest
    Production["Qfuel_cost"] = Qfuel_cost
    Production["Qeta"] = Qeta
    Production["Qlifetime"] = Qlifetime
    Production["Qemi"] = Qemi
    Production["Qmaint"] = Pmaint
    Production["Qhours_max"] = Phours_max

    Production["PV"] = PV
    Production["ST"] = ST
    Production["PVinvest"] = PVinvest
    Production["STinvest"] = STinvest
    Production["PV_lifetime"] = PVlifetime
    Production["ST_lifetime"] = STlifetime
    Production["PVmaint"] = PVmaint
    Production["STmaint"] = STmaint
    Production["Phours_max"] = Phours_max
    Production["Spot"] = spot
    Production["Gridemi"] = gridemi
    Production["DH_energy"] = dh_en_part
    Production["DH_power"] = dh_pw_part

    return Production

def calc_lcoe(power,heat,invest,maint,fuel):
    if power + heat == 0:
        lcoe = 0
    else:
        lcoe = (invest + maint + fuel) / (power + heat)
    return lcoe

#-------------------------------------------------------------------------#
#-------------------------Run Script From Here----------------------------#
#-------------------------------------------------------------------------#

