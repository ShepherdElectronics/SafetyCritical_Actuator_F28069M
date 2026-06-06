%% Analyze_SDC2_Full_Characterization_16u.m
% Summary plots for SDC2 16-ustep full characterization.
% Run after Python postprocess or after Plot_All_SDC2_Event_Timing_Final_OneFolder.m.

clear; clc; close all;

summaryFile = fullfile("Boss_SDC2_Event_Analysis", "SDC2_Event_Analysis_Summary.csv");
if ~isfile(summaryFile)
    summaryFile = "SDC2_Event_Analysis_Summary.csv";
end
if ~isfile(summaryFile)
    error("Could not find summary CSV. Run the event timing script first.");
end

T = readtable(summaryFile);
outFolder = "Boss_SDC2_16u_Summary_Figures";
if ~exist(outFolder, 'dir'); mkdir(outFolder); end

motion = T(T.TargetSpeed_deg_s ~= 0,:);

fig = figure('Name','16 ustep speed ratio','Color','w','Position',[100 100 1200 500]);
bar(categorical(string(motion.Direction) + " " + string(abs(motion.TargetSpeed_deg_s))), motion.MeasuredToTargetSpeedRatio);
hold on; grid on;
yline(1.0,'--','Target','LineWidth',2);
yline(0.8,':','80%','LineWidth',1.5);
yline(1.2,':','120%','LineWidth',1.5);
ylabel('Measured / target speed ratio');
xlabel('Direction and target speed magnitude (deg/s)');
title('SDC2 16 ustep Speed Tracking Ratio');
xtickangle(45);
saveas(fig, fullfile(outFolder,'Fig_01_Speed_Ratio.png'));

fig = figure('Name','16 ustep measured vs target','Color','w','Position',[100 100 900 650]);
hold on; grid on;
dirs = unique(string(motion.Direction));
for d = reshape(dirs,1,[])
    idx = string(motion.Direction) == d;
    plot(abs(motion.TargetSpeed_deg_s(idx)), motion.MeasuredAverageSpeed_deg_s(idx), '-o', 'LineWidth',2, 'MarkerSize',7, 'DisplayName',d);
end
x = unique(abs(motion.TargetSpeed_deg_s));
plot(x,x,'--','LineWidth',2,'DisplayName','Ideal 1:1');
xlabel('Target speed magnitude (deg/s)');
ylabel('Measured average speed (deg/s)');
title('SDC2 16 ustep Measured Average Speed vs Target');
legend('Location','northwest');
saveas(fig, fullfile(outFolder,'Fig_02_Measured_vs_Target.png'));

if any(strcmp(T.Properties.VariableNames,'RMSSpeedError_deg_s'))
    fig = figure('Name','16 ustep RMS speed error','Color','w','Position',[100 100 1200 500]);
    bar(categorical(string(motion.Direction) + " " + string(abs(motion.TargetSpeed_deg_s))), motion.RMSSpeedError_deg_s);
    grid on;
    ylabel('RMS event-speed error (deg/s)');
    xlabel('Direction and target speed magnitude (deg/s)');
    title('SDC2 16 ustep RMS Event-Speed Error');
    xtickangle(45);
    saveas(fig, fullfile(outFolder,'Fig_03_RMS_Speed_Error.png'));
end

fig = figure('Name','16 ustep gap counts','Color','w','Position',[100 100 1200 500]);
bar(categorical(string(motion.Direction) + " " + string(abs(motion.TargetSpeed_deg_s))), [motion.NumLongGapEvents motion.NumShortGapEvents]);
grid on;
ylabel('Count');
xlabel('Direction and target speed magnitude (deg/s)');
title('SDC2 16 ustep Long/Short Gap Counts');
legend('Long gaps','Short gaps','Location','northwest');
xtickangle(45);
saveas(fig, fullfile(outFolder,'Fig_04_Long_Short_Gaps.png'));

fprintf('Saved summary figures in %s\n', outFolder);
