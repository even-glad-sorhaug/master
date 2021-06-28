res_summer = get_data('results_week_summer.xlsx')
res_winter = get_data('results_week_winter.xlsx')
plot_storage(res_summer);
plot_storage(res_winter);

plot_electricity(res_summer);
plot_electricity(res_winter);
