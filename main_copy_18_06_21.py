"""

Optimization model for a microgrid with fuel cell chp
    =====================================

    (c) Even Glad Sørhaug, March 2021

    ====================================

"""
import warnings

import numpy as np


from model import *
import model_base_case as mbc
#from model_storage_optimization import *
from pyomo.environ import *
from data import *
import pandas as pd
# import numpy as np
import time

start_time = time.time()
#warnings.filterwarnings("ignore")

#---------------------------------------------------------------------------------#
# For optimizing multiple cases in dict. Imin (T/F) indicates whether import should be minimized. Default is only Cmin
def multiple_cases(dict,Imin,fc,summary_file_name):
    # Runs simulations for multiple cases and stores the results in separate files
    system_data = dict
    #system_data = {1: "system_data.xls"}
    solver = SolverFactory('gurobi')
    year_list = ["system_data.xls", "system_data_2050.xls","system_data_no_dh_2050.xls","system_data_no_dh.xls"]
    summary = create_summary_matrix()
    n = 1
    for key in system_data.keys():
        m = build_model(system_data[key])
        TransformationFactory('core.logical_to_linear').apply_to(m)
        TransformationFactory('gdp.bigm').apply_to(m)

        if system_data[key] in year_list:
            maintenance = [1000,2000,3000,4000,5000,6000]
            for t in maintenance:
                initiate_maintainance(m,t,'bio',97)
        for i in range(1,3):
            if i == 2 and Imin:
                m.o = Objective(expr= sum(m.p_imp[t] for t in m.T), sense= minimize)
                m.output = m.output.value.replace("_fc.xlsx","_import_min.xlsx")
                for t in m.T:
                    m.gen[2, t].unfix()
            elif i == 2:
                break
            for j in range (1,4):
                if j == 1:
                    if fc:
                        m.gen[1,1].fix(m.P_max[1])
                    m.output = m.output.value.replace(".xlsx", "_bio_fc.xlsx")
                elif j == 2:
                    for t in m.T:
                        m.gen[1, t].fix(0)
                    m.output = m.output.value.replace("_bio_fc.xlsx", "_bio.xlsx")
                elif j == 3:
                    for t in m.T:
                        m.gen[1, t].unfix()
                        if fc:
                            m.gen[1, 1].fix(m.P_max[1])
                        m.gen[2, t].fix(0)
                    m.output = m.output.value.replace("_bio.xlsx", "_fc.xlsx")

                #Calling the solver
                results = solver.solve(m)
                results.write(num=1)
                solver.options['Solfiles.xlsx'] = 'solution'

                calc_fractions(m, n, summary)
                n += 1

                print("Model " + system_data[key] + " was solved successfully after :")
                print("--- %s seconds ---" % (time.time() - start_time))
                print("\n\n")

                Results_to_file(m)
    summary_file(summary, summary_file_name)

def multiple_cases_strategic_fc_control(dict,Imin,summary_file_name):
    # Runs simulations for multiple cases and stores the results in separate files
    system_data = dict
    #system_data = {1: "system_data.xls"}
    solver = SolverFactory('gurobi')
    year_list = ["system_data.xls", "system_data_2050.xls", "system_data_no_dh_2050.xls", "system_data_no_dh.xls"]
    summary = create_summary_matrix()
    n = 1
    for key in system_data.keys():
        m = build_model(system_data[key])
        TransformationFactory('core.logical_to_linear').apply_to(m)
        TransformationFactory('gdp.bigm').apply_to(m)


        pause = [3625]
        for t in pause:
            initiate_maintainance(m,t,"fc",2928)
        maintenance = [1000, 2000, 3000, 4000, 5000, 6000]
        for t in maintenance:
            initiate_maintainance(m, t, 'bio', 97)
        for i in range(1,3):
            if i == 2 and Imin:
                m.o = Objective(expr= sum(m.p_imp[t] for t in m.T), sense= minimize)
                m.output = m.output.value.replace("_fc.xlsx","_import_min.xlsx")
                for t in m.T:
                    m.gen[2, t].unfix()
            elif i == 2:
                break
            for j in range (1,4):
                if j == 1:
                    m.output = m.output.value.replace(".xlsx", "_bio_fc.xlsx")
                elif j == 2:
                    for t in m.T:
                        m.gen[1, t].fix(0)
                    m.output = m.output.value.replace("_bio_fc.xlsx", "_bio.xlsx")
                elif j == 3:
                    for t in m.T:
                        m.gen[1, t].unfix()
                        for t in pause:
                            initiate_maintainance(m, t, "fc", 2928)
                        m.gen[2, t].fix(0)
                    m.output = m.output.value.replace("_bio.xlsx", "_fc.xlsx")

                #Calling the solver
                results = solver.solve(m)

                calc_fractions(m, n, summary)
                n += 1

                print("Model " + system_data[key] + " was solved successfully after :")
                print("--- %s seconds ---" % (time.time() - start_time))
                print("\n\n")

                Results_to_file(m)
    summary_file(summary, summary_file_name)

# For calculating cost with just DH and electricity grid.
def multiple_cases_base_case(dict,summary_file_name):
    # Runs simulations for multiple cases and stores the results in separate files
    system_data = dict
    #system_data = {1: "system_data.xls"}
    solver = SolverFactory('gurobi')

    summary = create_summary_matrix()
    n = 1
    for key in system_data.keys():
        m = mbc.build_model_base_case(system_data[key])
        TransformationFactory('core.logical_to_linear').apply_to(m)
        TransformationFactory('gdp.bigm').apply_to(m)

        #Calling the solver
        results = solver.solve(m)

        calc_fractions_base_case(m, n, summary)
        n += 1

        print("Model " + system_data[key] + " was solved successfully after :")
        print("--- %s seconds ---" % (time.time() - start_time))
        print("\n\n")

        Results_to_file(m)
    summary_file(summary, summary_file_name)

# For optimizing multiple cases with blackout during either "day"- or "night"-time. Lasts for 1 hour
def multiple_cases_blackout(dict,blackout,sf_name):
    # Runs simulations for multiple cases and stores the results in separate files
    system_data = dict
    year_list = ["system_data.xls","system_data_2050.xls"]
    solver = SolverFactory('gurobi')

    summary = create_summary_matrix()
    n = 1
    for key in system_data.keys():
        for c in range(1,3):
            m = build_model(system_data[key])
            TransformationFactory('core.logical_to_linear').apply_to(m)
            TransformationFactory('gdp.bigm').apply_to(m)
            if system_data[key] in year_list:
                maintenance = [1000,2000,3000,4000,5000,6000]
                for t in maintenance:
                    initiate_maintainance(m,t,'bio',97)
            if blackout == "day":
                if c == 2:
                    m.output = m.output.value.replace(".xlsx", "_storage_empty.xlsx")
                    m.v_bat[15].fix(0)
                initiate_black_out(m,16,2)
                m.output = m.output.value.replace(".xlsx", "_blackout_day.xlsx")
                print(m.output.value)
            elif blackout == "night":
                if c == 2:
                    m.v_bat[15].fix(0)
                    m.output = m.output.value.replace(".xlsx", "_storage_empty.xlsx")
                initiate_black_out(m,27,2)
                m.output = m.output.value.replace(".xlsx", "_blackout_night.xlsx")
                print(m.output.value)
            for i in range(1,3):
                if i == 2:
                    m.o = Objective(expr= sum(m.p_imp[t] for t in m.T), sense= minimize)
                    m.output = m.output.value.replace("_fc.xlsx","_import_min.xlsx")
                    for t in m.T:
                        m.gen[2, t].unfix()
                for j in range (1,4):
                    if j == 1:
                        m.output = m.output.value.replace(".xlsx", "_bio_fc.xlsx")
                    elif j == 2:
                        for t in m.T:
                            m.gen[1, t].fix(0)
                        m.output = m.output.value.replace("_bio_fc.xlsx", "_bio.xlsx")
                    elif j == 3:
                        for t in m.T:
                            m.gen[1, t].unfix()
                            m.gen[2, t].fix(0)
                        m.output = m.output.value.replace("_bio.xlsx", "_fc.xlsx")

                    #Calling the solver
                    results = solver.solve(m)

                    calc_fractions(m, n, summary)
                    n += 1

                    print("Model " + system_data[key] + " was solved successfully after :")
                    print("--- %s seconds ---" % (time.time() - start_time))
                    print("\n\n")

                    Results_to_file(m)
    summary_file(summary, sf_name)
    return()

# For optimizing one single case. No summary is stored.
def single_case(data):
    solver = SolverFactory('gurobi')

    m = build_model(data)
    TransformationFactory('core.logical_to_linear').apply_to(m)
    TransformationFactory('gdp.bigm').apply_to(m)

    results = solver.solve(m)
    Results_to_file(m)

    print("Model " + data + " was solved successfully after :")
    print("--- %s seconds ---" % (time.time() - start_time))
    print("\n\n")
    return()
# For optimizing n weeks. Summary stored.
def multiple_cases_weekly(data,summary_file_name,n):
    solver = SolverFactory('gurobi')
    start = 1
    summary = create_summary_matrix()

    k = 1

    for i in range(1,n+1):
        m = build_model_weekly(data,start)
        TransformationFactory('core.logical_to_linear').apply_to(m)
        TransformationFactory('gdp.bigm').apply_to(m)

        path = ""
        results = solver.solve(m)
        f_name = "results_cdhpw_week_" + str(i) + ".xlsx"
        m.output = f_name

        calc_fractions(m, k, summary)
        k += 1

        Results_to_file(m)

        print("Model " + data + " was solved successfully after :")
        print("--- %s seconds ---" % (time.time() - start_time))
        print("\n\n")

        start = start + 168
    summary_file(summary, summary_file_name)
    return()

# For optimizing storage technologies
#def single_storage_case(data):
    #solver = SolverFactory('gurobi')

    #m = build_storage_model(data)
    #TransformationFactory('core.logical_to_linear').apply_to(m)
    #TransformationFactory('gdp.bigm').apply_to(m)

    #results = solver.solve(m)
    #Results_to_file(m)

    #print("Model " + data + " was solved successfully after :")
    #print("--- %s seconds ---" % (time.time() - start_time))
    #print("\n\n")

    #print("Battery capacity: ", m.v_bat_cap.value)
    #print("Thermal capacity: ", m.v_tes_cap.value)
    #return()
#Sensitivity analysis for hydrogen prices. Increases costs by inc
def sensitivity_analysis_h2(dict,Imin,fixed,summary_file_name,inc):
    # Runs simulations for multiple cases and stores the results in separate files
    system_data = dict
    #system_data = {1: "system_data.xls"}
    solver = SolverFactory('gurobi')
    year_list = ["system_data.xls", "system_data_2050.xls", "system_data_no_dh_2050.xls", "system_data_no_dh.xls"]
    summary = create_summary_matrix()
    n = 1
    for key in system_data.keys():
        m = build_model(system_data[key])
        TransformationFactory('core.logical_to_linear').apply_to(m)
        TransformationFactory('gdp.bigm').apply_to(m)

        hp = 0.4
        if system_data[key] in year_list:
            maintenance = [1000,2000,3000,4000,5000,6000]
            for t in maintenance:
                initiate_maintainance(m,t,'bio',97)
        for h in range(1,30):
            hp += inc
            h_suffix = "_" + str(round(hp,1))
            suffix = h_suffix + ".xlsx"
            m.C_g_fuel[1] = hp/33
            if h == 1:
                m.output = m.output.value.replace(".xlsx", suffix)
            for i in range(1,3):
                if i == 2 and Imin:
                    m.o = Objective(expr= sum(m.p_imp[t] for t in m.T), sense= minimize)
                    m.output = m.output.value.replace("_fc.xlsx","_import_min.xlsx")
                elif i == 2:
                    break
                for j in range (1,3-fixed):
                    if j == 1:
                        for t in m.T:
                            m.gen[2, t].unfix()
                        if fixed:
                            m.b_g[1].fix(1)
                            for t in m.T:
                                m.gen[2, t].fix(0)
                            m.output = m.output.value.replace("_" + str(round(hp - inc, 1)) + "_fc.xlsx", suffix)
                            m.output = m.output.value.replace(".xlsx", "_fc.xlsx")
                        else:
                            m.output = m.output.value.replace("_" + str(round(hp-inc,1)) + "_fc.xlsx", suffix)
                            m.output = m.output.value.replace(".xlsx", "_bio_fc.xlsx")
                    elif j == 2:
                        for t in m.T:
                            m.gen[1, t].unfix()
                            m.gen[2, t].fix(0)
                        m.output = m.output.value.replace("_bio_fc.xlsx", "_fc.xlsx")

                    #Calling the solver
                    results = solver.solve(m)
                    print("\n\n")
                    print("The objective for " + str(hp) + " is : ")
                    results.write(num=1)
                    print("\n\n")

                    solver.options['Solfiles.xlsx'] = 'solution'

                    calc_fractions(m, n, summary)
                    n += 1

                    print("Model " + system_data[key] + " was solved successfully after :")
                    print("--- %s seconds ---" % (time.time() - start_time))
                    print("\n\n")

                    Results_to_file(m)
    summary_file(summary, summary_file_name)

def sensitivity_analysis_el(dict,Imin,fixed,summary_file_name,inc):
    # Runs simulations for multiple cases and stores the results in separate files
    system_data = dict
    #system_data = {1: "system_data.xls"}
    solver = SolverFactory('gurobi')
    year_list = ["system_data.xls", "system_data_2050.xls", "system_data_no_dh_2050.xls", "system_data_no_dh.xls"]
    summary = create_summary_matrix()
    n = 1



    for key in system_data.keys():
        sp = 0.4
        for k in range(1,17):
            sp += inc
            m = build_model_el(system_data[key],sp)
            TransformationFactory('core.logical_to_linear').apply_to(m)
            TransformationFactory('gdp.bigm').apply_to(m)

            if system_data[key] in year_list:
                maintenance = [1000,2000,3000,4000,5000,6000]
                for t in maintenance:
                    initiate_maintainance(m,t,'bio',97)

            s_suffix = "_" + str(round(sp,1))
            suffix = s_suffix + ".xlsx"
            if k == 1:
                m.output = m.output.value.replace(".xlsx", suffix)
            for i in range(1,3):
                if i == 2 and Imin:
                    m.o = Objective(expr= sum(m.p_imp[t] for t in m.T), sense= minimize)
                    m.output = m.output.value.replace("_fc.xlsx","_import_min.xlsx")
                elif i == 2:
                    break
                for j in range (1,3-fixed):
                    if j == 1:
                        for t in m.T:
                            m.gen[2, t].unfix()
                        if fixed:
                            m.b_g[1].fix(1)
                            for t in m.T:
                                m.gen[2, t].fix(0)
                            m.output = m.output.value.replace("_" + str(round(sp - inc, 1)) + "_fc.xlsx", suffix)
                            m.output = m.output.value.replace(".xlsx", "_fc.xlsx")
                        else:
                            m.output = m.output.value.replace("_" + str(round(sp-inc,1)) + "_fc.xlsx", suffix)
                            m.output = m.output.value.replace(".xlsx", "_bio_fc.xlsx")
                    elif j == 2:
                        for t in m.T:
                            m.gen[1, t].unfix()
                            m.gen[2, t].fix(0)
                        m.output = m.output.value.replace("_bio_fc.xlsx", "_fc.xlsx")

                    #Calling the solver
                    results = solver.solve(m)
                    print("\n\n")
                    print("The objective for " + str(sp) + " is : ")
                    results.write(num=1)
                    print("\n\n")

                    calc_fractions(m, n, summary)
                    n += 1

                    print("Model " + system_data[key] + " was solved successfully after :")
                    print("--- %s seconds ---" % (time.time() - start_time))
                    print("\n\n")

                    Results_to_file(m)
    summary_file(summary, summary_file_name)

def calc_fractions(m, n, summary):
    summary[1][n] = m.output.value.replace("results_", "")
    summary[2][n] = sum(m.P_dem[t] for t in m.T)
    summary[3][n] = sum(m.pv[t] for t in m.T)
    summary[4][n] = sum(m.gen[1, t].value for t in m.T)
    summary[5][n] = sum(m.gen[2, t].value for t in m.T)
    summary[6][n] = sum(m.p_imp[t].value for t in m.T)
    summary[23][n] = sum(m.boiler[t].value for t in m.T)
    summary[26][n] = sum(m.u_gen[1,t].value for t in m.T)
    summary[28][n] = sum(m.Q_dem[t] for t in m.T)/sum(m.P_dem[t] for t in m.T)
    summary[29][n] = sum(m.C_exp[t] for t in m.T)/m.hours.value
    summary[30][n] = sum(m.p_imp[t].value * m.C_imp[t] for t in m.T) +\
                     (m.C_grid_power*max(m.p_imp[t].value for t in m.T) + m.C_fixtar) * m.period * 1.25
    summary[31][n] = (mod.calc_dh_power_cost(m,m.period,m.start) + m.C_dh_fixed) * 1.25 +\
                    sum(m.dh[t].value * m.C_dh_entar[t] for t in m.T)

    summary[7][n] = sum(m.Q_dem[t] for t in m.T)
    summary[8][n] = sum(m.st[t] for t in m.T)
    summary[9][n] = sum(m.gen[1, t].value * m.chp[1] for t in m.T)
    summary[10][n] = sum(m.gen[2, t].value * m.chp[2] for t in m.T)
    summary[25][n] = sum(m.heat[1,t].value for t in m.T)
    summary[11][n] = sum(m.dh[t].value for t in m.T)

    summary[12][n] = sum(m.p_bat_ch[t].value for t in m.T)
    summary[13][n] = sum(m.eta_bat * m.p_bat_dis[t].value for t in m.T)
    summary[14][n] = sum(m.q_tes_ch[t].value for t in m.T)
    summary[15][n] = sum(m.eta_bat * m.q_tes_dis[t].value for t in m.T)
    summary[21][n] = summary[13][n]-summary[12][n]
    summary[22][n] = summary[15][n]-summary[14][n]

    summary[16][n] = calc_total_cost(m)
    summary[17][n] = calc_emissions(m)
    summary[18][n] = sum(m.p_exp[t].value for t in m.T)
    summary[27][n] = sum(m.Temp[t] for t in m.T)/m.hours.value

    self_generation = ((summary[2][n]-summary[6][n])+(summary[7][n]-summary[11][n]))/(summary[2][n]+summary[7][n])
    summary[24][n] = self_generation
    return summary

def calc_fractions_base_case(m, n, summary):
    summary[1][n] = m.output.value.replace("results_", "")
    summary[2][n] = sum(m.P_dem[t] for t in m.T)
    summary[3][n] = sum(m.pv[t] for t in m.T)
    summary[4][n] = 0
    summary[5][n] = 0
    summary[6][n] = sum(m.p_imp[t].value for t in m.T)
    summary[23][n] = sum(m.boiler[t].value for t in m.T)
    summary[26][n] = 0
    summary[28][n] = sum(m.Q_dem[t] for t in m.T) / sum(m.P_dem[t] for t in m.T)
    summary[29][n] = sum(m.C_exp[t] for t in m.T) / m.hours.value

    summary[7][n] = sum(m.Q_dem[t] for t in m.T)
    summary[8][n] = sum(m.st[t] for t in m.T)
    summary[9][n] = 0
    summary[10][n] = 0
    summary[25][n] = 0
    summary[11][n] = sum(m.dh[t].value for t in m.T)

    summary[12][n] = sum(m.p_bat_ch[t].value for t in m.T)
    summary[13][n] = sum(m.eta_bat * m.p_bat_dis[t].value for t in m.T)
    summary[14][n] = sum(m.q_tes_ch[t].value for t in m.T)
    summary[15][n] = sum(m.eta_bat * m.q_tes_dis[t].value for t in m.T)
    summary[21][n] = summary[13][n]-summary[12][n]
    summary[22][n] = summary[15][n]-summary[14][n]

    summary[16][n] = mbc.calc_total_cost(m)
    summary[17][n] = calc_emissions(m)
    summary[18][n] = sum(m.p_exp[t].value for t in m.T)
    summary[27][n] = sum(m.Temp[t] for t in m.T) / m.hours.value

    self_generation = ((summary[2][n]-summary[6][n])+(summary[7][n]-summary[11][n]))/(summary[2][n]+summary[7][n])
    summary[24][n] = self_generation
    return summary

def summary_file(summary,sf_name):
    kpi = {}
    kpi["Case"] = summary[1]
    kpi["Total cost"] = summary[16]
    kpi["Emissions"] = summary[17]
    kpi["Self-generation"] = summary[24]
    kpi["fc_hours"] = summary[26]
    kpi["TEr"] = summary[28]
    kpi["T_mean"] = summary[27]
    kpi["Spot_mean"] = summary[29]
    kpi["el_price"] = summary[30]
    kpi["dh_price"] = summary[31]

    fractions = {}
    fractions["Case"] = summary[1]
    fractions["P_demand"] = summary[2]
    fractions["P_pv"] = summary[3]
    fractions["P_fc"] = summary[4]
    fractions["P_bio"] = summary[5]
    fractions["P_imp"] = summary[6]
    fractions["P_exp"] = summary[18]
    fractions["Boiler"] = summary[23]
    fractions["V_bat_ch"] = summary[12]
    fractions["V_bat_dis"] = summary[13]
    fractions["Q_demand"] = summary[7]
    fractions["Q_st"] = summary[8]
    fractions["Q_fc"] = summary[9]
    fractions["Q_bio"] = summary[10]
    fractions["Q_dh"] = summary[11]
    fractions["Q_heater"] = summary[25]
    fractions["V_tes_ch"] = summary[14]
    fractions["V_tes_dis"] = summary[15]

    kpi = pd.DataFrame(kpi)
    fractions = pd.DataFrame(fractions)

    path = "summaries\\" + sf_name
    with pd.ExcelWriter(path) as writer:
        kpi.to_excel(writer, sheet_name="KPI")
        fractions.to_excel(writer, sheet_name="Total power")
    print("Summary stored in file: " + path)
    print("\n\n")

def create_summary_matrix():
    case = {}
    total_cost = {}
    emissions = {}
    self_generation = {}
    T_mean = {}
    TEr = {}
    Spot_mean = {}
    el_price = {}
    dh_price = {}

    p_dem = {}
    p_pv = {}
    p_fc = {}
    p_bio = {}
    p_import = {}
    p_export = {}
    fc_hours = {}
    boiler = {}

    q_dem = {}
    q_st = {}
    q_fc = {}
    q_bio = {}
    q_dh = {}
    q_heater = {}

    v_bat_ch = {}
    v_bat_dis = {}
    v_tes_ch = {}
    v_tes_dis = {}
    v_bat_end = {}
    v_tes_end = {}
    v_bat_loss = {}
    v_tes_loss = {}

    summary = {1:case,2:p_dem,3:p_pv,4:p_fc,5:p_bio,6:p_import,7:q_dem,8:q_st,9:q_fc,10:q_bio, 11:q_dh,12:v_bat_ch,\
               13:v_bat_dis,14:v_tes_ch,15:v_tes_dis,16:total_cost,17:emissions,18:p_export,19:v_bat_end,20:v_tes_end,\
               21:v_bat_loss,22:v_tes_loss,23:boiler,24:self_generation,25:q_heater,26:fc_hours,27:T_mean,28:TEr,\
               29:Spot_mean,30:el_price,31:dh_price}
    return summary

#---------------------------------------------------------------------------------#
""" 
Databases
"""

summer_winter = {1:"system_data_winter.xls",2:"system_data_summer.xls"}
summer = {1:"system_data_summer.xls"}
winter = {1:"system_data_winter.xls"}
months = {1:"system_data_month_january.xls",2:"system_data_month_february.xls",3:"system_data_month_march.xls",\
          4:"system_data_month_april.xls",5:"system_data_month_may.xls",6:"system_data_month_june.xls",\
          7:"system_data_month_july.xls",8:"system_data_month_august.xls",9:"system_data_month_september.xls",\
          10:"system_data_month_october.xls",11:"system_data_month_november.xls",12:"system_data_month_december.xls"}
year = {1:"system_data.xls"}
year_2050 = {1:"system_data_2050.xls"}
years = {1:"system_data.xls",2:"system_data_2050.xls"}
year_no_dh = {1:"system_data_no_dh.xls"}
year_no_dh_2050 = {1:"system_data_no_dh_2050.xls"}
years_no_dh = {1:"system_data_no_dh.xls",2:"system_data_no_dh_2050.xls"}
base_cases = {1:"system_data_year_base_case.xls",2:"system_data_year_no_solar_base_case.xls",3:"system_data_winter_base_case.xls",\
              4:"system_data_winter_no_solar_base_case.xls",5:"system_data_summer_base_case.xls",6:"system_data_summer_no_solar_base_case.xls"}
no_solar_base_cases = {1:"system_data_year_no_solar_base_case.xls",2:"system_data_winter_no_solar_base_case.xls",3:"system_data_summer_no_solar_base_case.xls"}

""" 
Cases 
"""

#multiple_cases(summer_winter, True, False, "summary_summer_winter.xlsx")
#multiple_cases_blackout(summer_winter, "day","summary_summer_winter_blackout_day.xlsx")
#multiple_cases_blackout(summer_winter, "night","summary_summer_winter_blackout_night.xlsx")

"""Multiple weeks"""
# calc_dh_power_cost_old
#multiple_cases_weekly("system_data_2050.xls","summary_weekly_constant_dhpw.xlsx",52)
# calc_dh_power_cost_new
#multiple_cases_weekly("system_data_2050.xls","summary_weekly_constant_dhpw.xlsx",52)

"""Year cases with IMin for 2020 and 2050"""
#multiple_cases(year, False, True, "summary_year_forced.xlsx")
multiple_cases(year_2050, False, False, "summary_year_2050.xlsx")
#multiple_cases_strategic_fc_control(year_2050, True, "summary_year_2050_fc_control_jun_sep.xlsx")

"""Sensitivity analysis"""
#sensitivity_analysis_h2(years, False, True, "summary_year_sa_h2.xlsx",0.1)
#sensitivity_analysis_el(years, False, True,"summary_year_sa_el_forced.xlsx",0.1)

"""Multiple months"""
# calc_dh_power_cost_old
#multiple_cases(months,False, False, "summary_months_2050.xlsx")
# calc_dh_power_cost_new
#multiple_cases(months,False, False, "summary_months_2050_constant_dhpw.xlsx")

"""Year cases with IMin for 2020 and 2050 including no district heating"""
#multiple_cases(year_no_dh, False, False, "summary_year_new_no_dh.xlsx")
#multiple_cases(year_no_dh_2050, False, False, "summary_year_no_dh_2050.xlsx")

"""Base cases"""
#multiple_cases_base_case(base_cases,"summary_base_cases.xlsx")


