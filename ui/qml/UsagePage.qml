import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCharts
import QtQuick.Particles
import FluentUI
import "theme"
import "effects"

// MrBoard 用量监控页（PL008.6）：卡片区 + 配额区 + 饼图
// 数据全部来自 launcher 注入的 context property（mock 样例三态可切）；
// 布局/文案/阈值对齐 qt6 前端（卡片 P17 顺序、配额三窗口、分级色阈值）

Item {
    id: root
    objectName: "usagePage"

    // 页面入场过渡（PL008.8.a：opacity 淡入，有限动画不阻塞）
    opacity: 0
    Behavior on opacity {
        NumberAnimation {
            duration: 300
        }
    }

    // 背景粒子点缀（PL008.8.b 必做：ParticleGroup 承载 + ImageParticle 渲染 +
    // Emitter 发射；z 序低于内容区，粒子在卡片间隙可见）
    ParticleSystem {
        id: particleSystem
        objectName: "particleSystem"
        anchors.fill: parent
        ParticleGroup {
            objectName: "sparkGroup"
            name: "spark"
        }
        ImageParticle {
            objectName: "sparkParticle"
            groups: ["spark"]
            color: Theme.pie1
            colorVariation: 0.3
            entryEffect: ImageParticle.Fade
        }
        Emitter {
            objectName: "sparkEmitter"
            group: "spark"
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            height: 30
            emitRate: 8
            lifeSpan: 3500
            size: 3
            endSize: 8
            velocity: AngleDirection {
                angle: 270
                angleVariation: 25
                magnitude: 60
                magnitudeVariation: 20
            }
        }
    }

    // ===== JS 格式化/分级（对齐 qt6 展示口径，参数经 context 注入） =====
    function formatTokens(count) {
        // token 缩写：K/M/B（阈值与后缀来自注入的 tokenAbbrUnits）
        for (var i = 0; i < tokenAbbrUnits.length; i++) {
            var entry = tokenAbbrUnits[i]
            if (count >= entry[0]) {
                return (count / entry[0]).toFixed(1) + entry[1]
            }
        }
        return "" + count
    }

    function formatCost(cost) {
        // 费用：≥1 保留 2 位，<1 保留 4 位；近零显示 -（容差注入 costZeroEpsilon）
        if (cost < costZeroEpsilon) {
            return "-"
        }
        return "$" + (cost >= 1 ? cost.toFixed(2) : cost.toFixed(4))
    }

    function formatCacheRate() {
        // 缓存率：(缓存读+缓存写)/总 token 百分比（对齐 qt6 _format_cache_rate_of）
        var total = usageSummary.total
        if (!total) {
            return "0.0%"
        }
        return (
            (usageSummary.cache_read + usageSummary.cache_write) / total * 100
        ).toFixed(1) + "%"
    }

    function colorForPercent(p) {
        // 配额分级色：>=danger 红 / >=warn 黄 / 其余绿（阈值经 context 注入，
        // 色板来自 Theme 单例自持三色，不复刻 qt6 的 quota_chunk_color）
        if (p >= dangerPercent) {
            return Theme.chunkDanger
        }
        if (p >= warnPercent) {
            return Theme.chunkWarn
        }
        return Theme.chunkOk
    }

    // 分级色阈值边界验证属性（.temp/probe_qml_usage.py 读取）
    property color colorWarnMinus1: colorForPercent(warnPercent - 1)
    property color colorWarn: colorForPercent(warnPercent)
    property color colorDangerMinus1: colorForPercent(dangerPercent - 1)
    property color colorDanger: colorForPercent(dangerPercent)

    // 状态提示弹出：statusText 非空时经 FluInfoBar 通知（错误/缓存分级类型）
    function showQuotaStatus() {
        if (statusText === "") {
            return
        }
        var err = quotaModel.getString(quotaCombo.currentIndex, "error")
        if (err) {
            infoBar.showError(statusText, 3000)
        } else {
            infoBar.showWarning(statusText, 3000)
        }
    }

    // 卡片显示值验证属性（探针读取，对齐 mock summary）
    property string cardTokens: formatTokens(usageSummary.total)
    property string cardInput: formatTokens(usageSummary.input)
    property string cardOutput: formatTokens(usageSummary.output)
    property string cardCacheRate: formatCacheRate()
    property string cardCost: formatCost(usageSummary.recorded_cost)

    // 配额状态文案（错误/缓存标注走 mock 三态样例）
    property string statusText: {
        var errorText = quotaModel.getString(quotaCombo.currentIndex, "error")
        if (errorText) {
            return errorText
        }
        if (quotaModel.getString(quotaCombo.currentIndex, "is_cached") === "True") {
            return "缓存数据"
        }
        return ""
    }
    // statusText 变化（切换账户/刷新）时弹通知条
    onStatusTextChanged: showQuotaStatus()

    // 通知条（PL008.9.b 错误策略"有提示"：FluInfoBar 替代状态栏提示；
    // FluObject 非 Item，root 经 onCompleted 绑定到本页；showError/showWarning）
    FluInfoBar {
        id: infoBar
        objectName: "infoBar"
    }

    // 饼图验证属性（探针读取；PieSeries 不在 QObject 树中，findChild 不可达）
    property int pieCount: pieSeries.count
    property string pieValues: sliceValuesText()
    property string pieColors: sliceColorsText()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // ===== 卡片区（P17 顺序：总 tokens/输入/输出/缓存率/总费用） =====
        RowLayout {
            spacing: 8
            Repeater {
                model: ["tokens", "input", "output", "cache_rate", "cost"]
                // CardShadow 包裹卡片（PL008.8.a：MultiEffect 阴影/光晕）
                delegate: CardShadow {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 84
                    FluArea {
                        anchors.fill: parent
                        radius: 8
                        color: Theme.cardBg
                        border.color: "#E0E0E0"
                        border.width: 1
                        Column {
                            anchors.centerIn: parent
                            spacing: 4
                            Text {
                                text: cardValue(modelData)
                                font.pixelSize: 20
                                font.bold: true
                                color: Theme.textPrimary
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: cardTitles[modelData] || ""
                                font.pixelSize: 12
                                color: Theme.textSecondary
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }
                }
            }
        }

        // ===== 配额区：账户选择器 + 添加账户 + 单卡三进度条 =====
        FluArea {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 8
            color: Theme.cardBg
            border.color: "#E0E0E0"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    spacing: 8
                    Text {
                        text: "配额账户"
                        font.pixelSize: 14
                        color: Theme.textPrimary
                    }
                    FluComboBox {
                        id: quotaCombo
                        objectName: "quotaCombo"
                        Layout.fillWidth: true
                        model: quotaModel
                        textRole: "workspace_id"
                    }
                    FluButton {
                        text: "添加账户"
                        font.pixelSize: 13
                        onClicked: {
                            console.log("PL008.6: 添加账户（演示版占位）")
                        }
                    }
                }

                Text {
                    text: root.statusText
                    visible: root.statusText !== ""
                    color: Theme.chunkWarn
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }

                // 三窗口进度条（five_hour/weekly/monthly 绑定当前账户）
                // FluProgressBar 在真实窗口（使用常态）正常；offscreen 下其
                // Infinite 循环动画崩溃（库 bug，仅探针环境受影响）
                FluProgressBar {
                    id: barFiveHour
                    objectName: "barFiveHour"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 10
                    from: 0
                    to: 100
                    value: quotaModel.getNumber(quotaCombo.currentIndex, "five_hour.usage_percent")
                    color: colorForPercent(value)
                    Text {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.topMargin: -18
                        text: "5 小时"
                        font.pixelSize: 12
                        color: Theme.textSecondary
                    }
                }
                FluProgressBar {
                    id: barWeekly
                    objectName: "barWeekly"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 10
                    from: 0
                    to: 100
                    value: quotaModel.getNumber(quotaCombo.currentIndex, "weekly.usage_percent")
                    color: colorForPercent(value)
                    Text {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.topMargin: -18
                        text: "每周"
                        font.pixelSize: 12
                        color: Theme.textSecondary
                    }
                }
                FluProgressBar {
                    id: barMonthly
                    objectName: "barMonthly"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 10
                    from: 0
                    to: 100
                    value: quotaModel.getNumber(quotaCombo.currentIndex, "monthly.usage_percent")
                    color: colorForPercent(value)
                    Text {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.topMargin: -18
                        text: "每月"
                        font.pixelSize: 12
                        color: Theme.textSecondary
                    }
                }

                // ===== 饼图（QtCharts PieSeries，用量百分比，clear-append 动态更新） =====
                Text {
                    text: "用量分布"
                    font.pixelSize: 14
                    color: Theme.textPrimary
                }
                ChartView {
                    id: chartView
                    objectName: "quotaPie"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    antialiasing: true
                    backgroundColor: "transparent"
                    legend.visible: false
                    PieSeries {
                        id: pieSeries
                        objectName: "quotaPieSeries"
                    }
                }
            }
        }
    }

    // 卡片值按键返回格式化字符串（delegate 绑定用）
    function cardValue(key) {
        if (key === "tokens") {
            return formatTokens(usageSummary.total)
        }
        if (key === "input") {
            return formatTokens(usageSummary.input)
        }
        if (key === "output") {
            return formatTokens(usageSummary.output)
        }
        if (key === "cache_rate") {
            return formatCacheRate()
        }
        if (key === "cost") {
            return formatCost(usageSummary.recorded_cost)
        }
        return "-"
    }

    // 饼图扇区数值文本（探针验证用，逗号连接）
    function sliceValuesText() {
        var parts = []
        for (var i = 0; i < pieSeries.count; i++) {
            parts.push(pieSeries.at(i).value.toFixed(0))
        }
        return parts.join(",")
    }

    // 饼图扇区颜色文本（探针验证用，逗号连接，小写）
    function sliceColorsText() {
        var parts = []
        for (var i = 0; i < pieSeries.count; i++) {
            parts.push(pieSeries.at(i).color.toString().toLowerCase())
        }
        return parts.join(",")
    }

    // 重建饼图：当前账户三窗口扇区（clear-append），弧色按 usage_percent 分级
    function updateSlices() {
        pieSeries.clear()
        var idx = quotaCombo.currentIndex
        var windows = [
            ["five_hour", "5 小时"],
            ["weekly", "每周"],
            ["monthly", "每月"]
        ]
        for (var i = 0; i < windows.length; i++) {
            var percent = quotaModel.getNumber(idx, windows[i][0] + ".usage_percent")
            var slice = pieSeries.append(windows[i][1], percent)
            slice.color = colorForPercent(percent)
        }
    }

    Component.onCompleted: {
        infoBar.root = root
        updateSlices()
        quotaCombo.currentIndexChanged.connect(updateSlices)
        showQuotaStatus()
        opacity = 1
    }
}