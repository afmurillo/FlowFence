clc;
clear all;
close all;

numBytes_1 = csvread('bytes_1.txt');
numBytes_2 = csvread('bytes_2.txt');
numBytes_3 = csvread('bytes_3.txt');

plot(numBytes_1, 'b');
hold on
plot(numBytes_2, 'k');
plot(numBytes_3, 'r');
txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');
grid on
