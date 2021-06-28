import numpy as np
import pandas as pd
import math
import re

def prepare_power_coordinate_file(summary, fo):
    file_directory = "summaries\\"
    i = 1
    result = {}
    result[0] = "k x y"

    for file in summary.values():
        df = pd.read_excel(file_directory+file, sheet_name="Total power")
        df = df.set_index(df.columns[0])  # First column is index
        num = len(df.loc[:])  # Length of dataframe
        df = df.to_dict()  # Convert sheet to dictionary

        for key in df.keys():
            for n in range(num):
            #p_dem = df["P_demand"][n+1]
                #print(df[key][n+1])
                if key != "Case":
                    case = tokenize_case_name(df["Case"][n + 1], True)
                    if case.find("IMin") == -1:
                        if key != "V_bat_dis":
                            result[i] = key + " " + str(abs(round(0.001*df[key][n+1],3))) + " " + case
                        else:
                            v_bat_loss = abs(round(0.001 * df["V_bat_ch"][n + 1], 3)) - abs(round(0.001 * df[key][n + 1], 3))
                            result[i] = "V_bat_loss " + str(round(v_bat_loss,3)) + " " + case
                        #print(result[n])
                        i += 1
    path = "latex_txt_files\\" + fo
    with open(path, 'w') as f:
        for key in result:
            print(result[key], file=f)

def prepare_kpi_coordinate_file(summary, fo):
    file_directory = "summaries\\"
    i = 1
    result = {}
    result[0] = "c x y"

    for file in summary.values():
        df = pd.read_excel(file_directory+file, sheet_name="KPI")
        df = df.set_index(df.columns[0])  # First column is index
        num = len(df.loc[:])  # Length of dataframe
        df = df.to_dict()  # Convert sheet to dictionary

        for key in df.keys():
            for n in range(num):
                # p_dem = df["P_demand"][n+1]
                # print(df[key][n+1])
                if key != "Case":
                    case = tokenize_case_name(df["Case"][n + 1], True)
                    if case.find("import") == -1:
                        result[i] = key + " " + str(abs(round(df[key][n+1],3))) + " " + case
                        # print(result[n])
                        i += 1

    path = "latex_txt_files\\" + fo
    with open(path, 'w') as f:
        for key in result:
            print(result[key], file=f)

def preare_economic_coordinates(results, fo, battery_cost):
    file_directory = "file_storage\\"
    i = 1
    result = {}
    result[0] = "c n x y"
    only_totals = ["Import","Export","Ceritificates","DH","Emission_cost","Total_cost","Fixed_Tarifs","Emissions"]

    for file in results.values():
        df = pd.read_excel(file_directory+file, sheet_name="Economics")
        df = df.set_index(df.columns[0])  # First column is index
        num = len(df.loc[:])  # Length of dataframe
        df = df.to_dict()  # Convert sheet to dictionary

        case = tokenize_case_name(file,True)

        for n in range(num):
            if n == 0:
                for key in df.keys():
                    if key != "Name":
                        if df[key][n + 1] is np.NaN:
                            value = 0
                        elif key == "Invest":
                            value = df[key][n + 1] + battery_cost
                        else:
                            value = df[key][n + 1]
                        result[i] = df["Name"][n+1].replace(" ","") + " " + key.replace(" ","_") + " " + str(abs(round(value,3))) + " " + case
                        # print(result[n])
                        i += 1
            else:
                for key in df.keys():
                    if key not in only_totals and key != "Name":
                        if math.isnan(df[key][n + 1]):
                            value = 0
                        else:
                            value = df[key][n + 1]
                        result[i] = df["Name"][n + 1].replace(" ","") + " " + key.replace(" ","_") + " " + str(value) + " " + case
                        i += 1
    path = "latex_txt_files\\" + fo
    with open(path, 'w') as f:
        for key in result:
            print(result[key], file=f)

def prepare_kpi_scatter_file(summary, imp_min, fo):
    file_directory = "summaries\\"
    i = 1
    letter = 'a'
    result = {}
    result[0] = "c cost emi self hours ter tmean spotmean elprice dhprice l"

    for file in summary.values():
        df = pd.read_excel(file_directory+file, sheet_name="KPI")
        df = df.set_index(df.columns[0])  # First column is index
        num = len(df.loc[:])  # Length of dataframe
        df = df.to_dict()  # Convert sheet to dictionary

        for n in range(num):
            string = ""
            case = tokenize_case_name(df["Case"][n + 1], True)
            if case.find("Imin") == -1 and imp_min == False:
                for key in df.keys():
                    string = string + str(abs(round(df[key][n+1],3))) + " "
                    i += 1
                string = string + letter
                result[i] = string
                letter = chr(ord(letter) + 1)
            elif imp_min == True:
                for key in df.keys():
                    value = df[key][n+1]
                    if key == "Self-generation":
                        value = round(value*100,3)
                    if value is num:
                        string = string + str(abs(round(value,3))) + " "
                    else:
                        string = string + str(value) + " "
                    i += 1
                string = string + letter
                result[i] = string
                letter = chr(ord(letter) + 1)
                if letter > 'f':
                    letter = 'a'

    path = "latex_txt_files\\" + fo
    with open(path, 'w') as f:
        for key in result:
            print(result[key], file=f)

def prepare_kpi_table(summary, imp_min, fo):
    file_directory = "summaries\\"
    i = 1
    letter = 'a'
    result = {}
    incl = ["Total cost","Self-generation","Emissions"]
    result[0] = "c cost emi self hours ter tmean spotmean elprice dhprice l"

    for file in summary.values():
        df = pd.read_excel(file_directory+file, sheet_name="KPI")
        df = df.set_index(df.columns[0])  # First column is index
        num = len(df.loc[:])  # Length of dataframe
        df = df.to_dict()  # Convert sheet to dictionary

        for n in range(num):
            string = ""
            case = tokenize_case_name(df["Case"][n + 1], True)
            if case.find("Imin") == -1 and imp_min == False:
                print("nop3")
            elif imp_min == True:
                cost = str(abs(round(df["Total cost"][n+1])))
                if len(cost) > 3:
                    cost = cost[:len(cost)-3] + "," + cost[len(cost)-3:]
                selfgen = str(abs(round(df["Self-generation"][n+1]*100,1)))
                emissions = str(abs(round(df["Emissions"][n + 1] / 1000)))
                if len(emissions) > 3:
                    emissions = emissions[:len(emissions)-3] + "," + emissions[len(emissions)-3:]
                string += cost + " & " + selfgen + " & " + emissions + " & - & - \\\\"
                i += 1
                result[i] = string

    path = "latex_txt_files\\" + fo
    with open(path, 'w') as f:
        for key in result:
            print(result[key], file=f)

#------------------------#
"""
Side functions
"""
def tokenize_case_name(name,duration):
    case = ""
    dur = ["year","summer","winter"]
    year = ["2020","2050"]
    chp = ["fc","bio"]
    outage = ["day","night"]
    special = ["import","empty"]

    list = re.split('_|\.',name)
    for item in list:
        if item in dur and duration:
            case += item[0].upper()
            duration = False
        elif item in chp:
            case += "+" + item.upper()
        elif item in outage:
            case += "+PO" + item[0].upper()
        elif item in special:
            case += "+IMin"
        elif item in special:
            case += "+Empty"
    return case

summary = {1:"summary_summer_winter.xlsx",2:"summary_summer_winter_blackout_day.xlsx",\
               3:"summary_summer_winter_blackout_night.xlsx"}
summary_summer_winter = {1:"summary_summer_winter.xlsx"}
summary_summer_winter_blackout = {1:"summary_summer_winter_blackout_day.xlsx",2:"summary_summer_winter_blackout_night.xlsx"}
summary_year = {1:"summary_year.xlsx"}
summary_year_2050 = {1:"summary_year_2050.xlsx"}

results_summer_winter_no_imin = {1:"results_winter_bio.xlsx",2:"results_winter_bio_fc.xlsx",3:"results_winter_fc.xlsx",\
                  4:"results_summer_bio.xlsx",5:"results_summer_bio_fc.xlsx",6:"results_summer_fc.xlsx"}
results_summer_winter = {1:"results_winter_bio.xlsx",2:"results_winter_bio_fc.xlsx",3:"results_winter_fc.xlsx",\
                  4:"results_summer_bio.xlsx",5:"results_summer_bio_fc.xlsx",6:"results_summer_fc.xlsx", \
                  7: "results_winter_import_min_bio.xlsx", 8: "results_winter_import_min_bio_fc.xlsx",9: "results_winter_import_min_fc.xlsx", \
                  10: "results_summer_import_min_bio.xlsx", 11: "results_summer_import_min_bio_fc.xlsx",12: "results_summer_import_min_fc.xlsx"}
results_winter = {1:"results_winter_bio.xlsx",2:"results_winter_bio_fc.xlsx",3:"results_winter_fc.xlsx"}
results_summer = {1:"results_summer_bio.xlsx",2:"results_summer_bio_fc.xlsx",3:"results_summer_fc.xlsx"}
results_years = {1:"results_year_bio.xlsx",2:"results_year_bio_fc.xlsx",3:"results_year_fc.xlsx",\
4: "results_year_import_min_bio.xlsx", 5: "results_year_import_min_bio_fc.xlsx",6: "results_year_import_min_fc.xlsx", \
7:"results_2050_year_bio.xlsx",8:"results_2050_year_bio_fc.xlsx",9:"results_2050_year_fc.xlsx",\
                  10: "results_2050_year_import_min_bio.xlsx", 11: "results_2050_year_import_min_bio_fc.xlsx",12: "results_2050_year_import_min_fc.xlsx"}

results_summer_winter_blackout_day = {1:"results_winter_blackout_day_bio.xlsx",2:"results_winter_blackout_day_bio_fc.xlsx",\
                               3:"results_winter_blackout_day_fc.xlsx",4:"results_summer_blackout_day_bio.xlsx",5:"results_summer_blackout_day_bio_fc.xlsx",\
                               6:"results_summer_blackout_day_fc.xlsx",7:"results_winter_storage_empty_blackout_day_bio.xlsx",\
                               8:"results_winter_storage_empty_blackout_day_bio_fc.xlsx",9:"results_winter_storage_empty_blackout_day_fc.xlsx",\
                               10:"results_summer_storage_empty_blackout_day_bio.xlsx",11:"results_summer_storage_empty_blackout_day_bio_fc.xlsx",\
                               12:"results_summer_storage_empty_blackout_day_fc.xlsx"}
results_summer_winter_blackout_night = {1:"results_winter_blackout_night_bio.xlsx",2:"results_winter_blackout_night_bio_fc.xlsx",\
                               3:"results_winter_blackout_night_fc.xlsx",4:"results_summer_blackout_night_bio.xlsx",5:"results_summer_blackout_night_bio_fc.xlsx",\
                               6:"results_summer_blackout_night_fc.xlsx",7:"results_winter_storage_empty_blackout_night_bio.xlsx",\
                               8:"results_winter_storage_empty_blackout_night_bio_fc.xlsx",9:"results_winter_storage_empty_blackout_night_fc.xlsx",\
                               10:"results_summer_storage_empty_blackout_night_bio.xlsx",11:"results_summer_storage_empty_blackout_night_bio_fc.xlsx",\
                               12:"results_summer_storage_empty_blackout_night_fc.xlsx"}
##
results_winter_blackout_day = {1:"results_winter_blackout_day_bio.xlsx",2:"results_winter_blackout_day_bio_fc.xlsx",\
                               3:"results_winter_blackout_day_fc.xlsx",4:"results_winter_blackout_day_import_min_bio.xlsx",\
                               5:"results_winter_blackout_day_import_min_bio_fc.xlsx",6:"results_winter_blackout_day_import_min_fc.xlsx"}
results_summer_blackout_day = {1:"results_summer_blackout_day_bio.xlsx",2:"results_summer_blackout_day_bio_fc.xlsx",\
                               3:"results_summer_blackout_day_fc.xlsx",4:"results_summer_blackout_day_import_min_bio.xlsx",\
                               5:"results_summer_blackout_day_import_min_bio_fc.xlsx",6:"results_summer_blackout_day_import_min_fc.xlsx"}
results_winter_blackout_night = {1:"results_winter_blackout_night_bio.xlsx",2:"results_winter_blackout_night_fc.xlsx",\
                               3:"results_winter_blackout_night_fc.xlsx",4:"results_winter_blackout_night_import_min_bio.xlsx",\
                               5:"results_winter_blackout_night_import_min_bio_fc.xlsx",6:"results_winter_blackout_night_import_min_fc.xlsx"}
results_summer_blackout_night = {1:"results_summer_blackout_night_bio.xlsx",2:"results_summer_blackout_night_bio_fc.xlsx",\
                               3:"results_summer_blackout_night_fc.xlsx",4:"results_summer_blackout_night_import_min_bio.xlsx",\
                               5:"results_summer_blackout_night_import_min_bio_fc.xlsx",6:"results_summer_blackout_night_import_min_fc.xlsx"}
results_winter_blackout_day_empty_store = {1:"results_winter_storage_empty_blackout_day_bio.xlsx",2:"results_winter_storage_empty_blackout_day_bio_fc.xlsx",\
                               3:"results_winter_storage_empty_blackout_day_fc.xlsx",4:"results_winter_storage_empty_blackout_day_import_min_bio.xlsx",\
                               5:"results_winter_storage_empty_blackout_day_import_min_bio_fc.xlsx",6:"results_winter_storage_empty_blackout_day_import_min_fc.xlsx"}
results_summer_blackout_day_empty_store = {1:"results_summer_storage_empty_blackout_day_bio.xlsx",2:"results_summer_storage_empty_blackout_day_bio_fc.xlsx",\
                               3:"results_summer_storage_empty_blackout_day_fc.xlsx",4:"results_summer_storage_empty_blackout_day_import_min_bio.xlsx",\
                               5:"results_summer_storage_empty_blackout_day_import_min_bio_fc.xlsx",6:"results_summer_storage_empty_blackout_day_import_min_fc.xlsx"}
results_winter_blackout_night_empty_store = {1:"results_winter_storage_empty_blackout_night_bio.xlsx",2:"results_winter_storage_empty_blackout_night_fc.xlsx",\
                               3:"results_winter_storage_empty_blackout_night_fc.xlsx",4:"results_winter_storage_empty_blackout_night_import_min_bio.xlsx",\
                               5:"results_winter_storage_empty_blackout_night_import_min_bio_fc.xlsx",6:"results_winter_storage_empty_blackout_night_import_min_fc.xlsx"}
results_summer_blackout_night_empty_store = {1:"results_summer_storage_empty_blackout_night_bio.xlsx",2:"results_summer_storage_empty_blackout_night_bio_fc.xlsx",\
                               3:"results_summer_storage_empty_blackout_night_fc.xlsx",4:"results_summer_storage_empty_blackout_night_import_min_bio.xlsx",\
                               5:"results_summer_storage_empty_blackout_night_import_min_bio_fc.xlsx",6:"results_summer_storage_empty_blackout_night_import_min_fc.xlsx"}

#----------------------------------------------------------------------------#
#----------------------------------------------------------------------------#

prepare_power_coordinate_file(summary_summer_winter,"coord_power_summer_winter.txt")
prepare_power_coordinate_file(summary_year,"coord_power_year.txt")
prepare_power_coordinate_file(summary_year_2050,"coord_power_year_2050.txt")

prepare_kpi_coordinate_file(summary_summer_winter,"coord_kpi_summer_winter.txt")
prepare_kpi_coordinate_file(summary_summer_winter_blackout,"coord_kpi_summer_winter_blackout.txt")

prepare_kpi_scatter_file(summary_summer_winter,True,"scatter_kpi_summer_winter.txt")
prepare_kpi_scatter_file(summary_summer_winter_blackout,True,"scatter_kpi_summer_winter_blackout.txt")

preare_economic_coordinates(results_summer_winter,"coord_economic_summer_winter.txt",254.03)
preare_economic_coordinates(results_summer_winter_blackout_day,"coord_economic_summer_winter_blackout_day.txt",254.03)
preare_economic_coordinates(results_summer_winter_blackout_day,"coord_economic_summer_winter_blackout_night.txt",254.03)
preare_economic_coordinates(results_years,"coord_economic_years.txt",13209.5)

prepare_kpi_table(summary_year_2050,True,"table_kpi_2050.txt")
prepare_kpi_table(summary_year,True,"table_kpi_2020.txt")
prepare_kpi_table(summary_summer_winter,True,"table_kpi_summer_winter.txt")
