%% Plot_All_SDC2_Event_Timing_Final_OneFolder.m
% Event-based encoder analysis for every SDC2 speed section.
% Input: SDC2_clean.csv or newest SDC2*_raw*.csv
% Output: Boss_SDC2_Event_Analysis/*.png and summary CSV
%
% Method: raw EncoderCount changes only; no filtering, smoothing, or grouped averaging.

clear; clc; close all;

rawFile = "SDC2_clean.csv";
CPR = 5000;
edgeMult = 2;
gearRatio = 24.65;
degPerCount = 360 / (CPR * edgeMult * gearRatio);

outputRoot = "Boss_SDC2_Event_Analysis";
if ~exist(outputRoot, 'dir'); mkdir(outputRoot); end

speedRatioGoodLow  = 0.80;
speedRatioGoodHigh = 1.20;
dtRatioWarnHigh = 2.0;
dtRatioWarnLow  = 0.5;
minRowsPerSegment = 10;

if ~isfile(rawFile)
    files = dir("SDC2*_raw*.csv");
    if isempty(files)
        files = dir("*.csv");
    end
    if isempty(files)
        error("Could not find SDC2_clean.csv or any CSV file in this folder.");
    end
    [~, idxNewest] = max([files.datenum]);
    rawFile = string(files(idxNewest).name);
end

fprintf("Reading file: %s\n", rawFile);
T = readtable(rawFile);
vars = string(T.Properties.VariableNames);

timeCol   = findCol(vars, ["Time_s","Time"]);
targetCol = findCol(vars, ["TargetSpeed_deg_s","TargetSpe","TargetSpeed"]);
countCol  = findCol(vars, ["EncoderCount","Encoder"]);
stateCol  = findColOptional(vars, ["State"]);
faultCol  = findColOptional(vars, ["FaultCode","Fault"]);
testCol   = findColOptional(vars, ["TestName","Test"]);
dirCol    = findColOptional(vars, ["Direction"]);
loadCol   = findColOptional(vars, ["LoadCase"]);

targetAll = T.(targetCol);
speeds = unique(targetAll);
speeds = speeds(~isnan(speeds));

Summary = table();

for s = reshape(speeds, 1, [])
    idxSpeed = abs(targetAll - s) < 1e-12;
    if nnz(idxSpeed) < minRowsPerSegment; continue; end

    % If TestName/Direction are available, split by them too.
    if testCol ~= ""
        testNames = unique(string(T.(testCol)(idxSpeed)));
    else
        testNames = "SEGMENT";
    end

    for tn = reshape(testNames,1,[])
        idx = idxSpeed;
        if testCol ~= ""; idx = idx & string(T.(testCol)) == tn; end
        if nnz(idx) < minRowsPerSegment; continue; end

        S = T(idx,:);
        tRaw = S.(timeCol);
        cRaw = S.(countCol);
        t = tRaw - tRaw(1);
        c = cRaw;
        cDelta = c - c(1);
        duration = t(end) - t(1);
        totalCountDelta = c(end) - c(1);

        expectedCountsPerSec = abs(s) / degPerCount;
        expectedDt = 1 / expectedCountsPerSec;
        expectedCountDelta = expectedCountsPerSec * duration;
        measuredCountsPerSec = abs(totalCountDelta) / duration;
        measuredAverageSpeed = measuredCountsPerSec * degPerCount;
        speedRatio = measuredAverageSpeed / abs(s);
        countRatio = abs(totalCountDelta) / expectedCountDelta;

        dcSample = diff(c);
        eventIdx = dcSample ~= 0;
        eventTimes = t(2:end); eventTimes = eventTimes(eventIdx);
        eventCounts = c(2:end); eventCounts = eventCounts(eventIdx);

        if numel(eventTimes) >= 2
            eventDt = diff(eventTimes);
            eventCountJump = abs(diff(eventCounts));
            eventSpeed = eventCountJump * degPerCount ./ eventDt;
            eventTimes2 = eventTimes(2:end);
            meanDt = mean(eventDt,"omitnan");
            medianDt = median(eventDt,"omitnan");
            stdDt = std(eventDt,"omitnan");
            minDt = min(eventDt); maxDt = max(eventDt);
            meanEventSpeed = mean(eventSpeed,"omitnan");
            medianEventSpeed = median(eventSpeed,"omitnan");
            stdEventSpeed = std(eventSpeed,"omitnan");
            rmsEventSpeed = sqrt(mean(eventSpeed.^2,"omitnan"));
            rmsSpeedError = sqrt(mean((eventSpeed - abs(s)).^2,"omitnan"));
            highDtIdx = eventDt > dtRatioWarnHigh * expectedDt;
            lowDtIdx = eventDt < dtRatioWarnLow * expectedDt;
            badSpeedIdx = eventSpeed < speedRatioGoodLow * abs(s) | eventSpeed > speedRatioGoodHigh * abs(s);
            numLongGaps = nnz(highDtIdx);
            numShortGaps = nnz(lowDtIdx);
            numBadSpeedEvents = nnz(badSpeedIdx);
        else
            eventDt = []; eventSpeed = []; eventTimes2 = [];
            meanDt = NaN; medianDt = NaN; stdDt = NaN; minDt = NaN; maxDt = NaN;
            meanEventSpeed = NaN; medianEventSpeed = NaN; stdEventSpeed = NaN;
            rmsEventSpeed = NaN; rmsSpeedError = NaN;
            highDtIdx = []; lowDtIdx = []; badSpeedIdx = [];
            numLongGaps = NaN; numShortGaps = NaN; numBadSpeedEvents = NaN;
        end

        if faultCol ~= ""
            faults = unique(string(S.(faultCol)));
            faults = faults(faults ~= "" & faults ~= "NONE");
            if isempty(faults); faultText = "NONE"; else; faultText = strjoin(faults, ", "); end
        else
            faultText = "N/A";
        end

        if stateCol ~= ""; stateText = strjoin(unique(string(S.(stateCol))), ", "); else; stateText = "N/A"; end
        if dirCol ~= ""; directionText = string(S.(dirCol)(1)); else; directionText = "N/A"; end
        if loadCol ~= ""; loadText = string(S.(loadCol)(1)); else; loadText = "N/A"; end

        if abs(s) == 0
            result = "STATIC";
        elseif speedRatio >= speedRatioGoodLow && speedRatio <= speedRatioGoodHigh
            result = "GOOD: average speed near target";
        elseif speedRatio < 0.40
            result = "FAIL: actual speed far below command";
        elseif speedRatio < speedRatioGoodLow
            result = "LOW: moving slower than command";
        else
            result = "HIGH: moving faster than command";
        end

        fig = figure('Name',sprintf('SDC2 event %.6f',s),'Color','w','Position',[100 60 1350 950]);
        tiledlayout(3,1,'TileSpacing','compact','Padding','compact');

        nexttile;
        if expectedCountsPerSec > 0
            idealCount = signOrOne(totalCountDelta) * expectedCountsPerSec * t;
        else
            idealCount = zeros(size(t));
        end
        plot(t,cDelta,'-o','MarkerSize',3,'LineWidth',1.2,'DisplayName','Measured encoder count delta'); hold on;
        plot(t,idealCount,'--','LineWidth',2.0,'DisplayName','Ideal count delta');
        grid on; ax=gca; ax.XMinorGrid='on'; ax.YMinorGrid='on'; ax.GridAlpha=0.28; ax.MinorGridAlpha=0.12;
        xlabel('Segment time (s)'); ylabel('Encoder count delta (counts)');
        title(sprintf('Raw Encoder Count Delta at %.6f deg/s',s),'Interpreter','none'); legend('Location','northwest');
        ann1 = sprintf(['Target speed: %.6f deg/s\nDuration: %.2f s\nMeasured count delta: %d counts\nExpected count delta: %.1f counts\nCount ratio: %.3f\nAverage measured speed: %.6f deg/s\nSpeed ratio: %.3f\n%s\nMethod: raw encoder counts; no filtering, smoothing, or grouped averaging'],s,duration,totalCountDelta,expectedCountDelta,countRatio,measuredAverageSpeed,speedRatio,result);
        text(0.012,0.95,ann1,'Units','normalized','VerticalAlignment','top','BackgroundColor','white','EdgeColor',[0.25 0.25 0.25],'Margin',7,'FontSize',10);

        nexttile;
        if ~isempty(eventTimes2)
            plot(eventTimes2,eventDt,'-o','MarkerSize',4,'LineWidth',1.2,'DisplayName','Measured event interval'); hold on;
            yline(expectedDt,'--','Expected interval','LineWidth',2.0);
            yline(dtRatioWarnHigh*expectedDt,':','Long-gap threshold','LineWidth',1.4);
            yline(dtRatioWarnLow*expectedDt,':','Short-gap threshold','LineWidth',1.4);
            if any(highDtIdx); plot(eventTimes2(highDtIdx),eventDt(highDtIdx),'ro','MarkerSize',7,'LineWidth',1.5,'DisplayName','Long gaps'); end
            if any(lowDtIdx); plot(eventTimes2(lowDtIdx),eventDt(lowDtIdx),'mo','MarkerSize',7,'LineWidth',1.5,'DisplayName','Short gaps'); end
        end
        grid on; ax=gca; ax.XMinorGrid='on'; ax.YMinorGrid='on'; ax.GridAlpha=0.28; ax.MinorGridAlpha=0.12;
        xlabel('Segment time (s)'); ylabel('Time between count events (s/event)'); title('Encoder Event Timing'); legend('Location','northwest');
        ann2 = sprintf(['Expected interval: %.4f s/event\nMean interval: %.4f s/event\nMedian interval: %.4f s/event\nStd interval: %.4f s\nMin / max interval: %.4f / %.4f s\nLong-gap events: %d\nShort-gap events: %d\nFaults observed: %s'],expectedDt,meanDt,medianDt,stdDt,minDt,maxDt,numLongGaps,numShortGaps,faultText);
        text(0.012,0.95,ann2,'Units','normalized','VerticalAlignment','top','BackgroundColor','white','EdgeColor',[0.25 0.25 0.25],'Margin',7,'FontSize',10);

        nexttile;
        if ~isempty(eventTimes2)
            plot(eventTimes2,eventSpeed,'-o','MarkerSize',4,'LineWidth',1.2,'DisplayName','Event-based speed'); hold on;
            yline(abs(s),'--','Target speed','LineWidth',2.0);
            yline(speedRatioGoodLow*abs(s),':','80% target','LineWidth',1.3);
            yline(speedRatioGoodHigh*abs(s),':','120% target','LineWidth',1.3);
            if any(badSpeedIdx); plot(eventTimes2(badSpeedIdx),eventSpeed(badSpeedIdx),'ro','MarkerSize',6,'LineWidth',1.3,'DisplayName','Outside 80-120% band'); end
        end
        grid on; ax=gca; ax.XMinorGrid='on'; ax.YMinorGrid='on'; ax.GridAlpha=0.28; ax.MinorGridAlpha=0.12;
        xlabel('Segment time (s)'); ylabel('Event-based table speed (deg/s)'); title('Raw Event-to-Event Encoder Speed, No Filtering'); legend('Location','northwest');
        ann3 = sprintf(['Target speed: %.6f deg/s\nMean event speed: %.6f deg/s\nMedian event speed: %.6f deg/s\nRMS event speed: %.6f deg/s\nRMS speed error: %.6f deg/s\nAverage speed from total counts: %.6f deg/s\nBad events outside 80-120%%: %d\nEvent speed = count step / time between count changes'],abs(s),meanEventSpeed,medianEventSpeed,rmsEventSpeed,rmsSpeedError,measuredAverageSpeed,numBadSpeedEvents);
        text(0.012,0.95,ann3,'Units','normalized','VerticalAlignment','top','BackgroundColor','white','EdgeColor',[0.25 0.25 0.25],'Margin',7,'FontSize',10);

        safeSpeed = replace(sprintf('%.6f',s),'.','p');
        safeTest = regexprep(char(tn),'[^A-Za-z0-9_]','_');
        figName = fullfile(outputRoot,sprintf('Event_Annotated_%s_%s_%s_deg_s.png',safeTest,directionText,safeSpeed));
        saveas(fig,figName);

        Summary = [Summary; table(string(tn),loadText,directionText,s,duration,totalCountDelta,expectedCountDelta,measuredCountsPerSec,expectedCountsPerSec,measuredAverageSpeed,speedRatio,countRatio,expectedDt,meanDt,medianDt,stdDt,minDt,maxDt,meanEventSpeed,medianEventSpeed,stdEventSpeed,rmsEventSpeed,rmsSpeedError,numLongGaps,numShortGaps,numBadSpeedEvents,string(faultText),string(result),string(stateText), ...
            'VariableNames',{'TestName','LoadCase','Direction','TargetSpeed_deg_s','Duration_s','MeasuredCountDelta','ExpectedCountDelta','MeasuredCountsPerSec','ExpectedCountsPerSec','MeasuredAverageSpeed_deg_s','MeasuredToTargetSpeedRatio','MeasuredToExpectedCountRatio','ExpectedSecondsPerEvent','MeanSecondsPerEvent','MedianSecondsPerEvent','StdSecondsPerEvent','MinSecondsPerEvent','MaxSecondsPerEvent','MeanEventSpeed_deg_s','MedianEventSpeed_deg_s','StdEventSpeed_deg_s','RMSEventSpeed_deg_s','RMSSpeedError_deg_s','NumLongGapEvents','NumShortGapEvents','NumBadSpeedEvents','FaultsObserved','Result','StatesObserved'})];
    end
end

writetable(Summary,fullfile(outputRoot,'SDC2_Event_Analysis_Summary.csv'));

fig = figure('Name','SDC2 Combined Summary','Color','w','Position',[150 100 1200 600]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile;
hold on; grid on; ax=gca; ax.XMinorGrid='on'; ax.YMinorGrid='on';
uniqueDirs = unique(Summary.Direction);
for d = reshape(uniqueDirs,1,[])
    idx = Summary.Direction == d & Summary.TargetSpeed_deg_s ~= 0;
    plot(abs(Summary.TargetSpeed_deg_s(idx)),Summary.MeasuredAverageSpeed_deg_s(idx),'-o','LineWidth',2,'MarkerSize',7,'DisplayName',d);
end
x = unique(abs(Summary.TargetSpeed_deg_s(Summary.TargetSpeed_deg_s ~= 0)));
plot(x,x,'--','LineWidth',2,'DisplayName','Ideal 1:1');
xlabel('Target table speed magnitude (deg/s)'); ylabel('Measured average table speed (deg/s)'); title('Measured Average Speed vs Target Speed'); legend('Location','northwest');
nexttile;
idx = Summary.TargetSpeed_deg_s ~= 0;
bar(categorical(string(Summary.Direction(idx)) + " " + string(abs(Summary.TargetSpeed_deg_s(idx)))),Summary.MeasuredToTargetSpeedRatio(idx)); hold on; grid on;
yline(1.0,'--','Target','LineWidth',2); yline(speedRatioGoodLow,':','80%','LineWidth',1.5); yline(speedRatioGoodHigh,':','120%','LineWidth',1.5);
ylabel('Measured / target speed ratio'); title('Speed Tracking Ratio by Test Section'); xtickangle(45);
saveas(fig,fullfile(outputRoot,'SDC2_Event_Analysis_Combined_Summary.png'));

fprintf('\nSaved all outputs in:\n  %s\n', fullfile(pwd,outputRoot));

function colName = findCol(vars,candidates)
    colName = findColOptional(vars,candidates);
    if colName == ""; error('Could not find required column. Tried: %s', strjoin(candidates, ', ')); end
end
function colName = findColOptional(vars,candidates)
    colName = "";
    for c = candidates
        idx = find(strcmpi(vars,c),1);
        if ~isempty(idx); colName = vars(idx); return; end
    end
    for c = candidates
        idx = find(startsWith(lower(vars),lower(c)),1);
        if ~isempty(idx); colName = vars(idx); return; end
    end
end
function y = signOrOne(x)
    if x < 0; y = -1; else; y = 1; end
end
