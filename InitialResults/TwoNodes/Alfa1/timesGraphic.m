clc;
clear all;
close all;

pingNoAttackTimes = csvread('httpPerfNoAttack/times.txt');
pingAttackTimes = csvread('httpPerfAttack/times.txt');
pingDefenseTimes = csvread('httpPerfDefense/times.txt');

httpNoAttackOuts = csvread('httpPerfNoAttack/outs.txt');
httpAttackOuts = csvread('httpPerfAttack/outs.txt');
httpDefenseOuts = csvread('httpPerfDefense/outs.txt');

httpNoAttackNwk= csvread('httpPerfNoAttack/nwk.txt');
httpAttackNwk = csvread('httpPerfAttack/nwk.txt');
httpDefenseNwk = csvread('httpPerfDefense/nwk.txt');

figure(1)

%boxplot(times,'labels',{'With no attack', 'With attack and no Flowfence', 'With attack and Flowfence'});
a = subplot(1,3,1)

boxplot(pingNoAttackTimes, 'labels',{'No attack'});
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on

b=subplot(1,3,2)
boxplot(pingAttackTimes, 'labels',{'Attack and no Flowfence'});
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on

subplot(1,3,3)
boxplot(pingDefenseTimes, 'labels',{'Attack and Flowfence'});
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on

ylabel(a,'Reply Time (ms)')
title(b, 'Client HTTP Perf Reply Time')

figure(2)
a = subplot(1,3,1)

boxplot(httpNoAttackOuts, 'labels',{'No attack'});
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on

b=subplot(1,3,2)
boxplot(httpAttackOuts, 'labels',{'Attack and no Flowfence'});
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on

subplot(1,3,3)
boxplot(httpDefenseOuts, 'labels',{'Attack and Flowfence'});
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on

ylabel(a,'Number of timeouts')
title(b, 'Connection timeouts')



figure(3)
a = subplot(1,3,1)

boxplot(httpNoAttackNwk, 'labels',{'No attack'});
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on

b=subplot(1,3,2)
boxplot(httpAttackNwk, 'labels',{'Attack and no Flowfence'});
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on

subplot(1,3,3)
boxplot(httpDefenseNwk, 'labels',{'Attack and Flowfence'});
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on

ylabel(a,'KB/s')
title(b, 'Network Throughput')



% meanUdp100=[meanTxUdpPkts_1' meanRoutedUdpPkts_1' meanRxUdpPkts_1'];
% 
% figure(2)
% boxplot(meanUdp100,'labels',{'Transmitidos', 'Recebidos Roteador', 'Recebidos Servidor'});


% 
% results=importdata('filesNames.csv');
% 
% numTests=7;
% meanTx = zeros(numTests,1);
% meanRx = zeros(numTests,1);
% 
% for i=1:numTests
%     auxStr = strcat(results{i},'/tx_flows_1.txt');     
%     auxTx = csvread(auxStr);
%     meanTx(i,1) = mean(auxTx);
% end
% 
% for i=1:numTests
%     auxStr = strcat(results{i},'/routed_flows_1.txt');
%     auxRouted = csvread(auxStr);
%     meanRouted(i,1) = mean(auxRouted);
% end
% 
% for i=1:numTests
%     auxStr = strcat(results{i},'/rx_flows_1.txt');
%     auxRx = csvread(auxStr);
%     meanRx(i,1) = mean(auxRx);
% end
% 
% format long g
% 
% meanTx
% meanRouted
% meanRx
% 
% figure(2)
% plot(meanTx, 'b');
% plot(auxTx, 'b');
% hold on
%plot(auxRouted, 'k');
%plot(auxRx, 'r');
%hold on;
%plot(meanRx, 'k');

% 
% meanUdp100=[meanTxUdpPkts_1' meanRoutedUdpPkts_1' meanRxUdpPkts_1'];
% 
% figure(2)
% boxplot(meanUdp100,'labels',{'Transmitidos', 'Recebidos Roteador', 'Recebidos Servidor'});
% 
% title('Pacotes por Segundo Inundação UDP Pacotes 1 byte com DETER Flooder')
% txt = findobj(gca,'Type','text');
% set(findobj(gca,'Type','text'),'FontSize',25)
% set(txt(1:end),'VerticalAlignment', 'Middle');
% grid on
% ylabel('Pacotes por Segundo')
% 
