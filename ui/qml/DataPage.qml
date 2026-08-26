import QtQuick
import QtQuick.Layouts
import "theme"
import "effects"

// MrBoard 数据与动态页（PL008.7）：用量明细表格 + 官方动态时间线
// 数据全部来自 launcher 注入的 context property（usageModel/releasesModel/
// tableColumns/dataPageTexts，mock 三态可切）；
// 表格列序/格式化口径对齐 qt6 _render_table（main_window.py），列头 title 经
// contracts.TABLE_COLUMNS 注入（ui.json table_columns 权威）；空态占位走
// dataPageTexts（data_empty_text/data_releases_empty）

Item {
    id: root
    objectName: "dataPage"

    // 页面入场过渡（PL008.8.a：opacity 淡入，有限动画不阻塞）
    opacity: 0
    Behavior on opacity {
        NumberAnimation {
            duration: 300
        }
    }

    // 表格静态视觉参数（qt6 QTableWidget 默认行高列宽，QML 固定合理值对齐观感）
    property var tableColumnWidths: [120, 100, 90, 100, 100, 100, 100, 90, 80]
    property int tableRowHeight: 30

    // ===== 验证/调试属性（.temp/probe_qml_data_page.py 读取） =====
    property string headerTitles: headerTitlesText()
    property int tableRowCount: tableView.rows
    property bool tableEmpty: usageModel.count === 0
    property string tableEmptyText: dataPageTexts.table_empty
    property string firstRowLabel: usageModel.count > 0 ? usageModel.getString(0, "label") : ""
    property string firstRowCalls: usageModel.count > 0 ? usageModel.getString(0, "calls") : ""
    property string firstRowTotal: usageModel.count > 0 ? formatTokens(usageModel.getNumber(0, "tokens.total")) : ""
    property string firstRowCacheRate: usageModel.count > 0 ? formatCacheRateOfNumbers(
        usageModel.getNumber(0, "tokens.cache_read"),
        usageModel.getNumber(0, "tokens.cache_write"),
        usageModel.getNumber(0, "tokens.total")
    ) : ""
    property string firstRowCost: usageModel.count > 0 ? formatCost(usageModel.getNumber(0, "cost")) : ""
    property int releaseCount: releasesModel.count
    property bool releaseEmptyVisible: releaseEmptyView.visible
    property string releaseEmptyText: dataPageTexts.releases_empty
    property string firstReleaseTag: releasesModel.count > 0 ? releasesModel.getString(0, "tag_name") : ""
    property string firstReleaseDate: releasesModel.count > 0
        ? String(releasesModel.getString(0, "published_at")).slice(0, 10) : ""

    // ===== 格式化函数（对齐 qt6 _format_tokens/_format_cost/_format_cache_rate_of） =====
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

    function formatCacheRateOfNumbers(readCount, writeCount, total) {
        // 缓存率：(缓存读+缓存写)/总 token 百分比（对齐 qt6 _format_cache_rate_of）
        if (!total) {
            return "0.0%"
        }
        return ((readCount + writeCount) / total * 100).toFixed(1) + "%"
    }

    // 单元格文本：按列 id 分支（表头顺序由 ui.json table_columns 权威，
    // 列 id 语义绑定格式化分支——P23 契约；role 名即字段名/点路径）
    function cellText(column, model) {
        var colId = column < tableColumns.length ? tableColumns[column].id : ""
        if (colId === "label") {
            return model["label"] || ""
        }
        if (colId === "calls") {
            return "" + (model["calls"] || 0)
        }
        if (colId === "total") {
            return formatTokens(model["tokens.total"])
        }
        if (colId === "input") {
            return formatTokens(model["tokens.input"])
        }
        if (colId === "output") {
            return formatTokens(model["tokens.output"])
        }
        if (colId === "reasoning") {
            return formatTokens(model["tokens.reasoning"])
        }
        if (colId === "cache") {
            return formatTokens(
                (model["tokens.cache_read"] || 0) + (model["tokens.cache_write"] || 0)
            )
        }
        if (colId === "cache_rate") {
            return formatCacheRateOfNumbers(
                model["tokens.cache_read"] || 0,
                model["tokens.cache_write"] || 0,
                model["tokens.total"]
            )
        }
        if (colId === "cost") {
            return formatCost(model["cost"])
        }
        return ""
    }

    // 列头标题逗号拼接（探针与 ui.json table_columns 动态比对）
    function headerTitlesText() {
        var parts = []
        for (var i = 0; i < tableColumns.length; i++) {
            parts.push(tableColumns[i].title)
        }
        return parts.join(",")
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // ===== 用量明细表格区 =====
        Text {
            text: dataPageTexts.detail_title
            font.pixelSize: 14
            color: Theme.textPrimary
        }

        // 列头（固定行，列宽对齐 tableColumnWidths）
        Row {
            Repeater {
                model: tableColumns
                delegate: Rectangle {
                    width: root.tableColumnWidths[index]
                    height: root.tableRowHeight
                    color: Theme.cardBg
                    border.color: "#E0E0E0"
                    border.width: 1
                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        text: modelData.title
                        font.pixelSize: 12
                        font.bold: true
                        color: Theme.textPrimary
                    }
                }
            }
        }

        // 表体（固定高度 = 行数×行高；空数据显示占位覆盖）
        Item {
            width: root.tableTotalWidth
            height: Math.max(usageModel.count, 1) * root.tableRowHeight
            TableView {
                id: tableView
                objectName: "usageTable"
                anchors.fill: parent
                model: usageModel
                clip: true
                columnWidthProvider: function (column) {
                    return root.tableColumnWidths[column] || 90
                }
                rowHeightProvider: function (row) {
                    return root.tableRowHeight
                }
                delegate: Rectangle {
                    required property int column
                    required property int row
                    required property var model
                    color: row % 2 === 1 ? "#F4F4F4" : "transparent"
                    border.color: "#E0E0E0"
                    border.width: 1
                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        anchors.rightMargin: 4
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        text: root.cellText(column, model)
                        font.pixelSize: 12
                        color: Theme.textPrimary
                    }
                }
            }
            Text {
                id: tableEmptyLabel
                visible: usageModel.count === 0
                anchors.centerIn: parent
                text: dataPageTexts.table_empty
                font.pixelSize: 12
                color: Theme.textSecondary
            }
        }

        // ===== 官方动态时间线 =====
        Text {
            text: dataPageTexts.releases_title
            font.pixelSize: 14
            color: Theme.textPrimary
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: releasesModel.count === 0 ? 1 : 0

            // 有数据：版本号/日期/正文 自绘 delegate（CardShadow 卡片阴影）
            ListView {
                id: releaseList
                objectName: "releaseList"
                clip: true
                spacing: 8
                model: releasesModel
                delegate: CardShadow {
                    width: releaseList.width
                    height: cardCol.implicitHeight + 20
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 5
                        color: Theme.cardBg
                        radius: 6
                        border.color: "#E0E0E0"
                        border.width: 1
                    }
                    Column {
                        id: cardCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4
                        Row {
                            spacing: 8
                            Text {
                                text: model.tag_name
                                font.pixelSize: 13
                                font.bold: true
                                color: Theme.textPrimary
                            }
                            Text {
                                text: String(model.published_at).slice(0, 10)
                                font.pixelSize: 12
                                color: Theme.textSecondary
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                        Text {
                            text: model.body || ""
                            font.pixelSize: 12
                            color: Theme.textSecondary
                            wrapMode: Text.Wrap
                            width: releaseList.width - 20
                        }
                    }
                }
            }

            // 空态占位
            Item {
                id: releaseEmptyView
                Text {
                    anchors.centerIn: parent
                    text: dataPageTexts.releases_empty
                    font.pixelSize: 12
                    color: Theme.textSecondary
                }
            }
        }
    }

    // 表格总宽（列宽求和，供表体容器与列头对齐）
    property int tableTotalWidth: {
        var total = 0
        for (var i = 0; i < tableColumnWidths.length; i++) {
            total += tableColumnWidths[i]
        }
        return total
    }

    Component.onCompleted: {
        opacity = 1
    }
}