clear all;
close all;
clc

%%% Iperf test with attackers doing iperf

attackers = [50, 150, 300, 450];

mean_defense_bw = zeros(1,4);
mean_no_defense_bw = zeros(1,4);

one_node_defense = [54.45, 28.06, 29.62];
one_node_no_defense = [19.71, 18.98, 18.06];

four_node_defense = [21.73, 21.95, 17.27];
four_node_no_defense =  [0.98, 1.18, 0.93];

seven_nodes_defense = [13.37, 20.84, 11.46];
seven_nodes_no_defense = [0.31, 2.36, 1.46];

ten_nodes_defense = [9.50, 4.78, 5.36];
ten_nodes_no_defense = [1.62, 2.47, 0.55];


mean_defense_bw(1) = mean(one_node_defense);
mean_no_defense_bw(1) = mean(one_node_no_defense);

mean_defense_bw(2) = mean(four_node_defense)
mean_no_defense_bw(2) = mean(four_node_no_defense);

mean_defense_bw(3) = mean(seven_nodes_defense)
mean_no_defense_bw(3) = mean(seven_nodes_no_defense);

mean_defense_bw(4) = mean(ten_nodes_defense);
mean_no_defense_bw(4) = mean(ten_nodes_no_defense);

figure(1)

plot(attackers, mean_defense_bw,'-b');

hold on;
grid on;

plot(attackers, mean_no_defense_bw,'-r');

txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20);
set(txt(1:end),'VerticalAlignment', 'Middle');

ylabel('Bandwidth Obtained by Legitimate Client (mbits/s)')
xlabel('Bandwidth Used by Attackers (mbits/s)')
title('Bandwidth Obtained by Legitimate Client using Iperf')




