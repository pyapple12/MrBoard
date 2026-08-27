pragma Singleton
import QtQuick

// MrBoard QML 字号档位单例（A021-P0.1）：modular scale 四档（base 16px @96dpi，
// Major second 1.125，data-heavy UI 紧凑档），全部用 pointSize 语义——随 OS
// DPI 缩放满足大字号适配（skill 规则：正文最小 16px、每屏 ≤3~4 档字号）；
// 全页面禁止 font.pixelSize 直写，统一经 TypeScale 取档

QtObject {
    // caption ≈12px：卡片标题/进度条标签/表格单元格/日期/状态文本（metadata）
    readonly property real caption: 9
    // body =16px：主要阅读正文（releases 正文），满足 16px 最小正文下限
    readonly property real body: 12
    // title ≈18.7px：卡片数值/版本号/区段标题（配额账户/用量分布/明细标题）
    readonly property real title: 14
    // display ≈24px：预留（当前无 display 级元素）
    readonly property real display: 18
}