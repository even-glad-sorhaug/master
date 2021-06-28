function plot_storage(res)

figure('Name',res('file'));
h = 1:max(res('hours'));

subplot(2,1,1)
plot(h,res('Bat_stat'),'LineWidth',0.6)
axis([0 max(h) 0 max(res('Bat_stat'))]);
legend({'V_{Bat}'},'Location','northeastoutside');
ylabel('Stored Energy [kWh]');
title('Battery')

subplot(2,1,2)
plot(h,res('Tes_stat'),'LineWidth',0.5)
axis([0 max(h) -inf max(res('Tes_stat'))]);
ylabel('Stored Heat [kWh]');
yyaxis right
plot(h,res('Temp'),'--','LineWidth',0.5);
ylabel('Temperature [\circC]')
axis([0 max(h) (min(res('Temp'))-5) (max(res('Temp'))+10)]);
title('Thermal Storage')
legend({'V_{Tes}'},'Location','northeastoutside');

end %func



