clear all;
close all;
clc

attackers = [50, 150, 300, 450];

mean_defense_reply_time = zeros(1,4);
mean_no_defense_reply_time = zeros(1,4);

two_nodes_defense =[3.2, 7.6, 5.7, 3.1, 4.1];
two_nodes_no_defense =[20.0, 26.5, 20.0, 20.0, 11.3];

four_nodes_defense = [4.8, 6.0, 4.0];
four_nodes_no_defense = [22.5, 15.6, 24.4];

seven_nodes_defense = [11.7, 19.5, 9.8];
seven_nodes_no_defense = [21.9, 33.3, 42.1];

ten_nodes_defense = [14.2, 15.0, 20.0];
ten_nodes_no_defense = [70.9, 24.2, 30.9];


mean_defense_reply_time(1) = mean(two_nodes_defense);
mean_no_defense_reply_time(1) = mean(two_nodes_no_defense);

mean_defense_reply_time(2) = mean(four_nodes_defense);
mean_no_defense_reply_time(2) = mean(four_nodes_no_defense);

mean_defense_reply_time(3) = mean(seven_nodes_defense);
mean_no_defense_reply_time(3) = mean(seven_nodes_no_defense);

mean_defense_reply_time(4) = mean(ten_nodes_defense);
mean_no_defense_reply_time(4) = mean(ten_nodes_no_defense);

figure(1)

plot(attackers, mean_defense_reply_time,'-b');

hold on;
grid on;

plot(attackers, mean_no_defense_reply_time,'-r');

txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20);
set(txt(1:end),'VerticalAlignment', 'Middle');

ylabel('Reply Time (ms)')
xlabel('Bandwidth Used by Attackers (mbits/s)')
title('Reply Time Obtained with HTTP Perf by Legitimate Client')

