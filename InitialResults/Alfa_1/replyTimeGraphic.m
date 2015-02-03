clc;
clear all;
close all;

% [1,3,6,9] Flooders

%%%%%%%%%%%%%%%%%%%%%%%%%%%% REPLY TIME %%%%%%%%%%%%%%%%%%%%%%%%%%%%

flooders=[1,3,6,9];

meanTimeNoAttack = [ 0.5000 0.5000 0.5000 0.5000 ];
meanTimeAttack =   [ 369.4800 1660.82 1632.16 2802.5 ];
meanTimeDefense=   [ 18.2600 27.62   1385.1 921.04 ];

stdTimeNoAttack = [ 0.0707 0.0707 0.0707 0.0707 ];
stdTimeAttack =   [ 229.3887 918.077614910635 471.845894334157 1235.85535561408];
stdTimeDefense=   [ 10.0843 6.8316908595164 302.1680492706 428.202584065066];

figure(1)

plot(flooders,meanTimeNoAttack, '-k*');

hold on;
grid on;

plot(flooders,meanTimeAttack, '-r*');

plot(flooders,meanTimeDefense, '-b*');

txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');

ylabel('Reply Time (ms)')
title('Client HTTP Perf Reply Time')


%%%%%%%%%%%%%%%%%%%%%%%%%%%% CLIENT TIMEOUTS %%%%%%%%%%%%%%%%%%%%%%%%%%%%

meanOutNoAttack = [0 0 0 0 ];
meanOutAttack =   [85.8 95.6 97.2 97.2 ];
meanOutDefense=   [45.2 88.2 82.8 91.6];

stdOutNoAttack = [0 0 0 0 ];
stdOutAttack =   [2.38746727726266  1.67332005306815 2.16794833886788 1.48323969741913 ];
stdOutDefense=   [18.0333025261598 3.27108544675922 5.80517010948 4.03732584763727];
      
figure(2)

plot(flooders,meanOutNoAttack, '-k*');

hold on;
grid on;

plot(flooders,meanOutAttack, '-r*');

plot(flooders,meanOutDefense, '-b*');

txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');

ylabel('Client Timeouts)')
title('Client Timeouts during HTTPPerf')





%%%%%%%%%%%%%%%%%%%%%%%%%%%% CLIENT NWK %%%%%%%%%%%%%%%%%%%%%%%%%%%%


meanNwkNoAttack = [11.8 11.8 11.8 11.8];
meanNwkAttack =   [0.94 0.32 0.22 0.24];
meanNwkDefense=   [3.68 1.02 1.32  0.7];

stdNwkNoAttack = [0 0 0 0 ];
stdNwkAttack =   [0.114017542509914  0.130384048104053 0.130384048104053 0.114017542509914];
stdNwkDefense=   [1.14105214604767 0.238746727726266  0.414728827066554 0.254950975679639];

figure(3)

plot(flooders,meanNwkNoAttack, '-k*');

hold on;
grid on;

plot(flooders,meanNwkAttack, '-r*');

plot(flooders,meanNwkDefense, '-b*');

txt = findobj(gca,'Type','text');
set(findobj(gca,'Type','text'),'FontSize',20)
set(txt(1:end),'VerticalAlignment', 'Middle');

ylabel('Client Network Throughput)')
title('Client Network Throughput during HTTPPerf')

