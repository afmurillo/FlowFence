clc;
clear all;
close all;

dropped = [0.12, 0.38, 0.36, 0.25, 0.53, 0.75, 0.76, 1.15, 2.0]

figure(1)

plot(dropped, '-k*');

hold on;

txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');

ylabel('Dropped packets (%)')
title('Dropped packets during Iperf UDP tests')