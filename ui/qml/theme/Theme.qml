pragma Singleton
import QtQuick
import QtQuick.Controls

// MrBoard QML 单基础主题单例（PL008.5.b）：接收 context 注入的 defaultTheme，
// 初始化一套基础色板（chunk_ok/warn/danger/pie 等对齐 qt6 动态色键语义）；
// 无主题切换 UI——能力体现在动效/光影/阴影/粒子而非主题数量（PL008 决策 4c）

QtObject {
    id: root

    // 主题名（context property 注入，launcher 经 contracts 注入 defaultTheme）
    property string themeName: defaultTheme

    // 动画开关（A021-P0.3）：用户偏好减少动效时置 true——粒子停发、入场过渡
    // 直显（Behavior 禁用 + opacity 直达 1）；默认 false 保持完整动效
    property bool reducedMotion: false

    // 配额分级三色（对齐 qt6 theme_loader 动态色键 chunk_ok/chunk_warn/chunk_danger）
    // A021-P0.2：三色均按白底对比度 ≥3:1 校正（ok=#3CA36F:3.15/warn=#C77F00:3.25/
    // danger=#FF4B4B:3.3），色弱/浅底可辨；pie2/pie3 保持原色不改（装饰性扇区色）
    property color chunkOk: "#3CA36F"
    property color chunkWarn: "#C77F00"
    property color chunkDanger: "#FF4B4B"

    // 基础界面色（单基础主题：浅色，卡片式布局）
    property color bg: "#F3F3F3"
    property color cardBg: "#FFFFFF"
    property color textPrimary: "#1F1F1F"
    property color textSecondary: "#616161"
    property color accent: "#0078D4"

    // 边框/条纹/圆角 token（A021-P1.1：两页硬编码 #E0E0E0/#F4F4F4/radius 6 收敛引用）
    property color borderSubtle: "#E0E0E0"
    property color rowStripe: "#F4F4F4"
    property int radius: 8

    // 饼图色板（pie 系列，PL008.6.c 扇区着色用；色系区别于三级配额色）
    property color pie1: "#0078D4"
    property color pie2: "#47C18C"
    property color pie3: "#FFB020"
    property color pie4: "#FF4B4B"
    property color pie5: "#9B6BFF"
}