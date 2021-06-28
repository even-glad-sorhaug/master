function plot_electricity(res)

figure('Name',res('file'));
h = 1:max(res('hours'));


subplot(2,1,1)
plot(h,res('D_el'),h,res('Power1'),h,res('Power2'),h,res('Import'),'LineWidth',0.7)
axis([0 max(h) 0 inf]);
legend({'Demand_{El}','FC','Bio','Grid'},'Location','northeastoutside');
ylabel('Electric power [kWh/h]');
title('Electricity dispatch')

subplot(2,1,2)
plot(h,res('D_heat'),h,res('CHP1'),h,res('CHP2'),h,res('DH'),'LineWidth',0.7)
axis([0 max(h) 0 (max(res('D_heat'))+50)]);
ylabel('Stored Heat [kWh]');
yyaxis right
plot(h,res('Temp'),'--','LineWidth',0.7);
ylabel('Temperature [\circC]')
axis([0 max(h) (min(res('Temp'))-5) (max(res('Temp'))+10)]);
title('Thermal Storage')
legend({'D_{Heat}','FC','Bio','DH'},'Location','northeastoutside');

end %func